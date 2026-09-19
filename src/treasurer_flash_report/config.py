from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import yaml

from .builder import DEFAULT_VARIANCE_AMOUNT_THRESHOLD, DEFAULT_VARIANCE_PERCENT_THRESHOLD
from .models import JournalEntry, JournalLine


@dataclass(frozen=True)
class NotesConfig:
    executive_snapshot: str = ""
    treasurer_notes: str = ""
    risks_and_issues: list[str] = field(default_factory=list)
    decisions_needed: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ReportConfig:
    meeting_date: date
    deliverables: tuple[str, ...] = ("html", "pdf")
    variance_amount: Decimal = DEFAULT_VARIANCE_AMOUNT_THRESHOLD
    variance_percent: Decimal = DEFAULT_VARIANCE_PERCENT_THRESHOLD
    notes: NotesConfig = field(default_factory=NotesConfig)
    adjustments: list[JournalEntry] = field(default_factory=list)


def load_report_config(path: Path) -> ReportConfig:
    if not path.exists():
        raise ValueError(f"Missing report configuration: {path}")
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML in {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ValueError(f"Expected a YAML mapping in {path}")

    meeting_date = _date_value(raw.get("meeting_date"), "meeting_date")
    deliverables = _deliverables(raw.get("deliverables", ["html", "pdf"]))
    variance = _mapping(raw.get("variance", {}), "variance")
    notes = _notes_config(_mapping(raw.get("notes", {}), "notes"))
    adjustments_raw = raw.get("adjustments", [])
    if not isinstance(adjustments_raw, list):
        raise ValueError("adjustments must be a list")
    adjustments = [
        _journal_entry(item, index + 1) for index, item in enumerate(adjustments_raw)
    ]

    return ReportConfig(
        meeting_date=meeting_date,
        deliverables=deliverables,
        variance_amount=_decimal(
            variance.get("amount", DEFAULT_VARIANCE_AMOUNT_THRESHOLD), "variance.amount"
        ),
        variance_percent=_decimal(
            variance.get("percent", DEFAULT_VARIANCE_PERCENT_THRESHOLD), "variance.percent"
        ),
        notes=notes,
        adjustments=adjustments,
    )


def _notes_config(raw: dict[str, Any]) -> NotesConfig:
    return NotesConfig(
        executive_snapshot=_string(raw.get("executive_snapshot", ""), "notes.executive_snapshot"),
        treasurer_notes=_string(raw.get("treasurer_notes", ""), "notes.treasurer_notes"),
        risks_and_issues=_string_list(raw.get("risks_and_issues", []), "notes.risks_and_issues"),
        decisions_needed=_string_list(raw.get("decisions_needed", []), "notes.decisions_needed"),
    )


def _journal_entry(raw: Any, number: int) -> JournalEntry:
    item = _mapping(raw, f"adjustments[{number}]")
    description = _string(item.get("description"), f"adjustments[{number}].description").strip()
    if not description:
        raise ValueError(f"adjustments[{number}].description cannot be blank")
    lines_raw = item.get("lines")
    if not isinstance(lines_raw, list) or len(lines_raw) < 2:
        raise ValueError(f"adjustments[{number}].lines must contain at least two lines")
    lines = [_journal_line(line, number, index + 1) for index, line in enumerate(lines_raw)]
    debits = sum((line.debit for line in lines), Decimal("0"))
    credits = sum((line.credit for line in lines), Decimal("0"))
    if debits != credits:
        raise ValueError(
            f"Adjustment {number} is not balanced: debits {debits:.2f}, credits {credits:.2f}"
        )
    if debits == 0:
        raise ValueError(f"Adjustment {number} cannot have a zero total")
    return JournalEntry(
        entry_date=_date_value(item.get("date"), f"adjustments[{number}].date"),
        description=description,
        lines=lines,
    )


def _journal_line(raw: Any, entry_number: int, line_number: int) -> JournalLine:
    prefix = f"adjustments[{entry_number}].lines[{line_number}]"
    item = _mapping(raw, prefix)
    statement = _string(item.get("statement"), f"{prefix}.statement").strip().lower()
    statement = {"income_statement": "income", "balance_sheet": "balance"}.get(
        statement, statement
    )
    if statement not in {"income", "balance"}:
        raise ValueError(f"{prefix}.statement must be 'income' or 'balance'")
    account = _string(item.get("account"), f"{prefix}.account").strip()
    if not account:
        raise ValueError(f"{prefix}.account cannot be blank")
    has_debit = "debit" in item
    has_credit = "credit" in item
    if has_debit == has_credit:
        raise ValueError(f"{prefix} must contain exactly one of debit or credit")
    debit = _decimal(item["debit"], f"{prefix}.debit") if has_debit else Decimal("0")
    credit = _decimal(item["credit"], f"{prefix}.credit") if has_credit else Decimal("0")
    if debit < 0 or credit < 0:
        raise ValueError(f"{prefix} amounts cannot be negative")
    if debit == 0 and credit == 0:
        raise ValueError(f"{prefix} amount must be greater than zero")
    normal_balance = item.get("normal_balance")
    if normal_balance is not None:
        normal_balance = _string(normal_balance, f"{prefix}.normal_balance").strip().lower()
        if normal_balance not in {"debit", "credit"}:
            raise ValueError(f"{prefix}.normal_balance must be 'debit' or 'credit'")
    section = item.get("section")
    return JournalLine(
        statement=statement,
        account=account,
        debit=debit,
        credit=credit,
        section=_string(section, f"{prefix}.section").strip() if section is not None else None,
        normal_balance=normal_balance,
    )


def _deliverables(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise ValueError("deliverables must be a non-empty list")
    deliverables = tuple(str(item).strip().lower() for item in value)
    invalid = set(deliverables) - {"html", "pdf"}
    if invalid:
        raise ValueError(f"Unsupported deliverables: {', '.join(sorted(invalid))}")
    return tuple(dict.fromkeys(deliverables))


def _date_value(value: Any, field_name: str) -> date:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(f"{field_name} must use YYYY-MM-DD format") from exc
    raise ValueError(f"{field_name} must use YYYY-MM-DD format")


def _decimal(value: Any, field_name: str) -> Decimal:
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be a number")
    try:
        result = Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field_name} must be a number") from exc
    return result


def _mapping(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be a mapping")
    return value


def _string(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be text")
    return value


def _string_list(value: Any, field_name: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ValueError(f"{field_name} must be a list of text values")
    return [item.strip() for item in value if item.strip()]
