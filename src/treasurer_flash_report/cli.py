from __future__ import annotations

import argparse
import sys
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from .builder import (
    DEFAULT_VARIANCE_AMOUNT_THRESHOLD,
    DEFAULT_VARIANCE_PERCENT_THRESHOLD,
    build_flash_report,
)
from .config import ReportConfig, load_report_config
from .reports import render_html, write_pdf
from .sample import build_sample_flash_report
from .workspace import create_meeting_workspace, discover_workbooks

DEFAULT_INPUT_DIR = Path("data/training")
DEFAULT_OUTPUT_DIR = Path("reports/out")
DEFAULT_INCOME_FILENAME = "IncomeApr26.xlsx"
DEFAULT_BALANCE_FILENAME = "BalanceApr26.xlsx"
DEFAULT_LEDGER_FILENAME = "LedgerApr26.xlsx"
DEFAULT_TRIAL_FILENAME = "TrialApr26.xlsx"
DEFAULT_CHEQUE_LOG_FILENAME = "ChqLogApr26.xlsx"
DEFAULT_NOTES_FILENAME = "notes.md"
DEFAULT_HTML_FILENAME = "flash-report.html"
DEFAULT_PDF_FILENAME = "flash-report.pdf"
DEFAULT_SAMPLE_HTML_FILENAME = "sample-flash-report.html"
DEFAULT_SAMPLE_PDF_FILENAME = "sample-flash-report.pdf"


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "init":
            if args.meeting is None:
                raise ValueError("init requires a meeting date in YYYY-MM-DD format")
            meeting_date = date.fromisoformat(args.meeting)
            meeting_dir = create_meeting_workspace(meeting_date, args.meetings_dir)
            print(f"Created meeting workspace: {meeting_dir}")
            print(f"Drop Sage .xlsx files into: {meeting_dir / 'source'}")
            print(f"Edit notes and adjustments in: {meeting_dir / 'report.yaml'}")
            return 0
        paths = _resolve_paths(args)
        if args.command == "doctor":
            result = doctor(paths, _deliverables(args, paths.config))
            if result != 0:
                return result
            _build_report(paths, args)
            print("OK workbooks parsed and adjustments validated")
            return 0

        if args.command == "sample":
            report = build_sample_flash_report()
        else:
            report = _build_report(paths, args)

        deliverables = _deliverables(args, paths.config)
        if "html" in deliverables:
            paths.html_output.parent.mkdir(parents=True, exist_ok=True)
            paths.html_output.write_text(render_html(report), encoding="utf-8")
            print(f"Wrote HTML report: {paths.html_output}")

        if "pdf" in deliverables:
            paths.pdf_output.parent.mkdir(parents=True, exist_ok=True)
            write_pdf(report, paths.pdf_output)
            print(f"Wrote PDF report: {paths.pdf_output}")
    except Exception as exc:
        print(f"treasurer-flash-report: {exc}", file=sys.stderr)
        return 1

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="treasurer-flash-report",
        description="Generate a board-ready flash report from Sage 50 income and balance exports.",
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="report",
        choices=("report", "doctor", "sample", "init"),
        help=(
            "Use 'doctor' to check expected files and outputs, or 'sample' to generate "
            "a synthetic shareable report."
        ),
    )
    parser.add_argument(
        "meeting",
        nargs="?",
        help=(
            "Meeting workspace path for report/doctor, or YYYY-MM-DD when using init."
        ),
    )
    parser.add_argument(
        "--meetings-dir",
        type=Path,
        default=Path("meetings"),
        help="Parent folder used by the init command.",
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=DEFAULT_INPUT_DIR,
        help=(
            "Folder containing Sage dump files. Defaults to data/training and expects "
            f"{DEFAULT_INCOME_FILENAME}, {DEFAULT_BALANCE_FILENAME}, and optional "
            f"{DEFAULT_LEDGER_FILENAME} and {DEFAULT_NOTES_FILENAME}."
        ),
    )
    parser.add_argument(
        "--deliverable",
        choices=("html", "pdf", "both"),
        default=None,
        help="Report deliverable override; meeting workspaces use report.yaml by default.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Folder for default generated outputs.",
    )
    parser.add_argument("--notes", type=Path, help="Markdown notes file override")
    parser.add_argument("--income", type=Path, help="Income statement override")
    parser.add_argument("--balance", type=Path, help="Balance sheet override")
    parser.add_argument("--ledger", type=Path, help="General ledger override")
    parser.add_argument("--output", type=Path, help="HTML output path override")
    parser.add_argument("--pdf", type=Path, help="PDF output path override")
    parser.add_argument(
        "--variance-amount-threshold",
        default=None,
        help="Dollar threshold for major variance detection",
    )
    parser.add_argument(
        "--variance-percent-threshold",
        default=None,
        help="Percent threshold for major variance detection",
    )
    return parser


