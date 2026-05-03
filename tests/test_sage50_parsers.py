from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from treasurer_flash_report.sage50 import Sage50WorkbookParser

TRAINING_DIR = Path("data/training")


pytestmark = pytest.mark.skipif(
    not TRAINING_DIR.exists() or not any(TRAINING_DIR.glob("*.xlsx")),
    reason="training workbooks are local-only and ignored by git",
)


def test_balance_sheet_comparative_spacer_columns_are_ignored() -> None:
    parser = Sage50WorkbookParser()

    rows = parser.parse_balance_sheet(TRAINING_DIR / "BalanceApr26.xlsx")

    bank = next(row for row in rows if row.label == "Bank")
    assert bank.section == "CURRENT ASSETS"
    assert bank.current == Decimal("90441.56")
    assert bank.prior == Decimal("37628.07")


def test_income_statement_percent_change_column_is_parsed() -> None:
    parser = Sage50WorkbookParser()

    rows = parser.parse_income_statement(TRAINING_DIR / "IncomeApr26.xlsx")

    one_game = next(row for row in rows if row.label == "1 Game/Wk")
    assert one_game.section == "MEMBERSHIP"
    assert one_game.prior == Decimal("88843.87")
    assert one_game.percent_change == Decimal("-100.00")


def test_trial_balance_flat_table_starts_after_report_headers() -> None:
    parser = Sage50WorkbookParser()

    rows = parser.parse_trial_balance(TRAINING_DIR / "TrialApr26.xlsx")

    assert rows[0].account_number == "1030"
    assert rows[0].account_description == "Cash Float - Bar"
    assert rows[0].debits == Decimal("1200.00")


def test_general_ledger_carries_account_header_to_sparse_detail_rows() -> None:
    parser = Sage50WorkbookParser()

    entries = parser.parse_general_ledger(TRAINING_DIR / "LedgerApr26.xlsx")

    debit_card = next(entry for entry in entries if entry.account_number == "1170")
    assert debit_card.account_name == "Debit Card Transactions"
    assert debit_card.transaction_date == date(2026, 4, 15)
    assert debit_card.source_number == "DSR APRIL 15/26"
    assert debit_card.debits == Decimal("112.33")


def test_cheque_log_converts_excel_serial_dates() -> None:
    parser = Sage50WorkbookParser()

    rows = parser.parse_cheque_log(TRAINING_DIR / "ChqLogApr26.xlsx")

    assert rows[0].cheque_number == "14584"
    assert rows[0].cheque_date == date(2026, 4, 8)
    assert rows[0].entered_into_system is True
