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
)

DEFAULT_LOGO_PATH = Path(__file__).resolve().parents[1] / "public" / "dcc-logo.jpg"


def render_html(report: FlashReport) -> str:
    notes = _list_items(report.treasurer_notes, "No notes provided.")
    variances = _variance_rows(report)
    periods = _period_disclosure(report)
    logo = _logo_image()
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
    .masthead {{ align-items: center; display: flex; gap: 18px; }}
    .logo {{ height: 82px; width: 82px; object-fit: contain; }}
    .periods {{ color: #43515a; font-family: Verdana, sans-serif; font-size: 0.92rem; }}
    .summary {{ display: grid; gap: 16px; grid-template-columns: repeat(3, 1fr); }}
    .card {{ background: #f3efe4; border-left: 5px solid #35605a; padding: 16px; }}
    .amount {{ display: block; font-size: 1.4rem; font-weight: 700; }}
    .net-result {{ margin-top: 28px; }}
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
  <header class="masthead">
    {logo}
    <div>
      <h1>{escape(report.organization_name)}</h1>
      <p>{escape(report.report_title)}</p>
    </div>
  </header>
  {periods}
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


def _logo_image(path: Path = DEFAULT_LOGO_PATH) -> str:
    if not path.exists():
        return ""
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f'<img class="logo" src="data:image/jpeg;base64,{data}" alt="">'


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
    if not report.major_variances:
        return (
            "<p>No major variances crossed the configured thresholds.</p>"
            f"<div class=\"net-result\">{_variance_table([net], include_header=False)}</div>"
        )

    return (
        _variance_table(report.major_variances[:10], include_header=True)
        +
        f"<div class=\"net-result\">{_variance_table([net], include_header=False)}</div>"
    )


def _variance_table(variances: list[Variance], *, include_header: bool) -> str:
    rows = []
    for variance in variances:
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

    header = (
        "<thead><tr><th>Section</th><th>Line</th><th>Current</th><th>Prior</th>"
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


def _currency(value: Decimal) -> str:
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
