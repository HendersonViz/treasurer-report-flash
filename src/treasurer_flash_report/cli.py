from __future__ import annotations

import argparse
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

from .builder import (
    DEFAULT_VARIANCE_AMOUNT_THRESHOLD,
    DEFAULT_VARIANCE_PERCENT_THRESHOLD,
    build_flash_report,
)
from .reports import render_html, write_pdf

DEFAULT_INPUT_DIR = Path("data/training")
DEFAULT_OUTPUT_DIR = Path("reports/out")
DEFAULT_INCOME_FILENAME = "IncomeApr26.xlsx"
DEFAULT_BALANCE_FILENAME = "BalanceApr26.xlsx"
DEFAULT_NOTES_FILENAME = "notes.md"
DEFAULT_HTML_FILENAME = "flash-report.html"
DEFAULT_PDF_FILENAME = "flash-report.pdf"


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        paths = _resolve_paths(args)
        if args.command == "doctor":
            return doctor(paths, args.deliverable)

        amount_threshold = _decimal_arg(args.variance_amount_threshold)
        percent_threshold = _decimal_arg(args.variance_percent_threshold)
        report = build_flash_report(
            income_path=paths.income,
            balance_path=paths.balance,
            notes_path=paths.notes,
            variance_amount_threshold=amount_threshold,
            variance_percent_threshold=percent_threshold,
        )

        wrote_html = False
        wrote_pdf = False
        if args.deliverable in ("html", "both"):
            paths.html_output.parent.mkdir(parents=True, exist_ok=True)
            paths.html_output.write_text(render_html(report), encoding="utf-8")
            wrote_html = True

        if args.deliverable in ("pdf", "both"):
            paths.pdf_output.parent.mkdir(parents=True, exist_ok=True)
            write_pdf(report, paths.pdf_output)
            wrote_pdf = True
    except Exception as exc:
        print(f"treasurer-flash-report: {exc}", file=sys.stderr)
        return 1

    if wrote_html:
        print(f"Wrote HTML report: {paths.html_output}")
    if wrote_pdf:
        print(f"Wrote PDF report: {paths.pdf_output}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="treasurer-flash-report",
        description="Generate a board-ready flash report from Sage 50 income and balance exports.",
    )
    parser.add_argument(
        "command",
        nargs="?",
        choices=("report", "doctor"),
        default="report",
        help="Use 'doctor' to check expected files and outputs without generating a report.",
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=DEFAULT_INPUT_DIR,
        help=(
            "Folder containing Sage dump files. Defaults to data/training and expects "
            f"{DEFAULT_INCOME_FILENAME}, {DEFAULT_BALANCE_FILENAME}, and optional "
            f"{DEFAULT_NOTES_FILENAME}."
        ),
    )
    parser.add_argument(
        "--deliverable",
        choices=("html", "pdf", "both"),
        default="html",
        help="Report deliverable to generate.",
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
    parser.add_argument("--output", type=Path, help="HTML output path override")
    parser.add_argument("--pdf", type=Path, help="PDF output path override")
    parser.add_argument(
        "--variance-amount-threshold",
        default=str(DEFAULT_VARIANCE_AMOUNT_THRESHOLD),
        help="Dollar threshold for major variance detection",
    )
    parser.add_argument(
        "--variance-percent-threshold",
        default=str(DEFAULT_VARIANCE_PERCENT_THRESHOLD),
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
        notes: Path | None,
        default_notes: Path,
        html_output: Path,
        pdf_output: Path,
    ) -> None:
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.income = income
        self.balance = balance
        self.notes = notes
        self.default_notes = default_notes
        self.html_output = html_output
        self.pdf_output = pdf_output


def doctor(paths: CliPaths, deliverable: str) -> int:
    print(f"Input folder: {paths.input_dir}")
    print()
    print("Found:")
    required = [(DEFAULT_INCOME_FILENAME, paths.income), (DEFAULT_BALANCE_FILENAME, paths.balance)]
    missing_required = False
    for label, path in required:
        if path.exists():
            print(f"OK {label}")
        else:
            print(f"MISSING {label} ({path})")
            missing_required = True

    notes_path = paths.notes or paths.default_notes
    if notes_path.exists():
        print(f"OK {notes_path.name}")
    else:
        print(f"optional {DEFAULT_NOTES_FILENAME} not found")

    print()
    print("Will write:")
    if deliverable in ("html", "both"):
        print(paths.html_output)
    if deliverable in ("pdf", "both"):
        print(paths.pdf_output)

    return 1 if missing_required else 0


def _resolve_paths(args: argparse.Namespace) -> CliPaths:
    input_dir = args.input_dir
    output_dir = args.output_dir
    default_notes = input_dir / DEFAULT_NOTES_FILENAME
    notes_path = args.notes
    if notes_path is None and default_notes.exists():
        notes_path = default_notes

    return CliPaths(
        input_dir=input_dir,
        output_dir=output_dir,
        income=args.income or input_dir / DEFAULT_INCOME_FILENAME,
        balance=args.balance or input_dir / DEFAULT_BALANCE_FILENAME,
        notes=notes_path,
        default_notes=default_notes,
        html_output=args.output or output_dir / DEFAULT_HTML_FILENAME,
        pdf_output=args.pdf or output_dir / DEFAULT_PDF_FILENAME,
    )


def _decimal_arg(value: str) -> Decimal:
    try:
        return Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"Expected decimal threshold, got {value!r}") from exc


if __name__ == "__main__":
    raise SystemExit(main())
