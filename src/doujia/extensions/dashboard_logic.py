import datetime
from decimal import Decimal
from typing import NamedTuple, cast

from beancount.core import data, getters
from beancount.core.data import Directive
from beancount.core.inventory import Inventory
from beancount.core.prices import build_price_map
from fava.beans.abc import Amount, Posting
from fava.core import CounterInventory, FavaLedger
from fava.core.conversion import conversion_from_str, convert_position
from fava.util.date import parse_date

from doujia.report.daily import DailyReport, daily_report
from doujia.report.saving import calc_saving
from doujia.report.summerize import (
    PeriodInventory,
    convert_period_inventory,
    sum_single_amount_between,
)

DataPoint = tuple[datetime.date, Decimal]


class ExpenseSummary(NamedTuple):
    begin: datetime.date
    end: datetime.date
    expenses: list[DataPoint]
    compare_total: Decimal


class ExpenseChart(NamedTuple):
    title: str
    currency: str
    summary: ExpenseSummary


class ExpenseChartConfig(NamedTuple):
    title: str
    accounts: list[str]
    time_range: str
    time_range_to_compare: str
    currency: str


class ExpenseChartGroup(NamedTuple):
    today: datetime.date
    charts: list[ExpenseChart]


class NetWorthChart(NamedTuple):
    title: str
    total: list[DataPoint]
    investment: list[DataPoint]
    stock: list[DataPoint]
    currency: str


class DashboardSummary(NamedTuple):
    net_worth: Decimal
    investment: Decimal
    gain_loss: Decimal
    xirr: Decimal
    saving_ratio: Decimal
    daily_report: DailyReport


class GroupExpenseSummary(NamedTuple):
    name: str
    total: Decimal


class OutingExpenseSummary(NamedTuple):
    total: Decimal
    last_total: Decimal
    groups: list[GroupExpenseSummary]
    last_groups: list[GroupExpenseSummary]


class AccountComparedBalance(NamedTuple):
    account: str
    period: tuple[datetime.date, datetime.date]
    period_balance: Decimal
    yoy_period_balance: Decimal
    balance_progress: Decimal
    date_progress: Decimal
    today_balance: Decimal
    today: datetime.date
    currency: str
    predict_balance: Decimal
    predict_remains: Decimal
    remains: Decimal


# 定义一个异常,  CurrencyConversionError
class CurrencyConversionError(Exception):
    def __init__(self, message):
        super().__init__(message)


def _get_only_amount_number(inventory: Inventory, expect_currency: str) -> Decimal:
    pos = inventory.get_only_position()
    if pos:
        assert pos.units.currency == expect_currency
        return pos.units.number

    return Decimal(0)


def expense_summary(
    ledger: FavaLedger,
    time_range: str,
    time_range_to_compare: str,
    account_prefix_list: list[str],
    currency: str,
) -> ExpenseSummary:
    begin, end = parse_date(time_range)
    assert begin
    assert end

    compare_begin, compare_end = parse_date(time_range_to_compare)
    assert compare_begin
    assert compare_end

    temp_end = begin + datetime.timedelta(days=1)
    intervals = [(begin, temp_end)]
    while temp_end < end:
        temp_end = min(temp_end + datetime.timedelta(days=7), end)
        intervals.append((begin, temp_end))

    price_map = build_price_map(ledger.all_entries)
    expenses = [
        (x[1] - datetime.timedelta(days=1), x[2])
        for x in sum_single_amount_between(ledger.all_entries, price_map, account_prefix_list, intervals, currency)
    ]

    compare_total = sum_single_amount_between(
        ledger.all_entries,
        build_price_map(ledger.all_entries),
        account_prefix_list,
        [(compare_begin, compare_end)],
        currency,
    )[0].amount

    return ExpenseSummary(
        begin=begin,
        end=end - datetime.timedelta(days=1),
        expenses=expenses,
        compare_total=compare_total,
    )


