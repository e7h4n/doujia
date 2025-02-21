import datetime

from beancount.core.prices import build_price_map
from fava.core import FavaLedger
from fava.util.date import parse_date
from freezegun import freeze_time

from doujia.extensions.dashboard_logic import (
    ExpenseChartConfig,
    dashboard_summary,
    expense_group,
    expense_summary,
    grouped_account_compared_balance,
    interval_balance,
    outing_expense_summary,
    transaction_count,
)


def test_pending_count(doc_ledger: FavaLedger):
    """
    @@@/main.bean
    2020-01-01 open Expenses:A
    2020-01-01 open Assets:A

    2020-01-01 !
        Expenses:A 100 CNY
        Assets:A
    """

    assert transaction_count(doc_ledger) == 1


def test_pending_count_should_calc_included_ledger(doc_ledger: FavaLedger):
    """
    @@@/main.bean
    2020-01-01 open Expenses:A
    2020-01-01 open Assets:A
    include "other.bean"

    2020-01-01 !
        Expenses:A 100 CNY
        Assets:A

    @@@/other.bean
    2020-01-01 !
        Expenses:A 100 CNY
        Assets:A
    """

    assert transaction_count(doc_ledger) == 2


def test_pending_count_should_ignore_history_ledger(doc_ledger: FavaLedger):
    """
    @@@/main.bean
    2020-01-01 open Expenses:A
    2020-01-01 open Assets:A
    include "history.bean"

    2020-01-01 !
        Expenses:A 100 CNY
        Assets:A

    @@@/history.bean
    2020-01-01 !
        Expenses:A 100 CNY
        Assets:A
    """

    assert transaction_count(doc_ledger) == 1


@freeze_time("2021-03-01")
def test_expenses(doc_ledger: FavaLedger):
    """
    @@@/main.bean
    2020-01-01 open Expenses:A
    2020-01-01 open Assets:A

    2020-01-01 !
        Expenses:A 100 CNY
        Assets:A

    2020-01-02 !
        Expenses:A 100 CNY
        Assets:A

    2021-01-01 !
        Expenses:A 200 CNY
        Assets:A
    """

    summary = expense_summary(doc_ledger, "quarter", "quarter-4", ["Expenses:A"], "CNY")
    assert summary.compare_total == 200
    assert summary.begin == datetime.date(2021, 1, 1)
    assert summary.end == datetime.date(2021, 3, 31)
    assert len(summary.expenses) > 0


@freeze_time("2021-01-01")
def test_expenses_first_expense_should_include_last_day(doc_ledger: FavaLedger):
    """
    @@@/main.bean
    2020-01-01 open Expenses:A
    2020-01-01 open Assets:A

    2021-01-31 !
        Expenses:A 200 CNY
        Assets:A
    """

    summary = expense_summary(doc_ledger, "month", "month-12", ["Expenses:A"], "CNY")
    assert summary.expenses[-1][0] == datetime.date(2021, 1, 31)
    assert summary.expenses[-1][1] == 200


@freeze_time("2021-01-01")
# 测试计算现金流时的日程应该包含第一天，7 天一个时间节点，且金额应该包括前一个周期的金额
def test_expenses_summary_interval(
    doc_ledger: FavaLedger,
):
    """
    @@@/main.bean
    2020-01-01 open Expenses:A
    2020-01-01 open Assets:A

    2021-01-01 !
        Expenses:A 1 CNY
        Assets:A

    2021-01-02 !
        Expenses:A 10 CNY
        Assets:A

    2021-01-07 !
        Expenses:A 100 CNY
        Assets:A

    2021-01-08 !
        Expenses:A 1000 CNY
        Assets:A

    """

    summary = expense_summary(doc_ledger, "month", "month-12", ["Expenses:A"], "CNY")
    assert len(summary.expenses) == 6
    assert summary.expenses[0][0] == datetime.date(2021, 1, 1)
    assert summary.expenses[0][1] == 1
    assert summary.expenses[-1][0] == datetime.date(2021, 1, 31)
    assert summary.expenses[-1][1] == 1111


