from beancount.core.inventory import Inventory
from frozendict import frozendict

from doujia.report.holding import holdings_at


EMPTY_MAP = frozendict()


def test_inventory_at(
    entries_options: tuple,
):  # 给定一个日期，返回这个日期时的所有持仓
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

    inventory: Inventory = holdings_at(
        entries_options[0],
        entries_options[1],
        ["Assets:Stock"],
    )

    assert len(inventory) == 1