def expense_group(ledger: FavaLedger, configs: list[ExpenseChartConfig]) -> ExpenseChartGroup:
    charts = [
        ExpenseChart(
            title=config.title,
            currency=config.currency,
            summary=expense_summary(
                ledger,
                config.time_range,
                config.time_range_to_compare,
                config.accounts,
                config.currency,
            ),
        )
        for config in configs
    ]
    return ExpenseChartGroup(today=datetime.date.today(), charts=charts)


def transaction_count(ledger: FavaLedger) -> int:
    count = 0
    for entry in ledger.all_entries_by_type.Transaction:
        name = entry.meta["filename"]
        assert isinstance(name, str)

        if name.endswith("history.bean"):
            continue

        if entry.flag == "!":
            count += 1

    return count


def _get_only_amount(inventory: CounterInventory, ledger: FavaLedger, currency: str, date: datetime.date) -> Decimal:
    """返回 inventory 中特定账户的金额, 如果 inventory 中不能转换的货币则报错"""
    inventory = conversion_from_str(currency).apply(inventory, ledger.prices, date)

    invalid_currencies = [x for x in inventory.keys() if x != currency]
    if len(invalid_currencies) > 0:
        message = f"can't convert currencies {invalid_currencies} at date {date}"
        raise CurrencyConversionError(message=message)

    amount = inventory.get(currency)
    return amount or Decimal(0)


def _sum_amount_at(
    end_exclude: datetime.date,
    account_prefixes: list[str],
    ledger: FavaLedger,
    currency: str,
) -> Decimal:
    """统计特定账户在 end 日期之前的 balance, 不包括 end_exclude 这一天"""
    inventory = CounterInventory()

    for txn in ledger.all_entries_by_type.Transaction:
        if txn.date >= end_exclude:
            continue

        for posting in txn.postings:
            founds = False
            for prefix in account_prefixes:
                if posting.account.startswith(prefix):
                    founds = True
                    break
            if founds:
                inventory.add_position(posting)

    if len(inventory) == 0:
        return Decimal(0)

    return _get_only_amount(inventory, ledger, currency, end_exclude - datetime.timedelta(days=1))


def _sum_amount_at_dates(
    balance_at_dates: list[datetime.date],
    account_prefixes: list[str],
    ledger: FavaLedger,
    currency: str,
) -> list[Decimal]:
    """返回在 balance_at_dates 之前的每一次 balance, 不包括 at_date 当天"""
    min_date, _ = getters.get_min_max_dates(ledger.all_entries)
    intervals = [(min_date, x) for x in balance_at_dates]
    period_inventories = sum_single_amount_between(
        entries=ledger.all_entries,
        price_map=build_price_map(ledger.all_entries),
        account_prefix_list=account_prefixes,
        date_range=intervals,
        target_currency=currency,
    )

    return [x.amount for x in period_inventories]


def _group_expense(
    begin_inclusive: datetime.date,
    end_exclusive: datetime.date,
    account_prefix: str,
    ledger: FavaLedger,
    currency: str,
    link_prefix: str,
    activity_tags: list[str],
) -> list[GroupExpenseSummary]:
    """
    对于 [begin, end) 之间的 account_prefix 的的交易尝试分组, 分组规则是按照
    link_prefix 和 activity_tags 进行识别, 如果都不能识别则进入 Other
    """
    groups: dict[str, Decimal] = {}

    for txn in ledger.all_entries_by_type.Transaction:
        if txn.date < begin_inclusive or txn.date >= end_exclusive:
            continue

        group_name: str | None = None
        for txn_link in txn.links:
            if txn_link.startswith(link_prefix):
                group_name = txn_link
                break

        if group_name is None:
            for txn_tag in txn.tags:
                if txn_tag in activity_tags:
                    group_name = txn_tag
                    break

        if group_name is None:
            group_name = "Other"

        for posting in txn.postings:
            if posting.account.startswith(account_prefix):
                amount = convert_position(posting, currency, ledger.prices, date=txn.date).number
                if group_name not in groups.keys():
                    groups[group_name] = amount
                else:
                    groups[group_name] += amount

    return [GroupExpenseSummary(name=x, total=groups[x]) for x in groups.keys()]


