from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from .models import ComparativeLine, JournalEntry, JournalLine


def apply_journal_entries(
    income_statement: list[ComparativeLine],
    balance_sheet: list[ComparativeLine],
    entries: list[JournalEntry],
) -> tuple[list[ComparativeLine], list[ComparativeLine]]:
    income_deltas: dict[int, Decimal] = {}
    balance_deltas: dict[int, Decimal] = {}

    for entry in entries:
        for journal_line in entry.lines:
            lines = income_statement if journal_line.statement == "income" else balance_sheet
            deltas = income_deltas if journal_line.statement == "income" else balance_deltas
            index = _match_line(lines, journal_line)
            normal_balance = journal_line.normal_balance or _infer_normal_balance(
                lines, index, journal_line.statement
            )
            delta = journal_line.debit - journal_line.credit
            if normal_balance == "credit":
                delta = -delta
            _add_delta(deltas, index, delta)
            _add_rollup_deltas(lines, deltas, index, delta, journal_line.statement)

    return _apply_deltas(income_statement, income_deltas), _apply_deltas(
        balance_sheet, balance_deltas
    )


def _match_line(lines: list[ComparativeLine], journal_line: JournalLine) -> int:
    account = _normalized(journal_line.account)
    section = _normalized(journal_line.section) if journal_line.section else None
    matches = [
        index
        for index, line in enumerate(lines)
        if _normalized(line.label) == account
        and (section is None or _normalized(line.section) == section)
    ]
    location = f"{journal_line.statement} statement account {journal_line.account!r}"
    if not matches:
        raise ValueError(f"Could not find {location}")
    if len(matches) > 1:
        raise ValueError(f"Ambiguous {location}; add its section to report.yaml")
    index = matches[0]
    label = lines[index].label.strip().upper()
    if label.startswith("TOTAL ") or label in {"NET INCOME", "NET LOSS"}:
        raise ValueError(f"Adjust a detail account, not aggregate line {lines[index].label!r}")
    return index


def _infer_normal_balance(
    lines: list[ComparativeLine], index: int, statement: str
) -> str:
    line = lines[index]
    if statement == "income":
        area = _income_area(lines, index)
        return "credit" if area == "revenue" else "debit"

    section = line.section.upper()
    if "ASSET" in section:
        return "debit"
    if "LIABIL" in section or "EQUITY" in section or "CAPITAL" in section:
        return "credit"
    raise ValueError(
        f"Cannot infer normal balance for {line.label!r} in section {line.section!r}; "
        "set normal_balance in report.yaml"
    )


def _income_area(lines: list[ComparativeLine], target_index: int) -> str:
    area = "revenue"
    for index, line in enumerate(lines):
        label = line.label.strip().upper()
        if label == "TOTAL REVENUE":
            if index == target_index:
                return "revenue"
            area = "expense"
            continue
        if index == target_index:
            return area
    return area


def _add_rollup_deltas(
    lines: list[ComparativeLine],
    deltas: dict[int, Decimal],
    target_index: int,
    delta: Decimal,
    statement: str,
) -> None:
    target = lines[target_index]
    labels: set[str] = {f"TOTAL {_normalized(target.section).upper()}"}
    if statement == "income":
        area = _income_area(lines, target_index)
        labels.add("TOTAL REVENUE" if area == "revenue" else "TOTAL EXPENSE")
        for index, line in enumerate(lines):
            if line.label.strip().upper() in {"NET INCOME", "NET LOSS"}:
                net_delta = delta if area == "revenue" else -delta
                _add_delta(deltas, index, net_delta)
    else:
        section = target.section.upper()
        if "ASSET" in section:
            labels.add("TOTAL ASSETS")
        elif "LIABIL" in section:
            labels.update({"TOTAL LIABILITIES", "TOTAL LIABILITIES AND EQUITY"})
        elif "EQUITY" in section or "CAPITAL" in section:
            labels.update({"TOTAL EQUITY", "TOTAL LIABILITIES AND EQUITY"})

    for index, line in enumerate(lines):
        if index != target_index and line.label.strip().upper() in labels:
            _add_delta(deltas, index, delta)


def _apply_deltas(
    lines: list[ComparativeLine], deltas: dict[int, Decimal]
) -> list[ComparativeLine]:
    adjusted: list[ComparativeLine] = []
    for index, line in enumerate(lines):
        if index not in deltas:
            adjusted.append(line)
            continue
        current = (line.current or Decimal("0")) + deltas[index]
        percent_change = None
        if line.prior not in (None, Decimal("0")):
            percent_change = ((current - line.prior) / abs(line.prior) * 100).quantize(
                Decimal("0.01")
            )
        adjusted.append(replace(line, current=current, percent_change=percent_change))
    return adjusted


def _add_delta(deltas: dict[int, Decimal], index: int, value: Decimal) -> None:
    deltas[index] = deltas.get(index, Decimal("0")) + value


def _normalized(value: str | None) -> str:
    return " ".join((value or "").split()).casefold()
