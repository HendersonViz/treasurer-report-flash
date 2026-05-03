# AGENTS.md — treasurer-flash-report

## Purpose
Convert Sage 50 `.xlsx` financial exports into a board-ready flash report.
Target users: volunteer treasurers and NPO finance staff.

## Product workflow
Upload monthly income statement + balance sheet (+ optional budget-to-actual),
add treasurer notes, generate: financial summary, cash position, major variances,
risks/issues, decisions needed, plain-English commentary.
Source of truth: `init-starter.txt`.

## Current state
Greenfield. No code, build system, dependencies, tests, or CI yet.

## Tech direction
- **Language:** Python.
- **Input parsing:** pandas + openpyxl for Sage 50 `.xlsx` exports.
- **Output targets:** crisp PDF report (e.g. via WeasyPrint or ReportLab) and
  email-friendly HTML. Avoid Excel as the final output—it is a parsing input only.
- **Audience constraint:** output must be readable by non-technical board members;
  no CLI tools or raw data dumps as deliverables.

## Data contract — `data/training/`
All files are single-sheet `.xlsx` with name `Sheet1`. Types observed:
- **Balance sheet** (`BalanceApr26.xlsx`) — comparative (current vs. prior); blank
  spacer columns between periods.
- **Income statement** (`IncomeApr26.xlsx`) — comparative (FY vs. FY); includes
  percent-change column.
- **Trial balance** (`TrialApr26.xlsx`) — flat table (Account #, Description,
  Debits, Credits).
- **General ledger** (`LedgerApr26.xlsx`) — **sparse/hierarchical**: account
  header row + detail rows with empty account/name columns; running balance with
  Dr/Cr indicator.
- **Cheque log** (`ChqLogApr26.xlsx`) — transaction list per bank account.

### Parsing gotchas an agent will miss
- **Dates are Excel serial numbers** (e.g. `46120`), not strings. Must convert.
- **First two rows are headers**: org name, then report title, before data begins.
- **Comparative reports have blank spacer columns** between periods.
- **General Ledger is not a rectangular table**. Don't parse it like the trial
  balance.

## Conventions
- Treat `data/training/` as the canonical schema. Validate any parser change
  against all five files.
- Prefer PDF/HTML output. Do not generate Excel as a final deliverable.
