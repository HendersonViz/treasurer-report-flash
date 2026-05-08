from __future__ import annotations

from datetime import date
from decimal import Decimal

from treasurer_flash_report.models import (
    CashSummaryLine,
    ComparativeLine,
    FlashReport,
    SignificantTransaction,
    Variance,
)
from treasurer_flash_report.reports import render_html


def test_render_html_contains_mvp_sections_and_escapes_notes() -> None:
    report = FlashReport(
        organization_name="Example Club",
        report_title="April Flash Report",
        current_period="Actual 04/01/2026 to 04/30/2026",
        comparative_period="Actual 04/01/2025 to 04/30/2025",
        balance_sheet_date="As at 04/30/2026",
        comparative_balance_sheet_date="As at 04/30/2025",
        treasurer_notes=["Use <restricted> funds carefully."],
        income_statement=[ComparativeLine("REVENUE", "Membership", Decimal("100"), Decimal("90"))],
        balance_sheet=[ComparativeLine("CURRENT ASSETS", "Bank", Decimal("50"), Decimal("40"))],
        cash_summary=[
            CashSummaryLine("Operating Account + float + petty cash", Decimal("50"), Decimal("40"))
        ],
        significant_transactions=[
            SignificantTransaction(date(2026, 4, 12), "Wages", "Payroll", Decimal("3375.38"))
        ],
        major_variances=[
            Variance("REVENUE", "Membership", Decimal("100"), Decimal("90"), Decimal("10"), None)
        ],
        risks_and_issues=["No major risks."],
        decisions_needed=["Approve budget transfer."],
        commentary=["Revenue is stable."],
    )

    html = render_html(report)

    assert "Financial Summary" in html
    assert "Major Variances" in html
    assert "Risks / Issues" in html
    assert "Decisions Needed" in html
    assert "Income statement: Actual 04/01/2026 to 04/30/2026" in html
    assert "comparative: Actual 04/01/2025 to 04/30/2025" in html
    assert "Balance sheet: As at 04/30/2026" in html
    assert "data:image/jpeg;base64," in html
    assert "Cash Summary" in html
    assert "Significant Transactions" in html
    assert "Payroll" in html
    assert "Use &lt;restricted&gt; funds carefully." in html


def test_render_html_places_net_result_below_major_variances() -> None:
    report = FlashReport(
        organization_name="Example Club",
        report_title="April Flash Report",
        income_statement=[
            ComparativeLine("REVENUE", "TOTAL REVENUE", Decimal("100"), Decimal("80")),
            ComparativeLine("EXPENSE", "TOTAL EXPENSE", Decimal("40"), Decimal("30")),
            ComparativeLine("NET RESULT", "NET INCOME", Decimal("60"), Decimal("50")),
        ],
        balance_sheet=[],
        major_variances=[
            Variance("REVENUE", "TOTAL REVENUE", Decimal("100"), Decimal("80"), Decimal("20"), None)
        ],
    )

    html = render_html(report)

    net_result_block = html.index('<div class="net-result">')
    assert html.index("TOTAL REVENUE") < net_result_block
    assert net_result_block < html.index("NET INCOME")
    assert "<td>NET RESULT</td>" in html
