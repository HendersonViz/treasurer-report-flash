from __future__ import annotations

from pathlib import Path

import pandas as pd

from treasurer_flash_report import cli


def test_cli_init_creates_dated_meeting_workspace(tmp_path: Path) -> None:
    result = cli.main(
        ["init", "2026-09-20", "--meetings-dir", str(tmp_path / "meetings")]
    )

    assert result == 0
    meeting_dir = tmp_path / "meetings" / "2026-09-20"
    assert (meeting_dir / "source").is_dir()
    assert (meeting_dir / "output").is_dir()
    assert "meeting_date: 2026-09-20" in (meeting_dir / "report.yaml").read_text()


def test_cli_builds_meeting_workspace_with_adjustment(tmp_path: Path) -> None:
    meetings_dir = tmp_path / "meetings"
    assert cli.main(["init", "2026-09-20", "--meetings-dir", str(meetings_dir)]) == 0
    meeting_dir = meetings_dir / "2026-09-20"
    source_dir = meeting_dir / "source"
    _write_comparative_workbook(
        source_dir / "arbitrary-income-name.xlsx",
        "Comparative Income Statement",
        [
            ["REVENUE", None, None, None, None, None],
            ["Donations", 1000, None, 800, None, 25],
            ["TOTAL REVENUE", 1000, None, 800, None, 25],
            ["EXPENSE", None, None, None, None, None],
            ["Repairs", 200, None, 100, None, 100],
            ["TOTAL EXPENSE", 200, None, 100, None, 100],
            ["NET INCOME", 800, None, 700, None, None],
        ],
    )
    _write_comparative_workbook(
        source_dir / "arbitrary-balance-name.xlsx",
        "Comparative Balance Sheet",
        [
            ["CURRENT LIABILITIES", None, None, None, None, None],
            ["Accounts Payable", 50, None, 25, None, None],
            ["TOTAL CURRENT LIABILITIES", 50, None, 25, None, None],
        ],
    )
    (meeting_dir / "report.yaml").write_text(
        """meeting_date: 2026-09-20
deliverables: [html]
notes:
  executive_snapshot: ""
  treasurer_notes: "Invoice accrued after export."
  risks_and_issues: []
  decisions_needed: [Approve the repair overage.]
adjustments:
  - date: 2026-09-18
    description: Late repair invoice
    lines:
      - statement: income
        account: Repairs
        debit: 125
      - statement: balance
        account: Accounts Payable
        credit: 125
""",
        encoding="utf-8",
    )

    result = cli.main(["report", str(meeting_dir)])

    assert result == 0
    html = (meeting_dir / "output" / "flash-report.html").read_text(encoding="utf-8")
    assert "Late repair invoice" in html
    assert "Invoice accrued after export." in html
    assert "Approve the repair overage." in html
    assert "$675.00" in html


def _write_comparative_workbook(path: Path, title: str, data_rows: list[list[object]]) -> None:
    rows = [
        ["Example Club", None, None, None, None, None],
        [title, None, None, None, None, None],
        [None, None, None, None, None, None],
        [None, "Current", None, "Prior", None, "%"],
        *data_rows,
    ]
    pd.DataFrame(rows).to_excel(path, sheet_name="Sheet1", header=False, index=False)


def test_cli_writes_html_report_with_training_files(tmp_path: Path) -> None:
    training_dir = Path("data/training")
    if not any(training_dir.glob("*.xlsx")):
        return

    output_dir = tmp_path / "out"

    result = cli.main(
        [
            "--input-dir",
            str(training_dir),
            "--output-dir",
            str(output_dir),
            "--deliverable",
            "html",
        ]
    )

    assert result == 0
    output_path = output_dir / "flash-report.html"
    html = output_path.read_text(encoding="utf-8")
    assert "Dartmouth Curling Club" in html
    assert "Decisions Needed" in html
    assert "Significant Transactions" in html


def test_cli_keeps_explicit_path_overrides(tmp_path: Path) -> None:
    training_dir = Path("data/training")
    if not any(training_dir.glob("*.xlsx")):
        return

    notes_path = tmp_path / "notes.md"
    output_path = tmp_path / "report.html"
    notes_path.write_text("Decision: approve reserve transfer.\n", encoding="utf-8")

    result = cli.main(
        [
            "--income",
            str(training_dir / "IncomeApr26.xlsx"),
            "--balance",
            str(training_dir / "BalanceApr26.xlsx"),
            "--ledger",
            str(training_dir / "LedgerApr26.xlsx"),
            "--notes",
            str(notes_path),
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    assert "approve reserve transfer" in output_path.read_text(encoding="utf-8")


def test_cli_doctor_reports_expected_inputs_and_outputs(capsys) -> None:
    training_dir = Path("data/training")
    if not any(training_dir.glob("*.xlsx")):
        return

    result = cli.main(["doctor", "--input-dir", str(training_dir)])

    assert result == 0
    output = capsys.readouterr().out
    assert "Input folder: data/training" in output
    assert "OK IncomeApr26.xlsx" in output
    assert "OK BalanceApr26.xlsx" in output
    assert "OK LedgerApr26.xlsx" in output
    assert "reports/out/flash-report.html" in output


def test_cli_doctor_fails_when_required_files_are_missing(tmp_path: Path, capsys) -> None:
    result = cli.main(["doctor", "--input-dir", str(tmp_path)])

    assert result == 1
    output = capsys.readouterr().out
    assert "MISSING IncomeApr26.xlsx" in output
    assert "MISSING BalanceApr26.xlsx" in output
    assert "optional LedgerApr26.xlsx not found" in output


def test_cli_sample_writes_synthetic_shareable_html(tmp_path: Path) -> None:
    output_dir = tmp_path / "out"

    result = cli.main(["sample", "--output-dir", str(output_dir)])

    assert result == 0
    output_path = output_dir / "sample-flash-report.html"
    html = output_path.read_text(encoding="utf-8")
    assert "Hartwell Community Foundation" in html
    assert "SAMPLE REPORT - Synthetic data only" in html
    assert "synthetic data for demonstration purposes only" in html
    assert "Dartmouth Curling Club" not in html
    assert "data:image/jpeg;base64" not in html
    assert 'class="sample-logo"' in html
