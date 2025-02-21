import datetime

from beancount.core.data import Directive
from beancount.core.inventory import Inventory
from beancount.core.prices import build_price_map
from frozendict import frozendict

from doujia.report.summerize import (
    sum_inventory_between,
    sum_single_amount_between,
)

EMPTY_MAP = frozendict()

_I = Inventory.from_string


def test_single_amount(entries: list[Directive]):  # type: ignore # 计算单个时间段内的现金流
    """
    @@@/main.bean
    2021-01-01 open Assets:Checking
    2021-01-01 open Expenses:Groceries

    2021-01-01 *
        Expenses:Groceries  100.00 USD
        Assets:Checking
    """

    cash_flow_amounts = sum_inventory_between(
        entries, ["Expenses"], [(datetime.date(2021, 1, 1), datetime.date(2021, 2, 1))]
    )
    assert cash_flow_amounts[0] == (
        datetime.date(2021, 1, 1),
        datetime.date(2021, 2, 1),
        _I("100 USD"),
    )


def test_multiple_amount(entries: list[Directive]):  # type: ignore # 计算多个时间段内的现金流
    """
    @@@/main.bean
    2021-01-01 open Assets:Checking
    2021-01-01 open Expenses:Groceries

    2021-01-01 *
        Expenses:Groceries  100.00 USD
        Assets:Checking

    2021-01-02 *
        Expenses:Groceries  200.00 USD
        Assets:Checking
    """

    cash_flow_amounts = sum_inventory_between(
        entries,
        ["Expenses"],
        [
            (datetime.date(2021, 1, 1), datetime.date(2021, 1, 2)),
            (datetime.date(2021, 1, 2), datetime.date(2021, 1, 3)),
        ],
    )
    assert cash_flow_amounts[0] == (
        datetime.date(2021, 1, 1),
        datetime.date(2021, 1, 2),
        _I("100 USD"),
    )
    assert cash_flow_amounts[1] == (
        datetime.date(2021, 1, 2),
        datetime.date(2021, 1, 3),
        _I("200 USD"),
    )


def test_ignore_history_transaction(
    entries: list[Directive],  # type: ignore
):  # 计算现金流应该不考虑历史交易
    """
    @@@/main.bean
    2021-01-01 open Assets:Checking
    2021-01-01 open Expenses:Groceries

    2021-01-01 *
        Expenses:Groceries  100.00 USD
        Assets:Checking

    2021-01-02 *
        Expenses:Groceries  200.00 USD
        Assets:Checking
    """

    cash_flow_amounts = sum_inventory_between(
        entries,
        ["Expenses"],
        [
            (datetime.date(2021, 1, 2), datetime.date(2021, 1, 3)),
        ],
    )
    assert cash_flow_amounts[0] == (
        datetime.date(2021, 1, 2),
        datetime.date(2021, 1, 3),
        _I("200 USD"),
    )


def test_price(entries: list[Directive]):  # type: ignore # 计算现金流应该考虑价格，价格位期末价值
    """
    @@@/main.bean
    2021-01-01 open Assets:Checking
    2021-01-01 open Expenses:Groceries

    2021-01-01 price AAPL 1000 USD

    2021-01-01 *
        Expenses:Groceries  1 AAPL { 100 USD }
        Assets:Checking
    """
    price_map = build_price_map(entries)
    cash_flow_amounts = sum_single_amount_between(
        entries,
        price_map=price_map,
        account_prefix_list=["Expenses"],
        target_currency="USD",
        date_range=[
            (datetime.date(2021, 1, 1), datetime.date(2021, 1, 2)),
        ],
    )
    assert cash_flow_amounts[0][2] == 1000


