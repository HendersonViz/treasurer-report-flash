from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .sage50 import Sage50WorkbookParser

WORKBOOK_TYPES = ("income", "balance", "ledger", "trial", "cheque_log")


@dataclass(frozen=True)
class WorkbookPackage:
    income: Path
    balance: Path
    ledger: Path | None = None
    trial: Path | None = None
    cheque_log: Path | None = None
    unsupported: tuple[Path, ...] = ()


def create_meeting_workspace(meeting_date: date, meetings_dir: Path = Path("meetings")) -> Path:
    meeting_dir = meetings_dir / meeting_date.isoformat()
    source_dir = meeting_dir / "source"
    output_dir = meeting_dir / "output"
    source_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    config_path = meeting_dir / "report.yaml"
    if config_path.exists():
        raise ValueError(
            f"Meeting workspace already exists: {meeting_dir}. "
            "Existing report.yaml was not changed."
        )
    config_path.write_text(_config_template(meeting_date), encoding="utf-8")
    return meeting_dir


def discover_workbooks(source_dir: Path) -> WorkbookPackage:
    if not source_dir.is_dir():
        raise ValueError(f"Missing source folder: {source_dir}")
    found: dict[str, list[Path]] = {kind: [] for kind in WORKBOOK_TYPES}
    unsupported: list[Path] = []
    parser = Sage50WorkbookParser()

    for path in sorted(source_dir.glob("*.xlsx")):
        try:
            kind = classify_workbook(path, parser)
        except Exception as exc:
            raise ValueError(f"Could not inspect workbook {path.name}: {exc}") from exc
        if kind is None:
            unsupported.append(path)
        else:
            found[kind].append(path)

    for kind, paths in found.items():
        if len(paths) > 1:
            names = ", ".join(path.name for path in paths)
            raise ValueError(f"Multiple {kind.replace('_', ' ')} workbooks found: {names}")
    missing = [kind for kind in ("income", "balance") if not found[kind]]
    if missing:
        labels = ", ".join(kind.replace("_", " ") for kind in missing)
        raise ValueError(f"Missing required workbook(s): {labels} in {source_dir}")

    return WorkbookPackage(
        income=found["income"][0],
        balance=found["balance"][0],
        ledger=_optional_path(found["ledger"]),
        trial=_optional_path(found["trial"]),
        cheque_log=_optional_path(found["cheque_log"]),
        unsupported=tuple(unsupported),
    )


def classify_workbook(path: Path, parser: Sage50WorkbookParser | None = None) -> str | None:
    parser = parser or Sage50WorkbookParser()
    frame = parser.read_sheet(path)
    title = ""
    if len(frame.index) > 1 and len(frame.columns) > 0:
        value = frame.iat[1, 0]
        title = "" if value is None else str(value).strip().casefold()
    title_rules = (
        ("income statement", "income"),
        ("balance sheet", "balance"),
        ("trial balance", "trial"),
        ("general ledger", "ledger"),
        ("cheque log", "cheque_log"),
        ("check log", "cheque_log"),
    )
    for phrase, kind in title_rules:
        if phrase in title:
            return kind

    visible = {
        str(value).strip().casefold()
        for value in frame.iloc[:12].to_numpy().ravel()
        if value is not None and str(value).strip()
    }
    if "cheque no." in visible:
        return "cheque_log"
    if "account number" in visible and {"debits", "credits"}.issubset(visible):
        return "trial"
    if {"source #", "journal entry", "balance"}.issubset(visible):
        return "ledger"
    return None


def _optional_path(paths: list[Path]) -> Path | None:
    return paths[0] if paths else None


def _config_template(meeting_date: date) -> str:
    return f'''# Treasurer Flash Report configuration
meeting_date: {meeting_date.isoformat()}
deliverables: [html, pdf]

variance:
  amount: 5000
  percent: 15

notes:
  # Leave blank to generate this summary automatically.
  executive_snapshot: ""
  # Basic Markdown is supported. Use | for a multi-line note.
  treasurer_notes: ""
  risks_and_issues: []
  decisions_needed: []

# Each adjustment must balance. Account names must match detail lines in the
# income statement or balance sheet. Add section when a name occurs twice.
adjustments: []
# Example:
# adjustments:
#   - date: {meeting_date.isoformat()}
#     description: Accrue an invoice received after the Sage export
#     lines:
#       - statement: income
#         account: Repairs and Maintenance
#         debit: 1250.00
#       - statement: balance
#         account: Accounts Payable
#         credit: 1250.00
'''
