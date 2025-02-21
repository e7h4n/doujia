from datetime import date, timedelta

from beancount.core.prices import build_price_map
from fava.ext import FavaExtensionBase, extension_endpoint
from fava.util.date import parse_date
from flask import jsonify

from doujia.extensions.dashboard_logic import (
    ExpenseChartConfig,
    NetWorthChart,
    dashboard_summary,
    expense_group,
    grouped_account_compared_balance,
    interval_balance,
    outing_expense_summary,
    transaction_count,
)
from doujia.report.daily import daily_report
from doujia.report.saving import calc_saving_summary


class Dashboard(FavaExtensionBase):
    report_title = "Dashboard"
    has_js_module = True

    def get_pending_transaction_count(self) -> int:
        return transaction_count(self.ledger)

    @extension_endpoint
    def trip_summary(self):
        return jsonify(
            outing_expense_summary(
                self.ledger,
                outing_account_prefix="Expenses:Outing",
                currency="CNY",
                activity_tags=[
                    "PLAYGROUND",
                    "HIKING",
                    "CYCLING",
                    "CAMPING",
                    "FIXED_EXPENSE",
                    "SKI",
                ],
            )
        )

    def grouped_expense_yoy_compare(self):
        begin, end = parse_date("quarter")
        yoy_begin, yoy_end = parse_date("quarter-4")
        today = date.today()
        compared_balances = grouped_account_compared_balance(
            self.ledger.all_entries,
            build_price_map(self.ledger.all_entries),
            "Expenses:Consume:",
            (begin, end),
            (yoy_begin, yoy_end),
            today,
            "CNY",
        )

        return compared_balances

    @extension_endpoint
    def net_worth_chart(self):
        begin, end = parse_date("2021-08-01 - day")
        end = end - timedelta(days=1)
        return jsonify(
            NetWorthChart(
                title="Net Worth",
                currency="CNY",
                total=interval_balance(
                    self.ledger,
                    end,
                    ["Assets:Short", "Liabilities:Short"],
                    "CNY",
                    interval_days=1,
                    begin_date=begin,
                ),
                investment=interval_balance(
                    self.ledger,
                    end,
                    ["Assets:Short:Investment"],
                    "CNY",
                    interval_days=1,
                    begin_date=begin,
                ),
                stock=interval_balance(
                    self.ledger,
                    end,
                    ["Assets:Short:Stock"],
                    "CNY",
                    interval_days=1,
                    begin_date=begin,
                ),
            )
        )

    def dashboard_summary(self):
        begin, _ = parse_date("year")
        return dashboard_summary(
            ledger=self.ledger,
            currency="CNY",
            account_prefixes=["Assets:Short", "Liabilities:Short"],
            investment_prefixes=["Assets:Short:Stock", "Assets:Short:Investment"],
            current_prefixes=[
                "Assets:Short:Current:CMB",
                "Assets:Receivables",
                "Assets:Short:Current:Alipay",
            ],
            saving_prefixes=["Assets:Short:Stock:CN:Current"],
            income_prefixes=[
                "Income:Positive:Salary",
                "Assets:Short:Current:HousingAccumulation",
            ],
            creditcard_prefixes=["Liabilities:Short:CreditCard:CMB"],
            begin_date=begin,
            end_date=date.today() + timedelta(days=1),
        )

    @extension_endpoint
    def daily_stat(self):
        options = self.ledger.options
        entries = self.ledger.all_entries
        return jsonify(
            daily_report(
                entries,
                options,
                self.ledger.join_path(self.config["beangrow_config"]),
                self.config["cash_account_prefix_list"],
                self.config["credit_card_prefix_list"],
            )
        )

    @extension_endpoint
    def summary(self):
        return jsonify(self.dashboard_summary())

    @extension_endpoint
    def saving_summary(self):
        return jsonify(
            calc_saving_summary(
                self.ledger.all_entries,
                salary_accounts=[
                    "Income:Positive:Salary",
                    "Assets:Short:Current:HousingAccumulation",
                ],
                current_accounts=[
                    "Assets:Short:Current:CMB",
                    "Assets:Receivables",
                    "Assets:Short:Current:Alipay",
                ],
                saving_accounts=["Assets:Short:Stock:CN:Current"],
            )
        )

    @extension_endpoint
    def charts(self):
        charts = [
            ExpenseChartConfig(
                title="Quarterly Living Expenses",
                accounts=["Expenses:Living"],
                time_range="quarter",
                time_range_to_compare="quarter-4",
                currency="CNY",
            ),
            ExpenseChartConfig(
                title="Quarterly Consume / Improvement / Social Expenses",
                accounts=[
                    "Expenses:Consume:",
                    "Expenses:Improvements:",
                    "Expenses:Social:",
                ],
                time_range="quarter",
                time_range_to_compare="quarter-4",
                currency="CNY",
            ),
            ExpenseChartConfig(
                title="Yearly Living Expenses",
                accounts=["Expenses:Living"],
                time_range="year",
                time_range_to_compare="year-1",
                currency="CNY",
            ),
            ExpenseChartConfig(
                title="Yearly Consume / Improvement / Social Expenses",
                accounts=[
                    "Expenses:Consume:",
                    "Expenses:Improvements:",
                    "Expenses:Social:",
                ],
                time_range="year",
                time_range_to_compare="year-1",
                currency="CNY",
            ),
            ExpenseChartConfig(
                title="Yearly Outing Expenses",
                accounts=["Expenses:Outing"],
                time_range="year",
                time_range_to_compare="year-1",
                currency="CNY",
            ),
            ExpenseChartConfig(
                title="Yearly Depreciation Expenses",
                accounts=["Expenses:Depreciation"],
                time_range="year",
                time_range_to_compare="year-1",
                currency="CNY",
            ),
        ]

        return jsonify(expense_group(self.ledger, charts))