def test_price_no_cost(
    entries: list[Directive],  # type: ignore
):  # 只有价格，没有 cost 的交易，应该只计算 unit
    """
    @@@/main.bean
    2021-01-01 open Assets:Checking
    2021-01-01 open Expenses:Groceries

    2021-01-01 *
        Expenses:Groceries  1 APPLE @ 100 CNY
        Assets:Checking
    """
    cash_flow_amounts = sum_inventory_between(
        entries,
        ["Expenses"],
        [
            (datetime.date(2021, 1, 1), datetime.date(2021, 1, 2)),
        ],
    )
    assert cash_flow_amounts[0][2] == _I("1 APPLE")


def test_price_via(entries: list[Directive]):  # type: ignore # 计算现金流时不考虑货币转换
    """
    @@@/main.bean
    2021-01-01 open Assets:Checking
    2021-01-01 open Expenses:Groceries

    2021-01-01 price USD 6.5 CNY

    2021-01-01 *
        Expenses:Groceries  1 AAPL { 100 USD }
        Assets:Checking
    """

    cash_flow_amounts = sum_inventory_between(
        entries,
        ["Expenses"],
        [
            (datetime.date(2021, 1, 1), datetime.date(2021, 1, 2)),
        ],
    )
    assert cash_flow_amounts[0][2] == _I("1 AAPL {100 USD, 2021-01-01}")


def test_ignore_price_map(
    entries: list[Directive],  # type: ignore
):  # 计算消耗掉特定商品时产生的现金流，不考虑货币转换
    """
    @@@/main.bean
    2021-01-01 open Assets:Checking
    2021-01-01 open Assets:Stock
    2021-01-01 open Expenses:Groceries

    2021-01-01 price PEAR 8 CNY
    2021-01-07 price PEAR 9 CNY
    2021-01-08 price PEAR 10 CNY

    2021-01-01 *
        Expenses:Groceries  -10 PEAR
        Assets:Checking 7 PEAR
        Assets:Stock 3 PEAR
    """

    cash_flow_amounts = sum_inventory_between(
        entries,
        ["Expenses"],
        [
            (datetime.date(2021, 1, 1), datetime.date(2021, 1, 7)),
        ],
    )
    assert cash_flow_amounts[0] == (
        datetime.date(2021, 1, 1),
        datetime.date(2021, 1, 7),
        _I("-10 PEAR"),
    )


def test_inventory_not_affected_by_price_up(
    entries: list[Directive],  # type: ignore
):  # 计算现金流库存时不考虑价格影响
    """
    @@@/main.bean
    2020-01-01 open Assets:Short
    2020-01-01 open Assets:Stock

    2022-01-01 price AAPL 10 CNY
    2022-01-01 !
        Assets:Short
        Assets:Stock 1 AAPL { 10 CNY }

    2022-01-30 price AAPL 100 CNY
    """

    cash_flow_amounts = sum_inventory_between(
        entries, ["Assets"], [(datetime.date(2022, 1, 1), datetime.date(2022, 2, 1))]
    )

    assert cash_flow_amounts[0] == (
        datetime.date(2022, 1, 1),
        datetime.date(2022, 2, 1),
        _I("-10 CNY, 1 AAPL {10 CNY, 2022-01-01}"),
    )


def test_amount_affected_by_price_up(
    entries: list[Directive],  # type: ignore
):  # 计算现金流总和时考虑价格影响
    """
    @@@/main.bean
    2020-01-01 open Assets:Short
    2020-01-01 open Assets:Stock

    2022-01-01 price AAPL 10 CNY
    2022-01-01 !
        Assets:Short
        Assets:Stock 1 AAPL { 10 CNY }

    2022-01-30 price AAPL 100 CNY
    """
    price_map = build_price_map(entries)
    cash_flow_amounts = sum_single_amount_between(
        entries,
        price_map,
        ["Assets"],
        [(datetime.date(2022, 1, 1), datetime.date(2022, 2, 1))],
        "CNY",
    )

    assert cash_flow_amounts[0] == (
        datetime.date(2022, 1, 1),
        datetime.date(2022, 2, 1),
        90,
        "CNY",
    )