@freeze_time("2021-01-01")
def test_expenses_first_expense_should_include_compare_first_and_last_day(
    doc_ledger: FavaLedger,
):
    """
    @@@/main.bean
    2020-01-01 open Expenses:A
    2020-01-01 open Assets:A

    2019-12-31 !
        Expenses:A 100 CNY
        Assets:A

    2020-01-01 !
        Expenses:A 1 CNY
        Assets:A

    2020-01-31 !
        Expenses:A 10 CNY
        Assets:A

    2020-02-01 !
        Expenses:A 1000 CNY
        Assets:A
    """

    summary = expense_summary(doc_ledger, "month", "month-12", ["Expenses:A"], "CNY")
    assert summary.compare_total == 11


@freeze_time("2021-01-01")
def test_expenses_first_expense_should_auto_convert_currency(
    doc_ledger: FavaLedger,
):
    """
    @@@/main.bean
    2020-01-01 open Expenses:A
    2020-01-01 open Assets:A

    2020-01-01 price USD 7 CNY

    2020-01-01 !
        Expenses:A 1 USD
        Assets:A

    """

    summary = expense_summary(doc_ledger, "month", "month-12", ["Expenses:A"], "CNY")
    assert summary.compare_total == 7


@freeze_time("2021-01-01")
def test_expenses_first_expense_should_auto_convert_currency_by_happened_time(
    doc_ledger: FavaLedger,
):
    """
    @@@/main.bean
    2020-01-01 open Expenses:A
    2020-01-01 open Assets:A

    2020-01-01 price USD 7 CNY

    2020-01-01 !
        Expenses:A 1 USD
        Assets:A

    2020-12-31 price USD 14 CNY
    """

    summary = expense_summary(doc_ledger, "month", "month-12", ["Expenses:A"], "CNY")
    assert summary.compare_total == 7


@freeze_time("2021-03-01")
def test_expenses_should_match_account_prefix(doc_ledger: FavaLedger):
    """
    @@@/main.bean
    2020-01-01 open Expenses:A
    2020-01-01 open Assets:A

    2020-01-01 !
        Expenses:A 100 CNY
        Assets:A
    """

    summary = expense_summary(doc_ledger, "quarter", "quarter-4", ["Expenses:"], "CNY")
    assert summary.compare_total == 100


@freeze_time("2021-03-01")
def test_expense_group(doc_ledger: FavaLedger):
    """
    @@@/main.bean
    2020-01-01 open Expenses:A
    2020-01-01 open Assets:A

    2020-01-01 !
        Expenses:A 100 CNY
        Assets:A
    """

    group = expense_group(
        doc_ledger,
        [
            ExpenseChartConfig(
                title="T",
                accounts=["Expenses:A"],
                time_range="quarter",
                time_range_to_compare="quarter-4",
                currency="CNY",
            ),
        ],
    )

    assert len(group.charts) == 1
    assert group.charts[0].title == "T"
    assert group.charts[0].currency == "CNY"


@freeze_time("2023-03-01")
def test_outing_expense(doc_ledger: FavaLedger):
    """
    @@@/main.bean
    2020-01-01 open Expenses:A
    2020-01-01 open Assets:A

    2023-01-01 ! ^2023-HK
        Expenses:A 100 CNY
        Assets:A
    """
    summary = outing_expense_summary(doc_ledger, "Expenses:", "CNY")
    assert summary.total == 100


@freeze_time("2023-03-01")
def test_outing_expense_last_year(doc_ledger: FavaLedger):
    """
    @@@/main.bean
    2020-01-01 open Expenses:A
    2020-01-01 open Assets:A

    2022-01-01 ! ^2023-HK
        Expenses:A 123 CNY
        Assets:A
    """
    summary = outing_expense_summary(doc_ledger, "Expenses:", "CNY")
    assert summary.last_total == 123


