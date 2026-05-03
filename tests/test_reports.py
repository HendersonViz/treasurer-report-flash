from __future__ import annotations

from decimal import Decimal

from treasurer_flash_report.models import ComparativeLine, FlashReport, Variance
from treasurer_flash_report.reports import render_html


def test_render_html_contains_mvp_sections_and_escapes_notes() -> None:
    report = FlashReport(
        organization_name="Example Club",
        report_title="April Flash Report",
        treasurer_notes=["Use <restricted> funds carefully."],
        income_statement=[ComparativeLine("REVENUE", "Membership", Decimal("100"), Decimal("90"))],
        balance_sheet=[ComparativeLine("CURRENT ASSETS", "Bank", Decimal("50"), Decimal("40"))],
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
    assert "Use &lt;restricted&gt; funds carefully." in html
