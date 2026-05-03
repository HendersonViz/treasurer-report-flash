from __future__ import annotations

from pathlib import Path

from treasurer_flash_report import cli


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
    assert "reports/out/flash-report.html" in output


def test_cli_doctor_fails_when_required_files_are_missing(tmp_path: Path, capsys) -> None:
    result = cli.main(["doctor", "--input-dir", str(tmp_path)])

    assert result == 1
    output = capsys.readouterr().out
    assert "MISSING IncomeApr26.xlsx" in output
    assert "MISSING BalanceApr26.xlsx" in output