@freeze_time("2023-03-01")
def test_outing_expense_grouped_group(doc_ledger: FavaLedger):
    """
    @@@/main.bean
    2020-01-01 open Expenses:A
    2020-01-01 open Assets:A

    2023-01-01 ! ^TRIP-2023-HK
        Expenses:A 123 CNY
        Assets:A
    """
    summary = outing_expense_summary(doc_ledger, "Expenses:", "CNY")
    assert len(summary.groups) == 1
    assert summary.groups[0].name == "TRIP-2023-HK"
    assert summary.groups[0].total == 123


@freeze_time("2023-03-01")
def test_outing_expense_last_year_grouped_group(doc_ledger: FavaLedger):
    """
    @@@/main.bean
    2020-01-01 open Expenses:A
    2020-01-01 open Assets:A

    2022-01-01 ! ^TRIP-2023-HK
        Expenses:A 123 CNY
        Assets:A
    """
    summary = outing_expense_summary(doc_ledger, "Expenses:", "CNY")
    assert len(summary.last_groups) == 1
    assert summary.last_groups[0].name == "TRIP-2023-HK"
    assert summary.last_groups[0].total == 123


@freeze_time("2023-03-01")
def test_outing_expense_grouped_group_by_tag(doc_ledger: FavaLedger):
    """
    @@@/main.bean
    2020-01-01 open Expenses:A
    2020-01-01 open Assets:A

    2023-01-01 ! #PLAYGROUND
        Expenses:A 1 CNY
        Assets:A

    2023-02-01 ! #HIKING
        Expenses:A 2 CNY
        Assets:A
    """
    summary = outing_expense_summary(
        doc_ledger, "Expenses:", "CNY", activity_tags=["PLAYGROUND", "HIKING"]
    )
    assert len(summary.groups) == 2
    assert summary.groups[0].name == "PLAYGROUND"
    assert summary.groups[0].total == 1
    assert summary.groups[1].name == "HIKING"
    assert summary.groups[1].total == 2


def test_net_worth_interval_amounts(doc_ledger: FavaLedger):
    """
    @@@/main.bean
    2020-01-01 open Assets:Short
    2020-01-01 open Liabilities:Short
    2020-01-01 open Equity:Opening-Balances

    2022-01-01 !
        Assets:Short 1 CNY
        Equity:Opening-Balances

    2022-01-02 !
        Assets:Short 1 CNY
        Equity:Opening-Balances

    2022-01-08 !
        Assets:Short 111 CNY
        Equity:Opening-Balances
    """
    amounts = interval_balance(
        doc_ledger, datetime.date(year=2023, month=3, day=1), ["Assets:Short"], "CNY"
    )
    assert amounts[0] == (datetime.date(year=2021, month=12, day=29), 0)
    assert amounts[1] == (datetime.date(year=2022, month=1, day=5), 2)
    assert amounts[-1] == (datetime.date(year=2023, month=3, day=1), 113)


def test_net_worth_interval_amounts_generate_amount_event_if_no_transaction(
    doc_ledger: FavaLedger,
):
    """
    @@@/main.bean
    2020-01-01 open Assets:Short
    2020-01-01 open Liabilities:Short
    2020-01-01 open Equity:Opening-Balances

    2022-01-01 price CNYX 1 CNY

    2022-01-01 !
        Assets:Short 1 CNY
        Equity:Opening-Balances

    2022-01-02 !
        Assets:Short 1 CNY
        Equity:Opening-Balances

    2022-01-08 !
        Assets:Short 111 CNY
        Equity:Opening-Balances

    2022-01-16 !
        Assets:Short 1 CNYX
        Equity:Opening-Balances

    2022-01-23 price CNYX 2 CNY
    """
    amounts = interval_balance(
        doc_ledger, datetime.date(year=2022, month=3, day=1), ["Assets:Short"], "CNY"
    )
    assert amounts[2] == (datetime.date(year=2022, month=1, day=11), 113)
    assert amounts[3] == (datetime.date(year=2022, month=1, day=18), 114)
    assert amounts[4] == (datetime.date(year=2022, month=1, day=25), 115)


