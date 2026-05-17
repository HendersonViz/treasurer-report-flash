from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from .models import (
    CashSummaryLine,
    ComparativeLine,
    FlashReport,
    LedgerEntry,
    SignificantTransaction,
    Variance,
    VarianceGroup,
)
from .notes import (
    extract_named_markdown_section,
    extract_plain_notes,
    read_notes_content,
    render_safe_markdown,
)
from .sage50 import Sage50WorkbookParser

DEFAULT_VARIANCE_AMOUNT_THRESHOLD = Decimal("5000")
DEFAULT_VARIANCE_PERCENT_THRESHOLD = Decimal("15")


def build_flash_report(
    income_path: Path,
    balance_path: Path,
    notes_path: Path | None = None,
    ledger_path: Path | None = None,
    variance_amount_threshold: Decimal = DEFAULT_VARIANCE_AMOUNT_THRESHOLD,
    variance_percent_threshold: Decimal = DEFAULT_VARIANCE_PERCENT_THRESHOLD,
) -> FlashReport:
    parser = Sage50WorkbookParser()
    organization_name, income_title = parser.read_report_heading(income_path)
    _, balance_title = parser.read_report_heading(balance_path)
    current_period, comparative_period = parser.read_comparative_periods(income_path)
    balance_sheet_date, comparative_balance_sheet_date = parser.read_comparative_periods(
        balance_path
    )
    income_statement = parser.parse_income_statement(income_path)
    balance_sheet = parser.parse_balance_sheet(balance_path)
    ledger_entries = parser.parse_general_ledger(ledger_path) if ledger_path is not None else []
    notes_markdown = read_notes_content(notes_path)
    snapshot_markdown, treasurer_notes_markdown = extract_named_markdown_section(
        notes_markdown, {"executive snapshot"}
    )
    notes = extract_plain_notes(treasurer_notes_markdown)
    variance_groups = find_major_variance_groups(
        income_statement,
        amount_threshold=variance_amount_threshold,
        percent_threshold=variance_percent_threshold,
    )
    variances = [group.summary for group in variance_groups]

    report = FlashReport(
        organization_name=organization_name,
        report_title=f"{income_title} and {balance_title}",
        current_period=current_period,
        comparative_period=comparative_period,
        balance_sheet_date=balance_sheet_date,
        comparative_balance_sheet_date=comparative_balance_sheet_date,
        executive_snapshot=extract_plain_notes(snapshot_markdown),
        executive_snapshot_html=render_safe_markdown(snapshot_markdown),
        treasurer_notes=notes,
        treasurer_notes_html=render_safe_markdown(treasurer_notes_markdown),
        income_statement=income_statement,
        balance_sheet=balance_sheet,
        cash_summary=build_cash_summary(balance_sheet),
        significant_transactions=find_significant_transactions(ledger_entries),
        major_variances=variances,
        major_variance_groups=variance_groups,
        ledger_entries=ledger_entries,
    )
    report.risks_and_issues = build_risks_and_issues(report)
    report.decisions_needed = build_decisions_needed(notes)
    report.commentary = build_commentary(report)
    if not report.executive_snapshot:
        report.executive_snapshot = build_executive_snapshot(report)
    return report


def build_cash_summary(lines: list[ComparativeLine]) -> list[CashSummaryLine]:
    operating = _sum_balance_lines(
        lines,
        {
            "Cash Float - Bar",
            "Petty Cash - Office",
            "Debit Card Transactions",
            "Master Card Debit",
            "VISA Card Debit",
            "Bank",
            "Share - Credit Union",
        },
    )
    short_term = _sum_balance_lines(lines, {"Term Deposits - short term"})
    locked_in = _sum_balance_lines(lines, {"Term Deposits"})
    restricted = _sum_balance_lines(lines, {"Capital Reserve Fund"})
    unrestricted = (
        operating[0] + short_term[0] + locked_in[0] - restricted[0],
        operating[1] + short_term[1] + locked_in[1] - restricted[1],
    )

    return [
        CashSummaryLine("Operating Account + float + petty cash", *operating),
        CashSummaryLine("Short Term Deposits (cashable)", *short_term),
        CashSummaryLine("Locked in Term Deposits", *locked_in),
        CashSummaryLine("Capital Reserve Fund (restricted)", -restricted[0], -restricted[1]),
        CashSummaryLine("Remainder (unrestricted funds)", *unrestricted),
    ]


