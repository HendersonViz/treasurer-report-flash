from __future__ import annotations

from decimal import Decimal
from html import escape
from pathlib import Path

from .builder import cash_position, section_total
from .models import FlashReport


def render_html(report: FlashReport) -> str:
    notes = _list_items(report.treasurer_notes, "No notes provided.")
    variances = _variance_rows(report)
    risks = _list_items(report.risks_and_issues, "No risks or issues flagged.")
    decisions = _list_items(report.decisions_needed, "No board decisions identified.")
    commentary = _paragraphs(report.commentary)
    cash = cash_position(report)
    revenue = section_total(report.income_statement, "REVENUE")
    expenses = section_total(report.income_statement, "EXPENSE")
    net = revenue - expenses

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{escape(report.report_title)}</title>
  <style>
    body {{
      background: #fbfaf4;
      color: #1f2a33;
      font: 16px/1.5 Georgia, 'Times New Roman', serif;
      margin: 40px;
    }}
    main {{ max-width: 820px; margin: 0 auto; }}
    h1, h2 {{ font-family: Verdana, sans-serif; line-height: 1.15; }}
    h1 {{ margin-bottom: 0; }}
    section {{ margin-top: 34px; }}
    .summary {{ display: grid; gap: 16px; grid-template-columns: repeat(3, 1fr); }}
    .card {{ background: #f3efe4; border-left: 5px solid #35605a; padding: 16px; }}
    .amount {{ display: block; font-size: 1.4rem; font-weight: 700; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border-bottom: 1px solid #d8d0bf; padding: 9px 6px; text-align: left; }}
    th {{ color: #35605a; font-family: Verdana, sans-serif; font-size: 0.85rem; }}
    .number {{ text-align: right; white-space: nowrap; }}
    @media (max-width: 700px) {{
      .summary {{ grid-template-columns: 1fr; }}
      body {{ margin: 20px; }}
    }}
  </style>
</head>
<body>
<main>
  <h1>{escape(report.organization_name)}</h1>
  <p>{escape(report.report_title)}</p>
  <section class="summary">
    <div class="card"><span>Cash position</span><span class="amount">{_currency(cash)}</span></div>
    <div class="card"><span>Revenue</span><span class="amount">{_currency(revenue)}</span></div>
    <div class="card"><span>Net result</span><span class="amount">{_currency(net)}</span></div>
  </section>
  <section>
    <h2>Financial Summary</h2>
    {commentary}
  </section>
  <section>
    <h2>Major Variances</h2>
    {variances}
  </section>
  <section>
    <h2>Risks / Issues</h2>
    <ul>{risks}</ul>
  </section>
  <section>
    <h2>Decisions Needed</h2>
    <ul>{decisions}</ul>
  </section>
  <section>
    <h2>Treasurer Notes</h2>
    <ul>{notes}</ul>
  </section>
</main>
</body>
</html>"""


def write_pdf(report: FlashReport, output_path: str | Path) -> None:
    from weasyprint import HTML

    HTML(string=render_html(report)).write_pdf(output_path)


def _list_items(items: list[str], empty_message: str) -> str:
    source = items or [empty_message]
    return "".join(f"<li>{escape(item)}</li>" for item in source)


def _paragraphs(items: list[str]) -> str:
    return "".join(f"<p>{escape(item)}</p>" for item in items)


def _variance_rows(report: FlashReport) -> str:
    if not report.major_variances:
        return "<p>No major variances crossed the configured thresholds.</p>"

    rows = []
    for variance in report.major_variances[:10]:
        percent = "" if variance.percent_change is None else f"{variance.percent_change:.2f}%"
        rows.append(
            "<tr>"
            f"<td>{escape(variance.section)}</td>"
            f"<td>{escape(variance.label)}</td>"
            f"<td class=\"number\">{_currency(variance.current)}</td>"
            f"<td class=\"number\">{_currency(variance.prior)}</td>"
            f"<td class=\"number\">{_currency(variance.change)}</td>"
            f"<td class=\"number\">{escape(percent)}</td>"
            "</tr>"
        )

    return (
        "<table>"
        "<thead><tr><th>Section</th><th>Line</th><th>Current</th><th>Prior</th>"
        "<th>Change</th><th>%</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody>"
        "</table>"
    )


def _currency(value: Decimal) -> str:
    return f"${value:,.2f}"