def test_net_worth_interval_amounts_should_contain_last_day(doc_ledger: FavaLedger):
    """
    @@@/main.bean
    2020-01-01 open Assets:Short
    2020-01-01 open Equity:Opening-Balances

    2022-01-01 !
        Assets:Short 1 CNY
        Equity:Opening-Balances
    """
    amounts = interval_balance(
        doc_ledger, datetime.date(year=2022, month=3, day=1), ["Assets:Short"], "CNY"
    )

    assert amounts[-1] == (datetime.date(year=2022, month=3, day=1), 1)


def test_net_worth_interval_amounts_custom_interval(
    doc_ledger: FavaLedger,
):
    """
    @@@/main.bean
    2020-01-01 open Assets:Short
    2020-01-01 open Equity:Opening-Balances

    2022-01-01 !
        Assets:Short 1 CNY
        Equity:Opening-Balances

    2022-01-02 !
        Assets:Short 1 CNY
        Equity:Opening-Balances
    """
    amounts = interval_balance(
        doc_ledger,
        datetime.date(year=2022, month=3, day=1),
        ["Assets:Short"],
        "CNY",
        interval_days=1,
    )
    assert amounts[0] == (datetime.date(year=2021, month=12, day=31), 0)
    assert amounts[1] == (datetime.date(year=2022, month=1, day=1), 1)
    assert amounts[2] == (datetime.date(year=2022, month=1, day=2), 2)
    assert amounts[-1] == (datetime.date(year=2022, month=3, day=1), 2)


def test_net_worth_interval_support_begin_date(
    doc_ledger: FavaLedger,
):
    """
    @@@/main.bean
    2020-01-01 open Assets:Short
    2020-01-01 open Equity:Opening-Balances

    2022-01-01 !
        Assets:Short 1 CNY
        Equity:Opening-Balances

    2022-01-02 !
        Assets:Short 1 CNY
        Equity:Opening-Balances
    """
    amounts = interval_balance(
        doc_ledger,
        datetime.date(year=2022, month=3, day=1),
        ["Assets:Short"],
        "CNY",
        interval_days=1,
        begin_date=datetime.date(year=2022, month=2, day=28),
    )

    assert amounts[0] == (datetime.date(year=2022, month=2, day=28), 2)
    assert amounts[1] == (datetime.date(year=2022, month=3, day=1), 2)


@freeze_time("2022-01-01")
def test_dashboard_summary(doc_ledger: FavaLedger):
    """
    @@@/main.bean
    2020-01-01 open Assets:Short
    2020-01-01 open Equity:Opening-Balances

    2021-12-31 !
        Assets:Short 10 CNY
        Equity:Opening-Balances

    2022-01-01 !
        Assets:Short 1 CNY
        Equity:Opening-Balances

    2022-01-02 !
        Assets:Short 1 CNY
        Equity:Opening-Balances

    2022-01-31 !
        Assets:Short 1 CNY
        Equity:Opening-Balances

    @@@/config/beangrow.pbtxt
    """

    begin, end = parse_date("month")
    summary = dashboard_summary(
        doc_ledger,
        begin,
        end,
        currency="CNY",
        account_prefixes=["Assets:Short"],
        investment_prefixes=[],
    )
    assert summary.net_worth == 13
    assert summary.gain_loss == 3