def outing_expense_summary(
    ledger: FavaLedger,
    outing_account_prefix: str,
    currency: str,
    link_prefix="TRIP-",
    activity_tags=None,
) -> OutingExpenseSummary:
    if activity_tags is None:
        activity_tags = []

    begin, end = parse_date("year")
    assert begin
    assert end

    last_begin, last_end = parse_date("year-1")
    assert last_begin
    assert last_end

    total = sum_single_amount_between(
        ledger.all_entries,
        build_price_map(ledger.all_entries),
        [outing_account_prefix],
        [(begin, end)],
        currency,
    )[0][2]

    last_total = sum_single_amount_between(
        ledger.all_entries,
        build_price_map(ledger.all_entries),
        [outing_account_prefix],
        [(last_begin, last_end)],
        currency,
    )[0][2]

    groups = _group_expense(begin, end, outing_account_prefix, ledger, currency, link_prefix, activity_tags)
    last_groups = _group_expense(
        last_begin,
        last_end,
        outing_account_prefix,
        ledger,
        currency,
        link_prefix,
        activity_tags,
    )

    return OutingExpenseSummary(total=total, last_total=last_total, groups=groups, last_groups=last_groups)


def interval_balance(
    ledger: FavaLedger,
    end_date: datetime.date,
    account_prefixes: list[str],
    currency: str,
    interval_days=7,
    begin_date: datetime.date | None = None,
) -> list[DataPoint]:
    all_inventory = CounterInventory()
    posting_by_date: list[tuple[datetime.date, Posting]] = []
    for txn in ledger.all_entries_by_type.Transaction:
        if txn.date <= end_date:
            for posting in txn.postings:
                for account_prefix in account_prefixes:
                    if posting.account.startswith(account_prefix):
                        posting_by_date.append((txn.date, posting))
                        all_inventory.add_position(posting)
                        break

    accumulated_amounts: list[DataPoint] = []
    while len(posting_by_date) > 0:
        while len(posting_by_date) > 0 and posting_by_date[-1][0] > end_date:
            _, posting = posting_by_date.pop()
            amount = cast(Amount, data.Amount(-posting.units.number, posting.units.currency))

            all_inventory.add_amount(amount, posting.cost)

        accumulated_amounts.append((end_date, _get_only_amount(all_inventory, ledger, currency, end_date)))

        if begin_date and end_date == begin_date:
            break

        end_date = end_date - datetime.timedelta(days=interval_days)
        if begin_date:
            end_date = max(end_date, begin_date)

    return [x for x in reversed(accumulated_amounts)]


def dashboard_summary(
    ledger: FavaLedger,
    begin_date: datetime.date,
    end_date: datetime.date,
    currency: str,
    account_prefixes: list[str],
    investment_prefixes: list[str],
    income_prefixes: list[str] = [],
    saving_prefixes: list[str] = [],
    current_prefixes: list[str] = [],
    creditcard_prefixes: list[str] = [],
) -> DashboardSummary:
    last_amount, amount = _sum_amount_at_dates(
        [begin_date, end_date],
        account_prefixes=account_prefixes,
        ledger=ledger,
        currency=currency,
    )

    investment = _sum_amount_at(end_date, account_prefixes=investment_prefixes, ledger=ledger, currency=currency)

    saving = calc_saving(
        ledger.all_entries,
        start_date_inclusive=max(begin_date, datetime.date(2024, 2, 1)),
        end_date_exclusive=end_date,
        salary_accounts=income_prefixes,
        current_accounts=current_prefixes,
        saving_accounts=saving_prefixes,
        debug_output=False,
    )

    saving_ratio = 0
    if saving.total_income > Decimal(0):
        saving_ratio = saving.total_saving / saving.total_income

    report = daily_report(
        entries=ledger.all_entries,
        options=ledger.options,
        beangrow_config_path="config/beangrow.pbtxt",
        cash_account_prefix_list=current_prefixes,
        credit_card_prefix_list=creditcard_prefixes,
    )

    return DashboardSummary(
        net_worth=amount,
        gain_loss=amount - last_amount,
        investment=investment,
        xirr=report.xirr,
        saving_ratio=saving_ratio,
        daily_report=report,
    )


