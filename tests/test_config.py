from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from treasurer_flash_report.config import load_report_config


def test_load_report_config_reads_notes_and_balanced_adjustment(tmp_path: Path) -> None:
    path = tmp_path / "report.yaml"
    path.write_text(
        """meeting_date: 2026-09-20
deliverables: [html, pdf]
notes:
  treasurer_notes: |
    **Cash** remains stable.
  risks_and_issues: [Late grant]
  decisions_needed: [Approve repairs]
adjustments:
  - date: 2026-09-18
    description: Late invoice
    lines:
      - statement: income
        account: Repairs
        debit: 1250.00
      - statement: balance_sheet
        account: Accounts Payable
        credit: 1250.00
""",
        encoding="utf-8",
    )

    config = load_report_config(path)

    assert config.meeting_date == date(2026, 9, 20)
    assert config.notes.risks_and_issues == ["Late grant"]
    assert config.adjustments[0].lines[0].debit == Decimal("1250.00")
    assert config.adjustments[0].lines[1].statement == "balance"


def test_load_report_config_rejects_unbalanced_adjustment(tmp_path: Path) -> None:
    path = tmp_path / "report.yaml"
    path.write_text(
        """meeting_date: 2026-09-20
adjustments:
  - date: 2026-09-18
    description: Bad entry
    lines:
      - statement: income
        account: Repairs
        debit: 10
      - statement: balance
        account: Bank
        credit: 9
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="not balanced"):
        load_report_config(path)