@freeze_time("2022-01-01")
def test_dashboard_summary_investment(doc_ledger: FavaLedger):
    """
    @@@/main.bean
    2020-01-01 open Assets:Short
    2020-01-01 open Assets:Stock

    2022-01-01 price AAPL 10 CNY
    2022-01-01 !
        Assets:Short
        Assets:Stock 1 AAPL { 10 CNY }

    @@@/config/beangrow.pbtxt
    """

    begin, end = parse_date("month")
    summary = dashboard_summary(
        doc_ledger,
        begin,
        end,
        currency="CNY",
        account_prefixes=["Assets:"],
        investment_prefixes=["Assets:Stock"],
    )
    assert summary.net_worth == 0
    assert summary.investment == 10
    assert summary.gain_loss == 0


def test_dashboard_summary_investment_affected_by_price(doc_ledger: FavaLedger):
    """
    @@@/main.bean
    2020-01-01 open Assets:Short
    2020-01-01 open Assets:Stock

    2022-01-01 price AAPL 10 CNY
    2022-01-01 !
        Assets:Short
        Assets:Stock 1 AAPL { 10 CNY }

    2022-01-30 price AAPL 100 CNY

    @@@/config/beangrow.pbtxt
    """

    summary = dashboard_summary(
        doc_ledger,
        datetime.date(2022, 1, 1),
        datetime.date(2022, 2, 1),
        currency="CNY",
        account_prefixes=["Assets:"],
        investment_prefixes=["Assets:Stock"],
    )
    assert summary.net_worth == 90
    assert summary.investment == 100
    assert summary.gain_loss == 90


@freeze_time("2022-01-31")
def test_dashboard_summary_xirr(doc_ledger: FavaLedger):
    """
    @@@/main.bean
    2020-01-01 open Assets:Current
    2020-01-01 open Assets:Stock

    1970-01-01 commodity AAPL

    2022-01-01 price AAPL 10 CNY
    2022-01-01 !
        Assets:Current
        Assets:Stock 1 AAPL { 10 CNY }

    2022-01-30 price AAPL 100 CNY

    @@@/config/beangrow.pbtxt
    investments {
        investment {
            currency: "AAPL"
            asset_account: "Assets:Stock"
            cash_accounts: "Assets:Current"
        }
    }
    groups {
        group {
            name: "All"
            investment: "Assets:*"
            currency: "CNY"
        }
    }
    """

    begin, end = parse_date("month")
    summary = dashboard_summary(
        doc_ledger,
        begin,
        end,
        currency="CNY",
        account_prefixes=["Assets:"],
        investment_prefixes=["Assets:Stock"],
    )
    assert summary.xirr > 0


@freeze_time("2022-01-31")
def test_account_compared_balance(
    doc_ledger: FavaLedger,
):  # 测试对一个前缀下所有的账户进行开销的排序分组
    """
    @@@/main.bean
    2020-01-01 open Assets:Current
    2020-01-01 open Expenses:Living
    2020-01-01 open Expenses:Outing

    2022-01-01 !
        Assets:Current
        Expenses:Living 1.00 CNY

    2022-01-01 !
        Assets:Current
        Expenses:Outing 10.00 CNY

    2022-03-01 !
        Assets:Current
        Expenses:Outing 100.00 CNY

    2021-01-01 !
        Assets:Current
        Expenses:Living 1.00 CNY

    2021-01-01 !
        Assets:Current
        Expenses:Outing 20.00 CNY

    2021-03-01 !
        Assets:Current
        Expenses:Outing 200.00 CNY
    """

    begin, end = parse_date("quarter")
    yoy_begin, yoy_end = parse_date("quarter-4")
    today = datetime.date.today()
    compared_balances = grouped_account_compared_balance(
        doc_ledger.all_entries,
        build_price_map(doc_ledger.all_entries),
        "Expenses:",
        (begin, end),
        (yoy_begin, yoy_end),
        today,
        "CNY",
    )

    assert len(compared_balances) == 2
    result_dict = {item.account: item for item in compared_balances}
    assert result_dict["Expenses:Outing"].period_balance == 110
    assert result_dict["Expenses:Outing"].yoy_period_balance == 220
    assert result_dict["Expenses:Outing"].today == datetime.date(2022, 1, 31)
    assert result_dict["Expenses:Outing"].today_balance == 10


