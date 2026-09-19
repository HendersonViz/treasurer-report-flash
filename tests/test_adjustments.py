from datetime import date
from decimal import Decimal

import pytest

from treasurer_flash_report.adjustments import apply_journal_entries
from treasurer_flash_report.models import ComparativeLine, JournalEntry, JournalLine


def test_balanced_entry_updates_details_rollups_net_and_percentages() -> None:
    income = [
        ComparativeLine("REVENUE", "Donations", Decimal("1000"), Decimal("800")),
        ComparativeLine("REVENUE", "TOTAL REVENUE", Decimal("1000"), Decimal("800")),
        ComparativeLine("ADMIN", "Repairs", Decimal("200"), Decimal("100")),
        ComparativeLine("ADMIN", "TOTAL ADMIN", Decimal("200"), Decimal("100")),
        ComparativeLine("EXPENSE", "TOTAL EXPENSE", Decimal("200"), Decimal("100")),
        ComparativeLine("NET RESULT", "NET INCOME", Decimal("800"), Decimal("700")),
    ]
    balance = [
        ComparativeLine("CURRENT LIABILITIES", "Accounts Payable", Decimal("50"), Decimal("25")),
        ComparativeLine(
            "CURRENT LIABILITIES", "TOTAL CURRENT LIABILITIES", Decimal("50"), Decimal("25")
        ),
        ComparativeLine("LIABILITIES", "TOTAL LIABILITIES", Decimal("50"), Decimal("25")),
    ]
    entry = JournalEntry(
        date(2026, 9, 18),
        "Late invoice",
        [
            JournalLine("income", "Repairs", debit=Decimal("125")),
            JournalLine("balance", "Accounts Payable", credit=Decimal("125")),
        ],
    )

    adjusted_income, adjusted_balance = apply_journal_entries(income, balance, [entry])

    assert adjusted_income[2].current == Decimal("325")
    assert adjusted_income[3].current == Decimal("325")
    assert adjusted_income[4].current == Decimal("325")
    assert adjusted_income[5].current == Decimal("675")
    assert adjusted_income[2].percent_change == Decimal("225.00")
    assert adjusted_balance[0].current == Decimal("175")
    assert adjusted_balance[1].current == Decimal("175")
    assert adjusted_balance[2].current == Decimal("175")


def test_adjustment_requires_section_for_duplicate_account_name() -> None:
    income = [
        ComparativeLine("PROGRAM A", "Supplies", Decimal("1"), Decimal("1")),
        ComparativeLine("PROGRAM B", "Supplies", Decimal("2"), Decimal("2")),
    ]
    entry = JournalEntry(
        date(2026, 9, 18),
        "Correction",
        [JournalLine("income", "Supplies", debit=Decimal("10"))],
    )

    with pytest.raises(ValueError, match="Ambiguous.*add its section"):
        apply_journal_entries(income, [], [entry])


def test_adjustment_rejects_aggregate_target() -> None:
    income = [ComparativeLine("EXPENSE", "TOTAL EXPENSE", Decimal("20"), Decimal("10"))]
    entry = JournalEntry(
        date(2026, 9, 18),
        "Correction",
        [JournalLine("income", "TOTAL EXPENSE", debit=Decimal("10"))],
    )

    with pytest.raises(ValueError, match="detail account"):
        apply_journal_entries(income, [], [entry])
