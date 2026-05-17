from __future__ import annotations

import base64
from decimal import Decimal
from html import escape
from pathlib import Path

from .builder import cash_position, net_result, section_total
from .models import (
    CashSummaryLine,
    ComparativeLine,
    FlashReport,
    SignificantTransaction,
    Variance,
    VarianceGroup,
)
from .notes import render_notes_fallback

DEFAULT_LOGO_PATH = Path(__file__).resolve().parents[1] / "public" / "dcc-logo.jpg"


def render_html(report: FlashReport) -> str:
    executive_snapshot = _executive_snapshot_section(report)
    notes = _treasurer_notes_section(report)
    sample_badge = _sample_badge(report)
    footer_note = _footer_note(report)
    variances = _variance_rows(report)
    periods = _period_disclosure(report)
    logo = _sample_logo() if report.sample_badge else _logo_image()
    page_title = _page_title(report)
    cash_summary = _cash_summary_table(report.cash_summary)
    significant_transactions = _significant_transactions_table(report.significant_transactions)
    risks = _list_items(report.risks_and_issues, "No risks or issues flagged.")
    decisions = _list_items(report.decisions_needed, "No board decisions identified.")
    commentary = _paragraphs(report.commentary)
    cash = cash_position(report)
    revenue = section_total(report.income_statement, "REVENUE")
    net = net_result(report.income_statement)

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{escape(page_title)}</title>
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
    .masthead {{ align-items: center; display: flex; gap: 18px; }}
    .logo {{ height: 82px; width: 82px; object-fit: contain; }}
    .sample-logo {{
      align-items: center;
      background: #eaf2ef;
      border: 2px solid #35605a;
      border-radius: 8px;
      color: #35605a;
      display: flex;
      flex: 0 0 auto;
      font-family: Verdana, sans-serif;
      font-size: 1.35rem;
      font-weight: 700;
      height: 78px;
      justify-content: center;
      position: relative;
      width: 78px;
    }}
    .sample-logo::before {{
      border: 2px solid #c29f5d;
      border-radius: 50%;
      content: "";
      height: 44px;
      position: absolute;
      width: 44px;
    }}
    .demo-badge {{
      display: inline-block;
      background: #35605a;
      color: #fff;
      font-family: Verdana, sans-serif;
      font-size: 0.75rem;
      letter-spacing: 0.06em;
      padding: 3px 10px;
      border-radius: 3px;
      margin-top: 6px;
    }}
    .periods {{ color: #43515a; font-family: Verdana, sans-serif; font-size: 0.92rem; }}
    .summary {{ display: grid; gap: 16px; grid-template-columns: repeat(3, 1fr); }}
    .card {{ background: #f3efe4; border-left: 5px solid #35605a; padding: 16px; }}
    .amount {{ display: block; font-size: 1.4rem; font-weight: 700; }}
    .net-result {{ margin-top: 28px; }}
    .snapshot {{ background: #eaf2ef; border-left: 5px solid #35605a; padding: 18px 20px; }}
    .snapshot h2 {{ margin-top: 0; }}
    .notes {{ background: #fff; border: 1px solid #d8d0bf; padding: 18px 20px; }}
    .notes h2 {{ margin-top: 0; }}
    .notes h1, .notes h2, .notes h3 {{ font-size: 1.05rem; }}
    .variance-driver td:first-child {{ padding-left: 24px; }}
    .muted {{ color: #5b6870; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border-bottom: 1px solid #d8d0bf; padding: 9px 6px; text-align: left; }}
    th {{ color: #35605a; font-family: Verdana, sans-serif; font-size: 0.85rem; }}
    .number {{ text-align: right; white-space: nowrap; }}
    .footer-note {{
      margin-top: 48px;
      padding-top: 16px;
      border-top: 1px solid #d8d0bf;
      font-family: Verdana, sans-serif;
      font-size: 0.8rem;
      color: #5b6870;
    }}
    @media (max-width: 700px) {{
      .summary {{ grid-template-columns: 1fr; }}
      body {{ margin: 20px; }}
    }}
  </style>
</head>
<body>
<main>
  <header class="masthead">
    {logo}
    <div>
      <h1>{escape(report.organization_name)}</h1>
      <p>{escape(report.report_title)}</p>
      {sample_badge}
    </div>
  </header>
  {periods}
  {executive_snapshot}
  {notes}
  <section class="summary">
    <div class="card"><span>Cash position</span><span class="amount">{_currency(cash)}</span></div>
    <div class="card"><span>Revenue</span><span class="amount">{_currency(revenue)}</span></div>
    <div class="card"><span>Net result</span><span class="amount">{_currency(net)}</span></div>
  </section>
  <section>
    <h2>Financial Summary</h2>
    {commentary}
    {cash_summary}
  </section>
  <section>
    <h2>Significant Transactions</h2>
    {significant_transactions}
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
  {footer_note}
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


def _sample_badge(report: FlashReport) -> str:
    if not report.sample_badge:
        return ""
    return f'<span class="demo-badge">{escape(report.sample_badge)}</span>'


def _page_title(report: FlashReport) -> str:
    if report.sample_badge:
        return f"Treasurer Flash Report - {report.organization_name} (Sample)"
    return report.report_title


def _footer_note(report: FlashReport) -> str:
    if not report.footer_note:
        return ""
    return f'<p class="footer-note">{escape(report.footer_note)}</p>'


def _executive_snapshot_section(report: FlashReport) -> str:
    snapshot_html = report.executive_snapshot_html.strip()
    if not snapshot_html and report.executive_snapshot:
        snapshot_html = render_notes_fallback(report.executive_snapshot, "No snapshot available.")
    if not snapshot_html:
        return ""
    return f'<section class="snapshot"><h2>Executive Snapshot</h2>{snapshot_html}</section>'


def _treasurer_notes_section(report: FlashReport) -> str:
    notes_html = report.treasurer_notes_html.strip()
    if not notes_html and report.treasurer_notes:
        notes_html = render_notes_fallback(report.treasurer_notes, "No notes provided.")
    if not notes_html:
        return ""
    title = "" if notes_html.startswith(("<h1", "<h2")) else "<h2>Treasurer Notes</h2>"
    return f'<section class="notes">{title}{notes_html}</section>'


def _logo_image(path: Path = DEFAULT_LOGO_PATH) -> str:
    if not path.exists():
        return ""
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f'<img class="logo" src="data:image/jpeg;base64,{data}" alt="">'


def _sample_logo() -> str:
    return '<div class="sample-logo" aria-label="Hartwell Community Foundation sample logo">H</div>'


def _period_disclosure(report: FlashReport) -> str:
    lines = []
    if report.current_period or report.comparative_period:
        current = report.current_period or "Not provided"
        comparative = report.comparative_period or "Not provided"
        lines.append(f"Income statement: {current}; comparative: {comparative}.")
    if report.balance_sheet_date or report.comparative_balance_sheet_date:
        current = report.balance_sheet_date or "Not provided"
        comparative = report.comparative_balance_sheet_date or "Not provided"
        lines.append(f"Balance sheet: {current}; comparative: {comparative}.")
    if not lines:
        return ""
    return f"<p class=\"periods\">{'<br>'.join(escape(line) for line in lines)}</p>"


def _cash_summary_table(lines: list[CashSummaryLine]) -> str:
    if not lines:
        return "<p>No cash summary could be calculated from the uploaded balance sheet.</p>"

    rows = []
    for line in lines:
        rows.append(
            "<tr>"
            f"<td>{escape(line.label)}</td>"
            f"<td class=\"number\">{_currency(line.current)}</td>"
            f"<td class=\"number\">{_currency(line.prior)}</td>"
            "</tr>"
        )

    return (
        "<table>"
        "<thead><tr><th>Cash Summary</th><th>Current</th><th>Prior</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody>"
        "</table>"
    )


def _significant_transactions_table(transactions: list[SignificantTransaction]) -> str:
    if not transactions:
        return "<p>No ledger uploaded, so significant transactions were not calculated.</p>"

    rows = []
    for transaction in transactions:
        rows.append(
            "<tr>"
            f"<td>{transaction.transaction_date.isoformat()}</td>"
            f"<td>{escape(transaction.item)}</td>"
            f"<td>{escape(transaction.description)}</td>"
            f"<td class=\"number\">{_currency(transaction.amount)}</td>"
            "</tr>"
        )

    return (
        "<table>"
        "<thead><tr><th>Date</th><th>Item</th><th>Description</th><th>Amount</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody>"
        "</table>"
    )


def _variance_rows(report: FlashReport) -> str:
    net = _net_result_row(report.income_statement)
    groups = report.major_variance_groups or [
        VarianceGroup(summary=variance, drivers=[]) for variance in report.major_variances
    ]
    if not groups:
        return (
            "<p>No major variances crossed the configured thresholds.</p>"
            f"<div class=\"net-result\">{_variance_table([net], include_header=False)}</div>"
        )

    return (
        _variance_group_table(groups)
        +
        f"<div class=\"net-result\">{_variance_table([net], include_header=False)}</div>"
    )


def _variance_group_table(groups: list[VarianceGroup]) -> str:
    rows = []
    for group in groups:
        rows.append(_variance_row(group.summary, row_class="variance-summary"))
        for driver in group.drivers:
            rows.append(_variance_row(driver, row_class="variance-driver", driver=True))

    return (
        "<table>"
        "<thead><tr><th>Area</th><th>What changed</th><th>Current</th><th>Prior</th>"
        "<th>Change</th><th>%</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody>"
        "</table>"
    )


def _variance_table(variances: list[Variance], *, include_header: bool) -> str:
    rows = []
    for variance in variances:
        rows.append(_variance_row(variance))

    header = (
        "<thead><tr><th>Area</th><th>What changed</th><th>Current</th><th>Prior</th>"
        "<th>Change</th><th>%</th></tr></thead>"
        if include_header
        else ""
    )
    return (
        "<table>"
        f"{header}"
        f"<tbody>{''.join(rows)}</tbody>"
        "</table>"
    )


def _variance_row(
    variance: Variance, *, row_class: str | None = None, driver: bool = False
) -> str:
    percent = "" if variance.percent_change is None else f"{variance.percent_change:.2f}%"
    class_attr = "" if row_class is None else f' class="{row_class}"'
    label = _display_variance_label(variance.label)
    if driver:
        label = f'<span class="muted">Driver:</span> {escape(label)}'
    else:
        label = escape(label)
    return (
        f"<tr{class_attr}>"
        f"<td>{escape(_display_variance_area(variance))}</td>"
        f"<td>{label}</td>"
        f"<td class=\"number\">{_currency(variance.current)}</td>"
        f"<td class=\"number\">{_currency(variance.prior)}</td>"
        f"<td class=\"number\">{_currency(variance.change)}</td>"
        f"<td class=\"number\">{escape(percent)}</td>"
        "</tr>"
    )


def _display_variance_area(variance: Variance) -> str:
    if variance.section.strip().upper() == "NET RESULT":
        return "Net result"
    if variance.label.strip().upper().startswith("TOTAL "):
        return variance.label.strip()[6:].title()
    return variance.section.title()


def _display_variance_label(label: str) -> str:
    stripped = label.strip()
    if stripped.upper().startswith("TOTAL "):
        return f"Total {stripped[6:].title()}"
    return stripped


def _currency(value: Decimal) -> str:
    if value < 0:
        return f"-${abs(value):,.2f}"
    return f"${value:,.2f}"


def _net_result_row(lines: list[ComparativeLine]) -> Variance:
    for label in ("NET INCOME", "NET LOSS"):
        line = _find_line(lines, label)
        if line is not None:
            current = line.current or Decimal("0")
            prior = line.prior or Decimal("0")
            change = current - prior
            percent_change = line.percent_change
            if percent_change is None and prior != 0:
                percent_change = (change / abs(prior) * Decimal("100")).quantize(Decimal("0.01"))
            return Variance("NET RESULT", line.label, current, prior, change, percent_change)

    current = net_result(lines)
    return Variance("NET RESULT", "Net result", current, Decimal("0"), current, None)


def _find_line(lines: list[ComparativeLine], label: str) -> ComparativeLine | None:
    target = label.upper()
    for line in lines:
        if line.label.strip().upper() == target:
            return line
    return None
