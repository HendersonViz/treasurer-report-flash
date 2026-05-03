from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from .models import ComparativeLine, FlashReport, Variance
from .sage50 import Sage50WorkbookParser

DEFAULT_VARIANCE_AMOUNT_THRESHOLD = Decimal("5000")
DEFAULT_VARIANCE_PERCENT_THRESHOLD = Decimal("15")


def build_flash_report(
    income_path: Path,
    balance_path: Path,
    notes_path: Path | None = None,
    variance_amount_threshold: Decimal = DEFAULT_VARIANCE_AMOUNT_THRESHOLD,
    variance_percent_threshold: Decimal = DEFAULT_VARIANCE_PERCENT_THRESHOLD,
) -> FlashReport:
    parser = Sage50WorkbookParser()
    organization_name, income_title = parser.read_report_heading(income_path)
    _, balance_title = parser.read_report_heading(balance_path)
    income_statement = parser.parse_income_statement(income_path)
    balance_sheet = parser.parse_balance_sheet(balance_path)
    notes = read_notes(notes_path)
    variances = find_major_variances(
        income_statement,
        amount_threshold=variance_amount_threshold,
        percent_threshold=variance_percent_threshold,
    )

    report = FlashReport(
        organization_name=organization_name,
        report_title=f"{income_title} and {balance_title}",
        treasurer_notes=notes,
        income_statement=income_statement,
        balance_sheet=balance_sheet,
        major_variances=variances,
    )
    report.risks_and_issues = build_risks_and_issues(report)
    report.decisions_needed = build_decisions_needed(notes)
    report.commentary = build_commentary(report)
    return report


def read_notes(notes_path: Path | None) -> list[str]:
    if notes_path is None:
        return []

    content = notes_path.read_text(encoding="utf-8").splitlines()
    notes: list[str] = []
    current: list[str] = []

    for line in content:
        stripped = line.strip()
        if not stripped:
            if current:
                notes.append(" ".join(current))
                current = []
            continue

        stripped = stripped.lstrip("#").strip()
        if stripped.startswith(("- ", "* ")):
            if current:
                notes.append(" ".join(current))
                current = []
            notes.append(stripped[2:].strip())
            continue

        current.append(stripped)

    if current:
        notes.append(" ".join(current))

    return [note for note in notes if note]


def find_major_variances(
    lines: list[ComparativeLine],
    *,
    amount_threshold: Decimal,
    percent_threshold: Decimal,
) -> list[Variance]:
    variances: list[Variance] = []

    for line in lines:
        current = line.current or Decimal("0")
        prior = line.prior or Decimal("0")
        change = current - prior
        percent_change = line.percent_change
        if percent_change is None and prior != 0:
            percent_change = (change / abs(prior) * Decimal("100")).quantize(Decimal("0.01"))

        if abs(change) < amount_threshold:
            continue
        if percent_change is not None and abs(percent_change) < percent_threshold:
            continue

        variances.append(
            Variance(
                section=line.section,
                label=line.label,
                current=current,
                prior=prior,
                change=change,
                percent_change=percent_change,
            )
        )

    return sorted(variances, key=lambda variance: abs(variance.change), reverse=True)


def build_risks_and_issues(report: FlashReport) -> list[str]:
    risks: list[str] = []

    for line in report.balance_sheet:
        label = line.label.lower()
        current = line.current or Decimal("0")
        if any(term in label for term in ("cash", "bank", "credit union")) and current < 0:
            risks.append(f"{line.label} is negative at {_currency(current)}.")

    for variance in report.major_variances:
        section = variance.section.upper()
        if section.startswith("REVENUE") and variance.change < 0:
            risks.append(f"{variance.label} revenue is down {_currency(abs(variance.change))}.")
        if section.startswith("EXPENSE") and variance.change > 0:
            risks.append(f"{variance.label} expense is up {_currency(variance.change)}.")

    return risks[:8] or ["No major financial risks were automatically flagged from the uploads."]


def build_decisions_needed(notes: list[str]) -> list[str]:
    decisions = [
        note
        for note in notes
        if any(term in note.lower() for term in ("decision", "approve", "approval", "vote"))
    ]
    return decisions or ["No board decisions were identified in the treasurer notes."]


def build_commentary(report: FlashReport) -> list[str]:
    revenue = section_total(report.income_statement, "REVENUE")
    expenses = section_total(report.income_statement, "EXPENSE")
    net = revenue - expenses
    cash = cash_position(report)
    commentary = [
        (
            f"Revenue is {_currency(revenue)} and expenses are {_currency(expenses)}, "
            f"for a net result of {_currency(net)}."
        ),
        f"Cash-like balances total {_currency(cash)} based on the uploaded balance sheet.",
    ]

    if report.major_variances:
        top = report.major_variances[0]
        direction = "higher" if top.change > 0 else "lower"
        commentary.append(
            f"The largest variance is {top.label}, which is "
            f"{_currency(abs(top.change))} {direction} than the comparison period."
        )
    else:
        commentary.append("No major income statement variances crossed the MVP thresholds.")

    return commentary


def section_total(lines: list[ComparativeLine], section_name: str) -> Decimal:
    section_name = section_name.upper()
    return sum(
        (line.current or Decimal("0"))
        for line in lines
        if line.section.upper().startswith(section_name)
    )


def cash_position(report: FlashReport) -> Decimal:
    cash_labels = ("cash", "bank", "credit union", "term deposit")
    return sum(
        (line.current or Decimal("0"))
        for line in report.balance_sheet
        if any(term in line.label.lower() for term in cash_labels)
    )


def _currency(value: Decimal) -> str:
    return f"${value:,.2f}"
