from datetime import date
from decimal import Decimal
from typing import TypeVar

from beancount.core import data
from beancount.core.convert import convert_amount
from beancount.core.inventory import Inventory
from beancount.core.prices import PriceMap
from beangrow.investments import AccountData, Cat

from doujia.portfolio.processor import TransactionProcessor

Directive = TypeVar("Directive", bound=data.Directive)  # type: ignore
Transaction = TypeVar("Transaction", bound=data.Transaction)  # type: ignore

inventory_processor = TransactionProcessor()


def reduce_inventory(memo: Inventory, transaction: Transaction) -> Inventory:
    for posting in transaction.postings:
        if posting.meta["category"] == Cat.ASSET:
            memo.add_position(posting)

    return memo


inventory_processor.register(
    categories_list=[
        [Cat.ASSET, Cat.CASH],
        [Cat.ASSET, Cat.CASH, Cat.DIVIDEND],
        [Cat.ASSET, Cat.CASH, Cat.EXPENSES],
        [Cat.ASSET, Cat.CASH, Cat.INCOME],
        [Cat.ASSET, Cat.CASH, Cat.EXPENSES, Cat.INCOME],
    ],
    description="基础的资产买卖交易",
    func=reduce_inventory,
)

inventory_processor.register(
    categories_list=[
        [Cat.CASH, Cat.DIVIDEND],
        [Cat.CASH, Cat.DIVIDEND, Cat.EXPENSES],
    ],
    description="除息",
    func=lambda memo, _: memo,
)

inventory_processor.register(
    categories_list=[
        [Cat.ASSET, Cat.DIVIDEND],
    ],
    description="合股",
    func=lambda memo, _: memo,
)


def split_transactions(
    account_datas: list[AccountData], begin_date: date | None
) -> tuple[list[Transaction], list[Transaction]]:
    before_begin_transactions = []
    after_begin_transactions = []
    for account_data in account_datas:
        if begin_date is not None:
            before_begin_transactions.extend(
                filter(lambda x: x.date <= begin_date, account_data.transactions)
            )
            after_begin_transactions.extend(
                filter(lambda x: x.date > begin_date, account_data.transactions)
            )
        else:
            after_begin_transactions.extend(account_data.transactions)

    before_begin_transactions.sort(key=lambda x: x.date)
    after_begin_transactions.sort(key=lambda x: x.date)
    return before_begin_transactions, after_begin_transactions


def prepare_inventory_and_transactions(
    account_datas: list[AccountData], begin_date: date | None
) -> tuple[Inventory, list[Transaction]]:
    before_begin_transactions, after_begin_transactions = split_transactions(
        account_datas, begin_date
    )

    begin_inventory = inventory_processor.reduce_transactions(
        Inventory(),
        before_begin_transactions,
    )

    return begin_inventory, after_begin_transactions


def balance_at(
    inventory: Inventory, price_map: PriceMap, target_currency: str, at_date: date
) -> data.Amount:
    balance = data.Amount(Decimal(0), target_currency)
    for posting in inventory.get_positions():
        amount = convert_amount(
            posting.units,
            target_currency=target_currency,
            price_map=price_map,
            date=at_date,
            via=["HKD", "CNY", "USD"],
        )
        assert amount.currency == target_currency
        balance = data.Amount(balance.number + amount.number, target_currency)

    return balance
