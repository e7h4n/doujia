from datetime import datetime
from decimal import Decimal
from typing import TypeVar

from beancount.core import data
from freezegun import freeze_time

from doujia.server.logic.utils import insert_missing_balance, sort_transactions
from doujia.utils.util import get_last_transaction_date

Directive = TypeVar("Directive", bound=data.Directive)


def test_sort_transactions(entries: list[Directive]):
    """
    @@@/main.bean
    2024-01-01 open Assets:Short:Current:CCB
    2024-01-01 open Expenses:Food

    2024-01-01 *
        Assets:Short:Current:CCB  -100 CNY
        Expenses:Food

    2024-01-02 *
        Assets:Short:Current:CCB  -100 CNY
        Expenses:Food
    """

    transactions = [entry for entry in entries if isinstance(entry, data.Transaction)]
    assert len(transactions) == 2
    sorted_transactions = sort_transactions(
        [
            transactions[1],
            transactions[0],
        ]
    )
    assert len(sorted_transactions) == 2
    assert sorted_transactions[0].date.day == 1


def test_sort_transactions_by_time(entries: list[Directive]):
    """
    @@@/main.bean
    2024-01-01 open Assets:Short:Current:CCB
    2024-01-01 open Expenses:Food

    2024-01-01 * "first"
        time: "00:40:19"
        Assets:Short:Current:CCB  -100 CNY
        Expenses:Food

    2024-01-01 * "second"
        time: "01:40:19"
        Assets:Short:Current:CCB  -100 CNY
        Expenses:Food
    """

    transactions = [entry for entry in entries if isinstance(entry, data.Transaction)]
    assert len(transactions) == 2
    sorted_transactions = sort_transactions(
        [
            transactions[1],
            transactions[0],
        ]
    )
    assert len(sorted_transactions) == 2
    assert sorted_transactions[0].narration == "first"


@freeze_time("2024-01-20")
def test_try_insert_missing_balance_1(entries: list[Directive]):
    # 插入一个 last balance 之前的 balance 不生效
    """
    @@@/main.bean
    2024-01-01 open Assets:Short:Current:CCB
    2024-01-01 open Income:Salary

    2024-01-09 *
        Assets:Short:Current:CCB  100 CNY
        Income:Salary

    2024-01-10 balance Assets:Short:Current:CCB 100 CNY
    """

    txn = insert_missing_balance(
        account="Assets:Short:Current:CCB",
        date=datetime(2024, 1, 9).date(),
        amount=data.Amount(Decimal("100"), "CNY"),
        ledger_file="/main.bean",
    )

    assert txn is None


@freeze_time("2024-01-09")
def test_try_insert_missing_balance_2(entries: list[Directive]):
    # 当天时间还没有晚于插入的 balance 日期的话不生效
    """
    @@@/main.bean
    2024-01-01 open Assets:Short:Current:CCB
    2024-01-01 open Income:Salary

    2024-01-09 *
        Assets:Short:Current:CCB  100 CNY
        Income:Salary
    """

    txn = insert_missing_balance(
        account="Assets:Short:Current:CCB",
        date=datetime(2024, 1, 9).date(),
        amount=data.Amount(Decimal("100"), "CNY"),
        ledger_file="/main.bean",
    )

    assert txn is None


@freeze_time("2024-01-10")
def test_try_insert_missing_balance_3(entries: list[Directive]):
    # 当天时间晚于插入的 balance 日期的话插入一条 balance 交易
    """
    @@@/main.bean
    2024-01-01 open Assets:Short:Current:CCB
    2024-01-01 open Income:Salary

    2024-01-09 *
        Assets:Short:Current:CCB  100 CNY
        Income:Salary
    """

    txn = insert_missing_balance(
        account="Assets:Short:Current:CCB",
        date=datetime(2024, 1, 9).date(),
        amount=data.Amount(Decimal("100"), "CNY"),
        ledger_file="/main.bean",
    )

    assert txn is not None
    with open("/main.bean") as f:
        content = f.read().strip()
        assert (
            """2024-01-01 open Assets:Short:Current:CCB
2024-01-01 open Income:Salary

2024-01-09 *
    Assets:Short:Current:CCB                 100 CNY
    Income:Salary
2024-01-10 balance Assets:Short:Current:CCB  100 CNY
""".strip()
        ) == content


def test_get_last_transaction_date(entries: list[Directive]):
    """
    @@@/main.bean
    2024-01-01 open Assets:Short:Current:CCB
    2024-01-01 open Expenses:Food
    2024-01-01 *
        Assets:Short:Current:CCB  -100 CNY
        Expenses:Food
    """

    last_date = get_last_transaction_date(main_file_path="/main.bean", account_name="Assets:Short:Current:CCB")
    assert last_date is not None
    assert last_date.year == 2024
    assert last_date.month == 1
    assert last_date.day == 1
