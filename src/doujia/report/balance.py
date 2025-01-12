import datetime
from decimal import Decimal
from typing import Tuple, TypeVar

from beancount.core.convert import convert_amount
from beancount.core import data
from beancount.core.prices import PriceMap
from beancount.core.inventory import Inventory

Directive = TypeVar("Directive", bound=data.Directive)  # type: ignore
DataPoint = Tuple[datetime.date, Decimal]


def balance_at(
    entries: list[Directive],
    at_date: datetime.date,
    account_prefixes: list[str],
    target_currency: str,
    price_map: PriceMap,
) -> Decimal:
    """统计特定账户在 end 日期之前的 balance，不包括 end_exclude 这一天"""
    inventory = Inventory()

    for txn in entries:
        if not isinstance(txn, data.Transaction):
            continue

        if txn.date >= at_date:
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

    result = Decimal(0)
    for posting in inventory:
        amount = convert_amount(
            posting.units,
            target_currency,
            price_map,
            date=at_date,
            via=["CNY", "HKD", "USD"],
        )
        assert amount.currency == target_currency
        result += amount.number

    return result
