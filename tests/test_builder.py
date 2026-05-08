from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from treasurer_flash_report.builder import (
    build_cash_summary,
    build_flash_report,
    find_major_variances,
    find_significant_transactions,
    net_result,
    read_notes,
    section_total,
)
from treasurer_flash_report.models import ComparativeLine

TRAINING_DIR = Path("data/training")


def test_read_notes_accepts_markdown_paragraphs_and_bullets(tmp_path: Path) -> None:
    notes_path = tmp_path / "notes.md"
    notes_path.write_text(
        "# Treasurer Notes\n\nCash remains stable.\n\n- Board approval needed for roof work.\n",
        encoding="utf-8",
    )

    assert read_notes(notes_path) == [
        "Treasurer Notes",
        "Cash remains stable.",
        "Board approval needed for roof work.",
    ]


def test_find_major_variances_requires_amount_and_percent_thresholds() -> None:
    rows = [
        ComparativeLine("REVENUE", "Large change", Decimal("20000"), Decimal("10000"), None),
        ComparativeLine("REVENUE", "Small dollars", Decimal("110"), Decimal("10"), None),
        ComparativeLine("EXPENSE", "Small percent", Decimal("10600"), Decimal("10000"), None),
        ComparativeLine("NET RESULT", "NET INCOME", Decimal("50000"), Decimal("10000"), None),
    ]

    variances = find_major_variances(
        rows,
        amount_threshold=Decimal("5000"),
        percent_threshold=Decimal("15"),
    )

    assert [variance.label for variance in variances] == ["Large change"]
    assert variances[0].change == Decimal("10000")
    assert variances[0].percent_change == Decimal("100.00")


def test_income_summary_prefers_explicit_total_and_net_lines() -> None:
    rows = [
        ComparativeLine("MEMBERSHIP", "Dues", Decimal("75"), Decimal("50"), None),
        ComparativeLine("OTHER REVENUE", "Grant", Decimal("25"), Decimal("25"), None),
        ComparativeLine("OTHER REVENUE", "TOTAL REVENUE", Decimal("125"), Decimal("75"), None),
        ComparativeLine("ADMIN", "Supplies", Decimal("20"), Decimal("10"), None),
        ComparativeLine("ADMIN", "TOTAL EXPENSE", Decimal("40"), Decimal("20"), None),
        ComparativeLine("", "NET INCOME", Decimal("85"), Decimal("55"), None),
    ]

    assert section_total(rows, "REVENUE") == Decimal("125")
    assert section_total(rows, "EXPENSE") == Decimal("40")
    assert net_result(rows) == Decimal("85")


@pytest.mark.skipif(
    not TRAINING_DIR.exists() or not any(TRAINING_DIR.glob("*.xlsx")),
    reason="training workbooks are local-only and ignored by git",
)
def test_build_flash_report_from_income_and_balance_training_files(tmp_path: Path) -> None:
    notes_path = tmp_path / "notes.md"
    notes_path.write_text("- Board approval requested for capital spending.\n", encoding="utf-8")

    report = build_flash_report(
        income_path=TRAINING_DIR / "IncomeApr26.xlsx",
        balance_path=TRAINING_DIR / "BalanceApr26.xlsx",
        ledger_path=TRAINING_DIR / "LedgerApr26.xlsx",
        notes_path=notes_path,
    )

    assert report.organization_name == "Dartmouth Curling Club"
    assert report.current_period == "Actual 05/01/2025 to 04/30/2026"
    assert report.comparative_period == "Actual 05/01/2024 to 04/30/2025"
    assert report.balance_sheet_date == "As at 04/30/2026"
    assert report.comparative_balance_sheet_date == "As at 04/30/2025"
    assert report.income_statement
    assert report.balance_sheet
    assert len(report.cash_summary) == 5
    assert report.significant_transactions
    assert report.major_variances
    assert report.decisions_needed == ["Board approval requested for capital spending."]
    assert "Revenue is" in report.commentary[0]


@pytest.mark.skipif(
    not TRAINING_DIR.exists() or not any(TRAINING_DIR.glob("*.xlsx")),
    reason="training workbooks are local-only and ignored by git",
)
def test_cash_summary_is_calculated_from_balance_sheet_training_file() -> None:
    from treasurer_flash_report.sage50 import Sage50WorkbookParser

    parser = Sage50WorkbookParser()
    summary = build_cash_summary(parser.parse_balance_sheet(TRAINING_DIR / "BalanceApr26.xlsx"))

    assert [(line.label, line.current, line.prior) for line in summary] == [
        (
            "Operating Account + float + petty cash",
            Decimal("92094.26"),
            Decimal("39051.62"),
        ),
        ("Short Term Deposits (cashable)", Decimal("-20609.78"), Decimal("109695.11")),
        ("Locked in Term Deposits", Decimal("-49631.06"), Decimal("184.47")),
        ("Capital Reserve Fund (restricted)", Decimal("-72833.43"), Decimal("-87733.01")),
        ("Remainder (unrestricted funds)", Decimal("-50980.01"), Decimal("61198.19")),
    ]


@pytest.mark.skipif(
    not TRAINING_DIR.exists() or not any(TRAINING_DIR.glob("*.xlsx")),
    reason="training workbooks are local-only and ignored by git",
)
def test_significant_transactions_are_grouped_from_ledger_training_file() -> None:
    from treasurer_flash_report.sage50 import Sage50WorkbookParser

    parser = Sage50WorkbookParser()
    transactions = find_significant_transactions(
        parser.parse_general_ledger(TRAINING_DIR / "LedgerApr26.xlsx")
    )

    assert len(transactions) == 5
    assert transactions[0].item == "Accrued Liabilities"
    assert transactions[0].description == "ACCRUAL REVERSE 25"
    assert transactions[0].amount == Decimal("11041.02")