class CliPaths:
    def __init__(
        self,
        *,
        input_dir: Path,
        output_dir: Path,
        income: Path,
        balance: Path,
        ledger: Path | None,
        trial: Path | None,
        cheque_log: Path | None,
        notes: Path | None,
        default_notes: Path,
        html_output: Path,
        pdf_output: Path,
        config: ReportConfig | None = None,
        unsupported: tuple[Path, ...] = (),
    ) -> None:
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.income = income
        self.balance = balance
        self.ledger = ledger
        self.trial = trial
        self.cheque_log = cheque_log
        self.notes = notes
        self.default_notes = default_notes
        self.html_output = html_output
        self.pdf_output = pdf_output
        self.config = config
        self.unsupported = unsupported


def doctor(paths: CliPaths, deliverables: tuple[str, ...]) -> int:
    print(f"Input folder: {paths.input_dir}")
    print()
    print("Found:")
    required = [(paths.income.name, paths.income), (paths.balance.name, paths.balance)]
    missing_required = False
    for label, path in required:
        if path.exists():
            print(f"OK {label}")
        else:
            print(f"MISSING {label} ({path})")
            missing_required = True

    notes_path = paths.notes or paths.default_notes
    ledger_path = paths.ledger or paths.input_dir / DEFAULT_LEDGER_FILENAME
    if paths.config is not None:
        print(f"OK report.yaml ({len(paths.config.adjustments)} adjustment(s))")
    elif notes_path.exists():
        print(f"OK {notes_path.name}")
    else:
        print(f"optional {DEFAULT_NOTES_FILENAME} not found")
    if ledger_path.exists():
        print(f"OK {ledger_path.name}")
    else:
        print(f"optional {DEFAULT_LEDGER_FILENAME} not found")
    for label, path in (
        (DEFAULT_TRIAL_FILENAME, paths.trial),
        (DEFAULT_CHEQUE_LOG_FILENAME, paths.cheque_log),
    ):
        if path is not None and path.exists():
            print(f"OK {path.name}")
        else:
            print(f"optional {label} not found")
    for path in paths.unsupported:
        print(f"IGNORED unsupported workbook: {path.name}")

    print()
    print("Will write:")
    if "html" in deliverables:
        print(paths.html_output)
    if "pdf" in deliverables:
        print(paths.pdf_output)

    return 1 if missing_required else 0


