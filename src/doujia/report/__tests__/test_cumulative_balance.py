from datetime import date
from decimal import Decimal
from typing import TypeVar

from beancount.core import data

from doujia.report.cumulative_balance import gen_cumulative_balances

Directive = TypeVar("Directive", bound=data.Directive)  # type: ignore


def test_cumulative_balance_simple(entries: list[Directive]):
    """
    @@@/main.bean
    2020-01-01 commodity AAPL
    2020-01-01 open Assets:Current
    2020-01-01 open Expenses:Food

    2020-01-02 * "Buy some food"
        Assets:Current -100.00 CNY
        Expenses:Food

    """

    begin_date, end_date = (date(2020, 1, 1), date(2020, 1, 3))

    balances = gen_cumulative_balances(
        entries,
        account_prefix="Expenses",
        begin_date=begin_date,
        end_date_inclusive=end_date,
    )

    assert len(balances) == 3
    assert balances[0] == (date(2020, 1, 1), Decimal(0))
    assert balances[1] == (date(2020, 1, 2), Decimal(100.0))
    assert balances[2] == (date(2020, 1, 3), Decimal(100.0))


def test_cumulative_balance_date_range(entries: list[Directive]):
    """
    @@@/main.bean
    2020-01-01 commodity AAPL
    2020-01-01 open Assets:Current
    2020-01-01 open Expenses:Food

    2020-01-01 * "Buy some food"
        Assets:Current -1.00 CNY
        Expenses:Food

    2020-01-05 * "Buy some food"
        Assets:Current -10.00 CNY
        Expenses:Food

    2020-01-10 * "Buy some food"
        Assets:Current -100.00 CNY
        Expenses:Food
    """

    begin_date, end_date = (date(2020, 1, 5), date(2020, 1, 5))

    balances = gen_cumulative_balances(
        entries,
        account_prefix="Expenses",
        begin_date=begin_date,
        end_date_inclusive=end_date,
    )

    assert len(balances) == 1
    assert balances[0] == (date(2020, 1, 5), Decimal(10))
