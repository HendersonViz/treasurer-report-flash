from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

Money = Decimal


@dataclass(frozen=True)
class ComparativeLine:
    section: str
    label: str
    current: Money | None
    prior: Money | None
    percent_change: Decimal | None = None


@dataclass(frozen=True)
class Variance:
    section: str
    label: str
    current: Money
    prior: Money
    change: Money
    percent_change: Decimal | None


@dataclass(frozen=True)
class CashSummaryLine:
    label: str
    current: Money
    prior: Money


@dataclass(frozen=True)
class SignificantTransaction:
    transaction_date: date
    item: str
    description: str
    amount: Money


@dataclass(frozen=True)
class TrialBalanceRow:
    account_number: str
    account_description: str
    debits: Money
    credits: Money


@dataclass(frozen=True)
class LedgerEntry:
    account_number: str
    account_name: str
    transaction_date: date
    comment: str | None
    source_number: str | None
    journal_entry: str | None
    debits: Money
    credits: Money
    balance: Money
    balance_type: str | None


@dataclass(frozen=True)
class ChequeLogRow:
    cheque_number: str
    cheque_type: str
    payee: str
    amount: Money
    cheque_date: date
    times_printed: int
    entered_into_system: bool
    journal_entry: str | None
    journal_entry_date: date | None


@dataclass
class FlashReport:
    organization_name: str
    report_title: str
    current_period: str | None = None
    comparative_period: str | None = None
    balance_sheet_date: str | None = None
    comparative_balance_sheet_date: str | None = None
    treasurer_notes: list[str] = field(default_factory=list)
    income_statement: list[ComparativeLine] = field(default_factory=list)
    balance_sheet: list[ComparativeLine] = field(default_factory=list)
    cash_summary: list[CashSummaryLine] = field(default_factory=list)
    significant_transactions: list[SignificantTransaction] = field(default_factory=list)
    major_variances: list[Variance] = field(default_factory=list)
    risks_and_issues: list[str] = field(default_factory=list)
    decisions_needed: list[str] = field(default_factory=list)
    commentary: list[str] = field(default_factory=list)
    trial_balance: list[TrialBalanceRow] = field(default_factory=list)
    ledger_entries: list[LedgerEntry] = field(default_factory=list)
    cheque_log: list[ChequeLogRow] = field(default_factory=list)