def _resolve_paths(args: argparse.Namespace) -> CliPaths:
    if args.meeting is not None:
        if args.command == "sample":
            raise ValueError("The sample command does not accept a meeting workspace")
        meeting_dir = Path(args.meeting)
        config = load_report_config(meeting_dir / "report.yaml")
        package = discover_workbooks(meeting_dir / "source")
        output_dir = (
            args.output_dir if args.output_dir != DEFAULT_OUTPUT_DIR else meeting_dir / "output"
        )
        return CliPaths(
            input_dir=meeting_dir / "source",
            output_dir=output_dir,
            income=package.income,
            balance=package.balance,
            ledger=package.ledger,
            trial=package.trial,
            cheque_log=package.cheque_log,
            notes=None,
            default_notes=meeting_dir / "notes.md",
            html_output=args.output or output_dir / DEFAULT_HTML_FILENAME,
            pdf_output=args.pdf or output_dir / DEFAULT_PDF_FILENAME,
            config=config,
            unsupported=package.unsupported,
        )

    input_dir = args.input_dir
    output_dir = args.output_dir
    default_notes = input_dir / DEFAULT_NOTES_FILENAME
    default_ledger = input_dir / DEFAULT_LEDGER_FILENAME
    default_trial = input_dir / DEFAULT_TRIAL_FILENAME
    default_cheque_log = input_dir / DEFAULT_CHEQUE_LOG_FILENAME
    notes_path = args.notes
    if notes_path is None and default_notes.exists():
        notes_path = default_notes
    ledger_path = args.ledger
    if ledger_path is None and default_ledger.exists():
        ledger_path = default_ledger

    return CliPaths(
        input_dir=input_dir,
        output_dir=output_dir,
        income=args.income or input_dir / DEFAULT_INCOME_FILENAME,
        balance=args.balance or input_dir / DEFAULT_BALANCE_FILENAME,
        ledger=ledger_path,
        trial=default_trial if default_trial.exists() else None,
        cheque_log=default_cheque_log if default_cheque_log.exists() else None,
        notes=notes_path,
        default_notes=default_notes,
        html_output=args.output or output_dir / _default_html_filename(args.command),
        pdf_output=args.pdf or output_dir / _default_pdf_filename(args.command),
    )


def _build_report(paths: CliPaths, args: argparse.Namespace):
    amount_threshold = _decimal_arg(
        args.variance_amount_threshold, DEFAULT_VARIANCE_AMOUNT_THRESHOLD
    )
    percent_threshold = _decimal_arg(
        args.variance_percent_threshold, DEFAULT_VARIANCE_PERCENT_THRESHOLD
    )
    if paths.config is not None:
        if args.variance_amount_threshold is None:
            amount_threshold = paths.config.variance_amount
        if args.variance_percent_threshold is None:
            percent_threshold = paths.config.variance_percent
    return build_flash_report(
        income_path=paths.income,
        balance_path=paths.balance,
        ledger_path=paths.ledger,
        notes_path=paths.notes,
        variance_amount_threshold=amount_threshold,
        variance_percent_threshold=percent_threshold,
        executive_snapshot_markdown=(
            paths.config.notes.executive_snapshot if paths.config else None
        ),
        notes_markdown=paths.config.notes.treasurer_notes if paths.config else None,
        manual_risks=paths.config.notes.risks_and_issues if paths.config else None,
        manual_decisions=paths.config.notes.decisions_needed if paths.config else None,
        adjustments=paths.config.adjustments if paths.config else None,
    )


def _decimal_arg(value: str | None, default: Decimal) -> Decimal:
    if value is None:
        return default
    try:
        return Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"Expected decimal threshold, got {value!r}") from exc


def _default_html_filename(command: str) -> str:
    if command == "sample":
        return DEFAULT_SAMPLE_HTML_FILENAME
    return DEFAULT_HTML_FILENAME


def _default_pdf_filename(command: str) -> str:
    if command == "sample":
        return DEFAULT_SAMPLE_PDF_FILENAME
    return DEFAULT_PDF_FILENAME


def _deliverables(args: argparse.Namespace, config: ReportConfig | None) -> tuple[str, ...]:
    if args.deliverable == "both":
        return ("html", "pdf")
    if args.deliverable is not None:
        return (args.deliverable,)
    if config is not None:
        return config.deliverables
    return ("html",)


if __name__ == "__main__":
    raise SystemExit(main())
