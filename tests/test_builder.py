from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from treasurer_flash_report.builder import build_flash_report, find_major_variances, read_notes
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
    ]

    variances = find_major_variances(
        rows,
        amount_threshold=Decimal("5000"),
        percent_threshold=Decimal("15"),
    )

    assert [variance.label for variance in variances] == ["Large change"]
    assert variances[0].change == Decimal("10000")
    assert variances[0].percent_change == Decimal("100.00")


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
        notes_path=notes_path,
    )

    assert report.organization_name == "Dartmouth Curling Club"
    assert report.income_statement
    assert report.balance_sheet
    assert report.major_variances
    assert report.decisions_needed == ["Board approval requested for capital spending."]
    assert "Revenue is" in report.commentary[0]
