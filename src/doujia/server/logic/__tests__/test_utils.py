from typing import TypeVar

from beancount.core import data

from doujia.server.logic.utils import sort_transactions

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