def find_significant_transactions(
    entries: list[LedgerEntry], *, limit: int = 5
) -> list[SignificantTransaction]:
    grouped: dict[tuple[object, str | None, str | None], list[LedgerEntry]] = {}
    for entry in entries:
        key = (entry.transaction_date, entry.source_number, entry.journal_entry)
        grouped.setdefault(key, []).append(entry)

    transactions: list[SignificantTransaction] = []
    for group in grouped.values():
        total_debits = sum((entry.debits for entry in group), Decimal("0"))
        total_credits = sum((entry.credits for entry in group), Decimal("0"))
        amount = max(total_debits, total_credits)
        if amount == 0:
            continue

        primary = _primary_transaction_entry(group)
        description = (
            primary.comment
            or primary.source_number
            or primary.journal_entry
            or "Ledger transaction"
        )
        transactions.append(
            SignificantTransaction(
                transaction_date=primary.transaction_date,
                item=primary.account_name,
                description=description,
                amount=amount,
            )
        )

    return sorted(transactions, key=lambda transaction: transaction.amount, reverse=True)[:limit]


def read_notes(notes_path: Path | None) -> list[str]:
    return extract_plain_notes(read_notes_content(notes_path))


def find_major_variances(
    lines: list[ComparativeLine],
    *,
    amount_threshold: Decimal,
    percent_threshold: Decimal,
) -> list[Variance]:
    variances: list[Variance] = []

    for line in lines:
        if line.section.upper() == "NET RESULT":
            continue

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


def find_major_variance_groups(
    lines: list[ComparativeLine],
    *,
    amount_threshold: Decimal,
    percent_threshold: Decimal,
    limit: int = 6,
    driver_limit: int = 3,
) -> list[VarianceGroup]:
    variances = find_major_variances(
        lines,
        amount_threshold=amount_threshold,
        percent_threshold=percent_threshold,
    )
    if not variances:
        return []

    statement_areas = _statement_area_map(lines)
    consumed: set[tuple[str, str]] = set()
    groups: list[VarianceGroup] = []

    for area_name in ("REVENUE", "EXPENSE"):
        total = next(
            (
                variance
                for variance in variances
                if variance.label.strip().upper() == f"TOTAL {area_name}"
            ),
            None,
        )
        if total is None:
            continue

        area_variances = [
            variance
            for variance in variances
            if variance != total and statement_areas.get(_variance_key(variance)) == area_name
        ]
        drivers = sorted(
            _representative_variances_by_section(area_variances),
            key=lambda variance: abs(variance.change),
            reverse=True,
        )[:driver_limit]
        groups.append(VarianceGroup(summary=total, drivers=drivers))
        consumed.add(_variance_key(total))
        consumed.update(_variance_key(variance) for variance in area_variances)

    section_totals = {
        _total_section_name(variance.label): variance
        for variance in variances
        if _is_total_line(variance.label) and _variance_key(variance) not in consumed
    }
    details_by_section: dict[str, list[Variance]] = {}
    details_without_total: dict[str, list[Variance]] = {}

    for variance in variances:
        if _variance_key(variance) in consumed:
            continue
        if _is_total_line(variance.label):
            continue
        section_key = variance.section.strip().upper()
        if section_key in section_totals:
            details_by_section.setdefault(section_key, []).append(variance)
        else:
            details_without_total.setdefault(section_key, []).append(variance)

    for section_key, total in section_totals.items():
        drivers = sorted(
            details_by_section.get(section_key, []),
            key=lambda variance: abs(variance.change),
            reverse=True,
        )[:driver_limit]
        groups.append(VarianceGroup(summary=total, drivers=drivers))

    for detail_variances in details_without_total.values():
        sorted_details = sorted(
            detail_variances,
            key=lambda variance: abs(variance.change),
            reverse=True,
        )
        groups.append(
            VarianceGroup(
                summary=sorted_details[0],
                drivers=sorted_details[1 : driver_limit + 1],
            )
        )

    return sorted(groups, key=lambda group: abs(group.summary.change), reverse=True)[:limit]


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
    net = net_result(report.income_statement)
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


def build_executive_snapshot(report: FlashReport) -> list[str]:
    revenue = section_total(report.income_statement, "REVENUE")
    expenses = section_total(report.income_statement, "EXPENSE")
    net = net_result(report.income_statement)
    cash = cash_position(report)
    snapshot = [
        f"Cash-like balances total {_currency(cash)}.",
        (
            f"Revenue is {_currency(revenue)} and expenses are {_currency(expenses)}, "
            f"for a net result of {_currency(net)}."
        ),
    ]

    revenue_group = _find_variance_group(report.major_variance_groups, "TOTAL REVENUE")
    if revenue_group is not None:
        snapshot.append(_variance_snapshot_line("Revenue", revenue_group))

    expense_group = _find_variance_group(report.major_variance_groups, "TOTAL EXPENSE")
    if expense_group is not None:
        snapshot.append(_variance_snapshot_line("Expenses", expense_group))

    decisions = [
        decision
        for decision in report.decisions_needed
        if not decision.startswith("No board decisions")
    ]
    if decisions:
        snapshot.append(f"Board attention requested: {decisions[0]}")
    else:
        snapshot.append(
            "No board decisions were automatically identified from the treasurer notes."
        )

    return snapshot


