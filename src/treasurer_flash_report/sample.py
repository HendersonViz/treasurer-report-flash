from __future__ import annotations

from datetime import date
from decimal import Decimal

from .models import (
    CashSummaryLine,
    ComparativeLine,
    FlashReport,
    SignificantTransaction,
    Variance,
    VarianceGroup,
)


def build_sample_flash_report() -> FlashReport:
    revenue = Variance(
        "REVENUE",
        "TOTAL REVENUE",
        Decimal("284750"),
        Decimal("251300"),
        Decimal("33450"),
        Decimal("13.30"),
    )
    expenses = Variance(
        "EXPENSE",
        "TOTAL EXPENSE",
        Decimal("272565"),
        Decimal("244190"),
        Decimal("28375"),
        Decimal("11.60"),
    )

    return FlashReport(
        organization_name="Hartwell Community Foundation",
        report_title="Comparative Income Statement and Comparative Balance Sheet",
        sample_badge="SAMPLE REPORT - Synthetic data only",
        footer_note=(
            "This is a sample report generated from synthetic data for demonstration purposes "
            "only. All figures, organization names, and transactions are fictional. Generated "
            "by Treasurer Flash Report, a tool for converting Sage 50 exports into board-ready "
            "financial summaries."
        ),
        current_period="Actual 05/01/2024 to 04/30/2025",
        comparative_period="Actual 05/01/2023 to 04/30/2024",
        balance_sheet_date="As at 04/30/2025",
        comparative_balance_sheet_date="As at 04/30/2024",
        executive_snapshot=[
            (
                "Cash is available for current operations, with unrestricted balances ahead "
                "of last year."
            ),
            (
                "Revenue is up $33,450.00 from the comparison period, mainly from grant income "
                "and spring fundraising."
            ),
            (
                "Expenses are up $28,375.00, led by staffing, occupancy, and insurance renewal "
                "costs."
            ),
            "Board approval is requested for an insurance budget reallocation.",
        ],
        treasurer_notes=[
            (
                "Grant pipeline: The $40,000 Provincial Arts Council disbursement arrived in "
                "April as expected. The second tranche is contingent on the May program report."
            ),
            (
                "Insurance: The administration cost increase reflects the annual insurance "
                "renewal and broader directors' liability coverage."
            ),
            (
                "Capital reserve: The reserve fund balance grew by $12,800 this year and remains "
                "on track against the board-approved target."
            ),
        ],
        income_statement=[
            ComparativeLine("REVENUE", "TOTAL REVENUE", Decimal("284750"), Decimal("251300")),
            ComparativeLine("EXPENSE", "TOTAL EXPENSE", Decimal("272565"), Decimal("244190")),
            ComparativeLine("NET RESULT", "NET INCOME", Decimal("12185"), Decimal("7110")),
        ],
        balance_sheet=[
            ComparativeLine(
                "CURRENT ASSETS",
                "Operating Account",
                Decimal("48210"),
                Decimal("39875"),
            ),
            ComparativeLine("CURRENT ASSETS", "Petty Cash & Float", Decimal("630"), Decimal("630")),
            ComparativeLine(
                "CURRENT ASSETS",
                "Short-Term GIC (cashable)",
                Decimal("12500"),
                Decimal("12500"),
            ),
            ComparativeLine(
                "RESTRICTED ASSETS",
                "Capital Reserve Fund",
                Decimal("84200"),
                Decimal("71400"),
            ),
        ],
        cash_summary=[
            CashSummaryLine("Operating Account", Decimal("48210"), Decimal("39875")),
            CashSummaryLine("Petty Cash & Float", Decimal("630"), Decimal("630")),
            CashSummaryLine("Short-Term GIC (cashable)", Decimal("12500"), Decimal("12500")),
            CashSummaryLine(
                "Capital Reserve Fund (restricted)",
                Decimal("84200"),
                Decimal("71400"),
            ),
            CashSummaryLine("Unrestricted operating balance", Decimal("61340"), Decimal("53005")),
        ],
        significant_transactions=[
            SignificantTransaction(
                date(2025, 4, 2),
                "Grants Receivable",
                "Provincial Arts Council - spring disbursement",
                Decimal("40000"),
            ),
            SignificantTransaction(
                date(2025, 4, 10),
                "Event Revenue",
                "Spring Gala net proceeds",
                Decimal("18450"),
            ),
            SignificantTransaction(
                date(2025, 4, 15),
                "Wages - Program Staff",
                "Semi-monthly payroll",
                Decimal("9240"),
            ),
            SignificantTransaction(
                date(2025, 4, 22),
                "Facility Rental",
                "Q4 lease payment - 220 Elm St",
                Decimal("6800"),
            ),
            SignificantTransaction(
                date(2025, 4, 30),
                "Accrued Liabilities",
                "Accrual reversal - prior year audit adjustment",
                Decimal("4125"),
            ),
        ],
        major_variances=[revenue, expenses],
        major_variance_groups=[
            VarianceGroup(
                summary=revenue,
                drivers=[
                    Variance(
                        "GRANTS",
                        "TOTAL GRANT INCOME",
                        Decimal("162000"),
                        Decimal("130000"),
                        Decimal("32000"),
                        Decimal("24.60"),
                    ),
                    Variance(
                        "FUNDRAISING",
                        "Events & Donations",
                        Decimal("87500"),
                        Decimal("84200"),
                        Decimal("3300"),
                        Decimal("3.90"),
                    ),
                    Variance(
                        "PROGRAM FEES",
                        "Participant Fees",
                        Decimal("35250"),
                        Decimal("37100"),
                        Decimal("-1850"),
                        Decimal("-5.00"),
                    ),
                ],
            ),
            VarianceGroup(
                summary=expenses,
                drivers=[
                    Variance(
                        "STAFFING",
                        "Wages & Benefits",
                        Decimal("148200"),
                        Decimal("132500"),
                        Decimal("15700"),
                        Decimal("11.80"),
                    ),
                    Variance(
                        "OCCUPANCY",
                        "Facility & Utilities",
                        Decimal("58400"),
                        Decimal("51600"),
                        Decimal("6800"),
                        Decimal("13.20"),
                    ),
                    Variance(
                        "ADMINISTRATION",
                        "Insurance renewal",
                        Decimal("14750"),
                        Decimal("11200"),
                        Decimal("3550"),
                        Decimal("31.70"),
                    ),
                ],
            ),
        ],
        commentary=[
            (
                "Revenue is $284,750.00 and expenses are $272,565.00, for a net result "
                "of $12,185.00."
            ),
            "Cash-like balances total $61,340.00 excluding the restricted capital reserve.",
            (
                "The organization ended the period modestly ahead of the prior year, driven "
                "primarily by stronger grant income and event fundraising."
            ),
        ],
        risks_and_issues=[
            "Second grant tranche is contingent on the May program report deadline.",
            "Insurance cost increases should be included in the annual budget review.",
            "Program fee revenue is trending slightly down; pricing review is recommended.",
        ],
        decisions_needed=[
            "Approve budget reallocation of $3,500 from contingency to cover insurance shortfall.",
            "Confirm fall program fee schedule before the June board meeting.",
        ],
    )