class MultiplePeriodInventory(NamedTuple):
    inventories: dict[str, Inventory]
    start_inclusive: datetime.date
    end_exclusive: datetime.date


def _fill_multiple_period_inventory(
    entries: list[Directive],  # type: ignore
    accounts: set[str],
    multiple_period_inventories: list[MultiplePeriodInventory],
):
    for entry in entries:
        if not isinstance(entry, data.Transaction):
            continue

        for posting in entry.postings:
            if posting.account in accounts:
                for mpi in multiple_period_inventories:
                    if posting.account not in mpi.inventories:
                        mpi.inventories[posting.account] = Inventory()

                    if mpi.start_inclusive <= entry.date < mpi.end_exclusive:
                        mpi.inventories[posting.account].add_position(posting)


def grouped_account_compared_balance(
    entries: list[Directive],  # type: ignore
    price_map: dict,
    account_prefix: str,
    date_range: tuple[datetime.date, datetime.date],
    yoy_date_range: tuple[datetime.date, datetime.date],
    today: datetime.date,
    target_currency: str,
) -> list[AccountComparedBalance]:
    accounts = set([x for x in getters.get_accounts(entries) if x.startswith(account_prefix)])

    current_mpi = MultiplePeriodInventory(inventories={}, start_inclusive=date_range[0], end_exclusive=date_range[1])
    yoy_mpi = MultiplePeriodInventory(
        inventories={},
        start_inclusive=yoy_date_range[0],
        end_exclusive=yoy_date_range[1],
    )
    today_mpi = MultiplePeriodInventory(
        inventories={},
        start_inclusive=date_range[0],
        end_exclusive=today + datetime.timedelta(days=1),
    )

    _fill_multiple_period_inventory(entries, accounts, [current_mpi, yoy_mpi, today_mpi])

    result: list[AccountComparedBalance] = []
    for account in accounts:
        period_balance = convert_period_inventory(
            PeriodInventory(
                start_inclusive=date_range[0],
                end_exclusive=date_range[1],
                inventory=current_mpi.inventories[account],
            ),
            price_map,
            target_currency,
        )

        yoy_period_balance = convert_period_inventory(
            PeriodInventory(
                start_inclusive=yoy_date_range[0],
                end_exclusive=yoy_date_range[1],
                inventory=yoy_mpi.inventories[account],
            ),
            price_map,
            target_currency,
        )

        today_balance = convert_period_inventory(
            PeriodInventory(
                start_inclusive=date_range[0],
                end_exclusive=today + datetime.timedelta(days=1),
                inventory=today_mpi.inventories[account],
            ),
            price_map,
            target_currency,
        )

        elapsed_days = (today + datetime.timedelta(days=1) - date_range[0]).days
        total_days = (date_range[1] - date_range[0]).days
        elapsed_percentage = Decimal(elapsed_days / total_days)
        if elapsed_percentage > 0:
            predict_balance = today_balance.amount / elapsed_percentage
        else:
            predict_balance = 0

        predict_remains = yoy_period_balance.amount - predict_balance

        result.append(
            AccountComparedBalance(
                account=account,
                period=date_range,
                period_balance=period_balance.amount,
                yoy_period_balance=yoy_period_balance.amount,
                today_balance=today_balance.amount,
                today=today,
                currency=target_currency,
                balance_progress=yoy_period_balance.amount and period_balance.amount / yoy_period_balance.amount,
                date_progress=elapsed_percentage,
                predict_balance=predict_balance,
                predict_remains=predict_remains,
                remains=yoy_period_balance.amount - today_balance.amount,
            )
        )

    result.sort(key=lambda x: x.yoy_period_balance, reverse=True)
    return result