def section_total(lines: list[ComparativeLine], section_name: str) -> Decimal:
    section_name = section_name.upper()
    total_label = f"TOTAL {section_name}"
    explicit_total = _line_current(lines, total_label)
    if explicit_total is not None:
        return explicit_total

    return sum(
        (line.current or Decimal("0"))
        for line in lines
        if line.section.upper().startswith(section_name)
    )


def net_result(lines: list[ComparativeLine]) -> Decimal:
    for label in ("NET INCOME", "NET LOSS"):
        explicit_net = _line_current(lines, label)
        if explicit_net is not None:
            return explicit_net

    return section_total(lines, "REVENUE") - section_total(lines, "EXPENSE")


def cash_position(report: FlashReport) -> Decimal:
    cash_labels = ("cash", "bank", "credit union", "term deposit")
    return sum(
        (line.current or Decimal("0"))
        for line in report.balance_sheet
        if any(term in line.label.lower() for term in cash_labels)
    )


def _currency(value: Decimal) -> str:
    if value < 0:
        return f"-${abs(value):,.2f}"
    return f"${value:,.2f}"


def _sum_balance_lines(lines: list[ComparativeLine], labels: set[str]) -> tuple[Decimal, Decimal]:
    targets = {label.lower() for label in labels}
    current = Decimal("0")
    prior = Decimal("0")
    for line in lines:
        if line.label.strip().lower() in targets:
            current += line.current or Decimal("0")
            prior += line.prior or Decimal("0")
    return current, prior


def _primary_transaction_entry(group: list[LedgerEntry]) -> LedgerEntry:
    non_cash_entries = [
        entry for entry in group if not _is_cash_or_control_account(entry.account_name)
    ]
    candidates = non_cash_entries or group
    return max(candidates, key=lambda entry: max(abs(entry.debits), abs(entry.credits)))


def _is_cash_or_control_account(account_name: str) -> bool:
    normalized = account_name.lower()
    return any(
        term in normalized
        for term in (
            "bank",
            "cash",
            "credit union",
            "debit card",
            "master card",
            "visa card",
        )
    )


def _line_current(lines: list[ComparativeLine], label: str) -> Decimal | None:
    target = label.upper()
    for line in lines:
        if line.label.strip().upper() == target and line.current is not None:
            return line.current
    return None


def _is_total_line(label: str) -> bool:
    return label.strip().upper().startswith("TOTAL ")


def _total_section_name(label: str) -> str:
    return label.strip().upper().removeprefix("TOTAL ").strip()


def _statement_area_map(lines: list[ComparativeLine]) -> dict[tuple[str, str], str]:
    areas: dict[tuple[str, str], str] = {}
    current_area = "REVENUE"

    for line in lines:
        label = line.label.strip().upper()
        if label in {"NET INCOME", "NET LOSS"}:
            areas[(line.section, line.label)] = "NET RESULT"
            continue
        if label == "TOTAL REVENUE":
            areas[(line.section, line.label)] = "REVENUE"
            current_area = "EXPENSE"
            continue
        if label == "TOTAL EXPENSE":
            areas[(line.section, line.label)] = "EXPENSE"
            continue
        areas[(line.section, line.label)] = current_area

    return areas


def _variance_key(variance: Variance) -> tuple[str, str]:
    return variance.section, variance.label


def _representative_variances_by_section(variances: list[Variance]) -> list[Variance]:
    by_section: dict[str, list[Variance]] = {}
    for variance in variances:
        by_section.setdefault(variance.section.strip().upper(), []).append(variance)

    representatives: list[Variance] = []
    for section_variances in by_section.values():
        total = next(
            (variance for variance in section_variances if _is_total_line(variance.label)),
            None,
        )
        if total is not None:
            representatives.append(total)
            continue
        representatives.append(
            max(section_variances, key=lambda variance: abs(variance.change))
        )

    return representatives


def _find_variance_group(groups: list[VarianceGroup], label: str) -> VarianceGroup | None:
    target = label.strip().upper()
    for group in groups:
        if group.summary.label.strip().upper() == target:
            return group
    return None


def _variance_snapshot_line(area: str, group: VarianceGroup) -> str:
    direction = "up" if group.summary.change > 0 else "down"
    verb = "are" if area.endswith("s") else "is"
    line = (
        f"{area} {verb} {direction} {_currency(abs(group.summary.change))} "
        "from the comparison period"
    )
    if group.drivers:
        drivers = ", ".join(_display_label(driver.label) for driver in group.drivers[:3])
        line = f"{line}, mainly driven by {drivers}"
    return f"{line}."


def _display_label(label: str) -> str:
    stripped = label.strip()
    if stripped.upper().startswith("TOTAL "):
        return stripped[6:].title()
    return stripped
