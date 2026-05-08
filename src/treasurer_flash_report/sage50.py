from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import pandas as pd

from .models import ChequeLogRow, ComparativeLine, LedgerEntry, TrialBalanceRow

EXCEL_EPOCH = datetime(1899, 12, 30)


class Sage50WorkbookParser:
    """Parser for the Sage 50 workbook shapes observed in data/training."""

    def read_sheet(self, path: str | Path) -> pd.DataFrame:
        return pd.read_excel(path, sheet_name="Sheet1", header=None, engine="openpyxl")

    def read_report_heading(self, path: str | Path) -> tuple[str, str]:
        df = self.read_sheet(path)
        organization_name = _text(df.iat[0, 0]) if len(df.index) > 0 else None
        report_title = _text(df.iat[1, 0]) if len(df.index) > 1 else None
        return organization_name or "Organization", report_title or "Treasurer Flash Report"

    def read_comparative_periods(self, path: str | Path) -> tuple[str | None, str | None]:
        df = self.read_sheet(path)
        if len(df.index) <= 3:
            return None, None
        current_period = _text(df.iat[3, 1]) if len(df.columns) > 1 else None
        comparative_period = _text(df.iat[3, 3]) if len(df.columns) > 3 else None
        return current_period, comparative_period

    def parse_balance_sheet(self, path: str | Path) -> list[ComparativeLine]:
        return self._parse_comparative_report(path, has_percent_change=False)

    def parse_income_statement(self, path: str | Path) -> list[ComparativeLine]:
        return self._parse_comparative_report(path, has_percent_change=True)

    def parse_trial_balance(self, path: str | Path) -> list[TrialBalanceRow]:
        df = self.read_sheet(path)
        header_idx = self._find_row(df, "Account Number")
        rows: list[TrialBalanceRow] = []

        for _, row in df.iloc[header_idx + 1 :].iterrows():
            account_number = _text(row.get(0))
            account_description = _text(row.get(1))
            if not account_number or account_number.startswith("Generated On"):
                continue
            rows.append(
                TrialBalanceRow(
                    account_number=account_number,
                    account_description=account_description or "",
                    debits=_money(row.get(2)),
                    credits=_money(row.get(3)),
                )
            )

        return rows

    def parse_general_ledger(self, path: str | Path) -> list[LedgerEntry]:
        df = self.read_sheet(path)
        entries: list[LedgerEntry] = []
        current_account_number: str | None = None
        current_account_name: str | None = None

        for _, row in df.iloc[4:].iterrows():
            first = _text(row.get(0))
            second = _text(row.get(1))
            transaction_date = _excel_date(row.get(2))

            if first and second and transaction_date is None:
                current_account_number = first
                current_account_name = second
                continue

            if current_account_number is None or current_account_name is None:
                continue
            if transaction_date is None:
                continue

            entries.append(
                LedgerEntry(
                    account_number=current_account_number,
                    account_name=current_account_name,
                    transaction_date=transaction_date,
                    comment=_text(row.get(3)),
                    source_number=_text(row.get(4)),
                    journal_entry=_text(row.get(5)),
                    debits=_money(row.get(6)),
                    credits=_money(row.get(7)),
                    balance=_money(row.get(8)),
                    balance_type=_text(row.get(9)),
                )
            )

        return entries

    def parse_cheque_log(self, path: str | Path) -> list[ChequeLogRow]:
        df = self.read_sheet(path)
        header_idx = self._find_row(df, "Cheque No.")
        rows: list[ChequeLogRow] = []

        for _, row in df.iloc[header_idx + 1 :].iterrows():
            cheque_number = _text(row.get(0))
            if not cheque_number or cheque_number.startswith("Generated On"):
                continue

            rows.append(
                ChequeLogRow(
                    cheque_number=cheque_number,
                    cheque_type=_text(row.get(1)) or "",
                    payee=_text(row.get(2)) or "",
                    amount=_money(row.get(3)),
                    cheque_date=_required_date(row.get(4)),
                    times_printed=int(_money(row.get(5))),
                    entered_into_system=(_text(row.get(6)) or "").lower() == "yes",
                    journal_entry=_text(row.get(7)),
                    journal_entry_date=_excel_date(row.get(8)),
                )
            )

        return rows

    def _parse_comparative_report(
        self, path: str | Path, *, has_percent_change: bool
    ) -> list[ComparativeLine]:
        df = self.read_sheet(path)
        lines: list[ComparativeLine] = []
        section = ""

        for _, row in df.iloc[4:].iterrows():
            label = _text(row.get(0))
            if not label or label.startswith("Generated On"):
                continue

            current = _first_money(row.get(1), row.get(2))
            prior = _first_money(row.get(3), row.get(4))
            percent = _optional_money(row.get(5)) if has_percent_change else None

            if current is None and prior is None and _looks_like_section(label):
                section = label
                continue

            if current is None and prior is None:
                continue

            lines.append(
                ComparativeLine(
                    section=_section_for_line(label, section),
                    label=label,
                    current=current,
                    prior=prior,
                    percent_change=percent,
                )
            )

        return lines

    @staticmethod
    def _find_row(df: pd.DataFrame, needle: str) -> int:
        target = needle.strip().lower()
        for idx, row in df.iterrows():
            values = {_text(value).strip().lower() for value in row if _text(value)}
            if target in values:
                return int(idx)
        raise ValueError(f"Could not find header row containing {needle!r}")


def _text(value: Any) -> str | None:
    if pd.isna(value):
        return None
    text = str(value).strip()
    return text or None


def _money(value: Any) -> Decimal:
    amount = _optional_money(value)
    return amount if amount is not None else Decimal("0")


def _optional_money(value: Any) -> Decimal | None:
    if pd.isna(value):
        return None
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return None


def _first_money(*values: Any) -> Decimal | None:
    for value in values:
        amount = _optional_money(value)
        if amount is not None:
            return amount
    return None


def _excel_date(value: Any) -> date | None:
    if pd.isna(value):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        serial = int(value)
    except (TypeError, ValueError):
        return None
    return (EXCEL_EPOCH + timedelta(days=serial)).date()


def _required_date(value: Any) -> date:
    parsed = _excel_date(value)
    if parsed is None:
        raise ValueError(f"Expected Excel serial date, got {value!r}")
    return parsed


def _looks_like_section(label: str) -> bool:
    letters = [char for char in label if char.isalpha()]
    return bool(letters) and label.upper() == label


def _section_for_line(label: str, current_section: str) -> str:
    normalized = label.strip().upper()
    if normalized == "TOTAL REVENUE":
        return "REVENUE"
    if normalized == "TOTAL EXPENSE":
        return "EXPENSE"
    if normalized in {"NET INCOME", "NET LOSS"}:
        return "NET RESULT"
    return current_section