@freeze_time("2022-01-31")
def test_account_compared_balance_sort_by_yoy_balance(
    doc_ledger: FavaLedger,
):  # 返回的结果应该按照去年的金额进行排序
    """
    @@@/main.bean
    2020-01-01 open Assets:Current
    2020-01-01 open Expenses:Living
    2020-01-01 open Expenses:Outing

    2022-01-01 !
        Assets:Current
        Expenses:Living 1.00 CNY

    2022-01-01 !
        Assets:Current
        Expenses:Outing 10.00 CNY

    2022-03-01 !
        Assets:Current
        Expenses:Outing 100.00 CNY

    2021-01-01 !
        Assets:Current
        Expenses:Living 1.00 CNY

    2021-01-01 !
        Assets:Current
        Expenses:Outing 20.00 CNY

    2021-03-01 !
        Assets:Current
        Expenses:Outing 200.00 CNY
    """

    begin, end = parse_date("quarter")
    yoy_begin, yoy_end = parse_date("quarter-4")
    today = datetime.date.today()
    compared_balances = grouped_account_compared_balance(
        doc_ledger.all_entries,
        build_price_map(doc_ledger.all_entries),
        "Expenses:",
        (begin, end),
        (yoy_begin, yoy_end),
        today,
        "CNY",
    )

    assert compared_balances[0].account == "Expenses:Outing"


@freeze_time("2025-01-01")
def test_dashboard_summary_saving_ratio(doc_ledger: FavaLedger):
    """
    @@@/main.bean
    2021-01-01 open Assets:Current
    2021-01-01 open Assets:Investment
    2021-01-01 open Income:Salary

    2025-01-05 * "工资"
        Income:Salary -1,000.00 CNY
        Assets:Current

    2025-01-08 * "存钱"
        Assets:Current -500.00 CNY
        Assets:Investment

    2025-02-05 * "工资"
        Income:Salary -3,000.00 CNY
        Assets:Current

    2025-04-05 * "工资"
        Income:Salary -1,000.00 CNY
        Assets:Current

    @@@/config/beangrow.pbtxt
    """

    begin, end = parse_date("month")
    summary = dashboard_summary(
        doc_ledger,
        begin,
        end,
        currency="CNY",
        account_prefixes=["Assets:Short"],
        investment_prefixes=[],
        income_prefixes=["Income:Salary"],
        saving_prefixes=["Assets:Investment"],
        current_prefixes=["Assets:Current"],
    )
    assert summary.saving_ratio == 0.5


@freeze_time("2025-01-01")
def test_dashboard_summary_saving_ratio_with_income_prefix(doc_ledger: FavaLedger):
    """
    @@@/main.bean
    2021-01-01 open Assets:Current
    2021-01-01 open Assets:Investment
    2021-01-01 open Income:Salary

    2025-01-05 * "工资"
        Income:Salary -1,000.00 CNY
        Assets:Current

    2025-01-08 * "存钱"
        Assets:Current -500.00 CNY
        Assets:Investment

    2025-02-05 * "工资"
        Income:Salary -3,000.00 CNY
        Assets:Current

    2025-04-05 * "工资"
        Income:Salary -1,000.00 CNY
        Assets:Current

    @@@/config/beangrow.pbtxt
    """

    begin, end = parse_date("month")
    summary = dashboard_summary(
        doc_ledger,
        begin,
        end,
        currency="CNY",
        account_prefixes=["Assets:Short"],
        investment_prefixes=[],
        income_prefixes=["Income:Salary"],
        saving_prefixes=["Assets:Investment"],
        current_prefixes=["Assets:Current"],
    )
    assert summary.saving_ratio == 0.5
