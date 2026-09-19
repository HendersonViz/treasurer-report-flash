from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from treasurer_flash_report.config import load_report_config
from treasurer_flash_report.workspace import create_meeting_workspace, discover_workbooks


def _write_workbook(path: Path, title: str) -> None:
    pd.DataFrame([["Example Club"], [title]]).to_excel(
        path, sheet_name="Sheet1", header=False, index=False
    )


def test_create_workspace_writes_valid_template_without_overwriting(tmp_path: Path) -> None:
    meeting_dir = create_meeting_workspace(date(2026, 9, 20), tmp_path / "meetings")

    assert (meeting_dir / "source").is_dir()
    assert (meeting_dir / "output").is_dir()
    config = load_report_config(meeting_dir / "report.yaml")
    assert config.meeting_date == date(2026, 9, 20)
    assert config.deliverables == ("html", "pdf")

    with pytest.raises(ValueError, match="already exists"):
        create_meeting_workspace(date(2026, 9, 20), tmp_path / "meetings")


def test_discover_workbooks_uses_content_not_filenames(tmp_path: Path) -> None:
    _write_workbook(tmp_path / "first.xlsx", "Comparative Income Statement")
    _write_workbook(tmp_path / "second.xlsx", "Comparative Balance Sheet")
    _write_workbook(tmp_path / "extra.xlsx", "General Ledger")
    _write_workbook(tmp_path / "unknown.xlsx", "Supporting Schedule")

    package = discover_workbooks(tmp_path)

    assert package.income.name == "first.xlsx"
    assert package.balance.name == "second.xlsx"
    assert package.ledger is not None and package.ledger.name == "extra.xlsx"
    assert [path.name for path in package.unsupported] == ["unknown.xlsx"]


def test_discover_workbooks_rejects_duplicate_statement_type(tmp_path: Path) -> None:
    _write_workbook(tmp_path / "one.xlsx", "Income Statement")
    _write_workbook(tmp_path / "two.xlsx", "Comparative Income Statement")
    _write_workbook(tmp_path / "balance.xlsx", "Balance Sheet")

    with pytest.raises(ValueError, match="Multiple income workbooks"):
        discover_workbooks(tmp_path)
