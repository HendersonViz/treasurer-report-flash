# Treasurer Flash Report

Convert Sage 50 Excel exports into board-ready HTML and PDF flash reports for
volunteer treasurers and non-profit finance teams.

The product source of truth is `init-starter.txt`. The canonical import schema
is represented by local examples in `data/training/`, which are intentionally
ignored by git because they may contain financial data.

## Current Scope

- Parse Sage 50 `.xlsx` balance sheet, income statement, trial balance, general
  ledger, and cheque log exports.
- Normalize report headers, comparative spacer columns, Excel serial dates, and
  sparse/hierarchical ledger rows.
- Render an email-friendly HTML flash report with cash summary, major variances,
  significant ledger transactions, and period disclosure.
- Keep PDF generation optional through WeasyPrint so parsing can be tested
  independently.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev,pdf]"
```

## CLI MVP

Put the standard Sage dump files in one folder:

- `IncomeApr26.xlsx`
- `BalanceApr26.xlsx`
- optional `LedgerApr26.xlsx`
- optional `notes.md`

Check the folder before generating:

```bash
treasurer-flash-report doctor
```

Generate the default HTML report:

```bash
treasurer-flash-report
```

Choose a deliverable:

```bash
treasurer-flash-report --input-dir data/training --deliverable html
treasurer-flash-report --input-dir data/training --deliverable pdf
treasurer-flash-report --input-dir data/training --deliverable both
```

Outputs default to `reports/out/flash-report.html` and
`reports/out/flash-report.pdf`. Use `--output-dir` to change the folder, or
advanced overrides like `--income`, `--balance`, `--notes`, `--output`, and
`--ledger`, `--output`, and `--pdf` when needed.

## Shortcuts

The `Makefile` wraps the common local commands:

```bash
make doctor
make report
make test
make lint
```

## Validation

Place representative Sage 50 exports in `data/training/` and run:

```bash
pytest
```

The tests assert the observed structure of the current training workbooks.
