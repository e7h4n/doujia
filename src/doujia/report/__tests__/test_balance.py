import datetime
from decimal import Decimal

from beancount.core import data
from beancount.core.prices import build_price_map
from fava.core import FavaLedger
from typing import TypeVar
from doujia.report.balance import balance_at

Directive = TypeVar("Directive", bound=data.Directive)  # type: ignore


def test_balance_at_basic(entries: list[Directive]):
    """
    @@@/main.bean
    2020-01-01 open Assets:A
    2020-01-01 open Assets:B

    2020-01-01 *
        Assets:A 100 CNY
        Assets:B
    """
    balance = balance_at(
        entries,
        datetime.date(2020, 1, 2),
        ["Assets:A"],
        "CNY",
        build_price_map(entries),
    )
    assert balance == Decimal(100)


def test_balance_at_should_not_include_end_date(entries: list[Directive]):
    """
    @@@/main.bean
    2020-01-01 open Assets:A
    2020-01-01 open Assets:B

    2020-01-01 *
        Assets:A 100 CNY
        Assets:B
    """
    balance = balance_at(
        entries,
        datetime.date(2020, 1, 1),
        ["Assets:A"],
        "CNY",
        build_price_map(entries),
    )
    assert balance == Decimal(0)


def test_balance_at_should_convert_currency(entries: list[Directive]):
    """
    @@@/main.bean
    2020-01-01 open Assets:A
    2020-01-01 open Assets:B

    2020-01-01 price USD 7 CNY

    2020-01-01 *
        Assets:A 100 USD
        Assets:B
    """
    balance = balance_at(
        entries,
        datetime.date(2020, 1, 2),
        ["Assets:A"],
        "CNY",
        build_price_map(entries),
    )
    assert balance == Decimal(700)


def test_balance_at_should_match_account_prefix(entries: list[Directive]):
    """
    @@@/main.bean
    2020-01-01 open Assets:A:Sub
    2020-01-01 open Assets:B

    2020-01-01 *
        Assets:A:Sub 100 CNY
        Assets:B
    """
    balance = balance_at(
        entries,
        datetime.date(2020, 1, 2),
        ["Assets:A"],
        "CNY",
        build_price_map(entries),
    )
    assert balance == Decimal(100)


def test_balance_at_should_sum_multiple_transactions(entries: list[Directive]):
    """
    @@@/main.bean
    2020-01-01 open Assets:A
    2020-01-01 open Assets:B

    2020-01-01 *
        Assets:A 100 CNY
        Assets:B

    2020-01-02 *
        Assets:A 50 CNY
        Assets:B
    """
    balance = balance_at(
        entries,
        datetime.date(2020, 1, 3),
        ["Assets:A"],
        "CNY",
        build_price_map(entries),
    )
    assert balance == Decimal(150)
