from beancount.core.data import Directive


def test_load_entries_from_doc(entries: list[Directive]):
    """
    @@@/main.bean
    2021-01-01 open Assets:Checking
    2021-01-01 open Expenses:Groceries

    2021-01-01 *
        Expenses:Groceries  100.00 USD
        Assets:Checking
    """
    assert len(entries) == 3
