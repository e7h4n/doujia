from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import TypeVar
from beancount.core import data
from beancount.core.inventory import Inventory
from beancount.core.prices import PriceMap
from beancount.core.convert import convert_amount
from beangrow.investments import AccountData, Cat
from doujia.portfolio.processor import TransactionProcessor
from logzero import logger

from doujia.report.util import balance_at, prepare_inventory_and_transactions


Directive = TypeVar("Directive", bound=data.Directive)  # type: ignore
Transaction = TypeVar("Transaction", bound=data.Transaction)  # type: ignore

nav_processor = TransactionProcessor()


@dataclass
class Nav:
    index: Decimal
    units: Decimal


@dataclass
class NavMemo:
    price_map: PriceMap
    target_currency: str
    inventory: Inventory
    units: Decimal
    index: Decimal
    history: dict[date, Nav]
    end_date: date
    last_date: date | None
    fill_gap_days: bool


def _finalize_nav(memo: NavMemo) -> list[tuple[date, Decimal]]:
    close_inventory(memo, close_date=memo.end_date)

    return [(d, nav.index) for d, nav in sorted(memo.history.items())]


def gen_nav_index_data(
    account_datas: list[AccountData],
    price_map: PriceMap,
    target_currency: str,
    fill_gap_days: bool = True,
    begin_date: date | None = None,
    end_date: date | None = None,
):
    if end_date is None:
        end_date = date.today()

    inventory, transactions = prepare_inventory_and_transactions(
        account_datas, begin_date
    )

    begin_units = Decimal(0)
    for postion in inventory:
        amount = convert_amount(
            postion.units,
            target_currency=target_currency,
            price_map=price_map,
            date=begin_date,
            via=["USD", "HKD", "CNY"],
        )
        assert amount.currency == target_currency
        begin_units += amount.number

    history = {}
    if begin_units > 0:
        history[begin_date] = Nav(index=Decimal(1), units=begin_units)

    return nav_processor.reduce_transactions(
        NavMemo(
            price_map=price_map,
            target_currency=target_currency,
            inventory=inventory,
            units=begin_units,
            index=Decimal(1),
            history=history,
            fill_gap_days=fill_gap_days,
            last_date=begin_date,
            end_date=end_date,
        ),
        transactions,
        finalize=_finalize_nav,
    )


def update_price(
    price_map: PriceMap, currency_pair: tuple[str, str], new_price: Decimal, date: date
):
    prices = price_map.get(currency_pair, [])
    insert_idx = 0
    for idx, (price_date, _) in enumerate(prices):
        if price_date == date:
            prices[idx] = (date, new_price)
            return
        if price_date < date:
            insert_idx = idx + 1
        else:
            break

    prices.insert(insert_idx, (date, new_price))
    price_map[currency_pair] = prices


def update_price_from_transaction(price_map: PriceMap, transaction: Transaction):
    inventory = Inventory()
    asset_currency = None
    cash_currency = None
    for posting in transaction.postings:
        if posting.meta["category"] == Cat.ASSET:
            asset_currency = posting.units.currency
            inventory.add_amount(posting.units)
        elif posting.meta["category"] == Cat.CASH:
            cash_currency = posting.units.currency
            inventory.add_amount(posting.units)

    total_assets = inventory.get_currency_units(asset_currency)
    total_cash = inventory.get_currency_units(cash_currency)
    if abs(total_assets.number) < 0.01 or abs(total_cash.number) < 0.01:
        return

    price = Decimal(0) - total_cash.number / total_assets.number
    logger.debug(
        f"""found price at {transaction.date}
{asset_currency} {total_assets}
{cash_currency} {total_cash}
price: {price}
"""
    )
    update_price(price_map, (asset_currency, cash_currency), price, transaction.date)
    update_price(
        price_map,
        (cash_currency, asset_currency),
        Decimal(1) / price,
        transaction.date,
    )


def sum_cash_from_transaction(transaction: Transaction) -> data.Amount:
    inventory = Inventory()
    for posting in transaction.postings:
        if posting.meta["category"] == Cat.CASH:
            inventory.add_amount(posting.units)

    amount = inventory.get_only_position().units
    return data.Amount(Decimal(0) - amount.number, amount.currency)


def update_inventory_from_transaction(inventory: Inventory, transaction: Transaction):
    for posting in transaction.postings:
        if posting.meta["category"] == Cat.ASSET:
            inventory.add_position(posting)


def fill_gap_days(memo: NavMemo, up_to_date_exclude: date):
    if not memo.fill_gap_days:
        return

    if memo.last_date is None or memo.last_date >= up_to_date_exclude:
        return memo

    last_date = memo.last_date
    while last_date < up_to_date_exclude:
        logger.debug(f"fill_gap_days: {last_date}")
        last_date += timedelta(days=1)
        pre_units = memo.units
        if abs(pre_units) < 0.01:  # 已经清仓的情况
            memo.last_date = last_date
            continue

        pre_balance = balance_at(
            memo.inventory, memo.price_map, memo.target_currency, last_date
        )
        post_index = pre_balance.number / pre_units
        memo.index = post_index
        memo.history[last_date] = Nav(index=post_index, units=pre_units)
        memo.last_date = last_date


def reduce_asset_transaction(memo: NavMemo, transaction: Transaction) -> NavMemo:
    fill_gap_days(memo, transaction.date)

    logger.debug(
        f"""memo
units: {memo.units}
index: {memo.index}
"""
    )
    update_price_from_transaction(memo.price_map, transaction)

    pre_balance = balance_at(
        memo.inventory, memo.price_map, memo.target_currency, transaction.date
    )

    if abs(memo.units) < 0.01:
        pre_index = memo.index
        pre_units = pre_balance.number / pre_index
    else:
        pre_units = memo.units
        pre_index = pre_balance.number / pre_units

    amount = convert_amount(
        sum_cash_from_transaction(transaction),
        target_currency=memo.target_currency,
        price_map=memo.price_map,
        date=transaction.date,
        via=["USD", "HKD", "CNY"],
    )
    post_units = pre_units + amount.number / pre_index
    memo.index = pre_index
    memo.units = post_units
    memo.history[transaction.date] = Nav(index=pre_index, units=post_units)
    memo.last_date = transaction.date

    logger.debug(
        f"""reduce_asset_transaction: {transaction.date}
pre_balance: {pre_balance}
pre_index: {pre_index}
pre_units: {pre_units}
amount: {amount}
post_units: {post_units}
post_index: {pre_index}
"""
    )

    update_inventory_from_transaction(memo.inventory, transaction)
    return memo


def reduce_close_saving(memo: NavMemo, transaction: Transaction) -> NavMemo:
    fill_gap_days(memo, transaction.date)

    logger.debug(
        f"""memo
units: {memo.units}
index: {memo.index}
"""
    )

    pre_balance = balance_at(
        memo.inventory, memo.price_map, memo.target_currency, transaction.date
    )

    pre_units = memo.units
    pre_index = pre_balance.number / pre_units

    dividend_inventory = Inventory()
    cash_inventory = Inventory()
    for posting in transaction.postings:
        if posting.meta["category"] == Cat.DIVIDEND:
            dividend_inventory.add_amount(posting.units)
        elif posting.meta["category"] == Cat.CASH:
            cash_inventory.add_amount(posting.units)

    dividend_amount = convert_amount(
        dividend_inventory.get_only_position().units,
        target_currency=memo.target_currency,
        price_map=memo.price_map,
        date=transaction.date,
        via=["USD", "HKD", "CNY"],
    )

    cash_amount = convert_amount(
        cash_inventory.get_only_position().units,
        target_currency=memo.target_currency,
        price_map=memo.price_map,
        date=transaction.date,
        via=["USD", "HKD", "CNY"],
    )

    post_index = (pre_balance.number - dividend_amount.number) / pre_units
    post_units = pre_units - cash_amount.number / post_index

    memo.index = post_index
    memo.units = post_units
    memo.history[transaction.date] = Nav(index=post_index, units=post_units)
    memo.last_date = transaction.date

    logger.debug(
        f"""reduce_saving_close: {transaction.date}
pre_balance: {pre_balance}
pre_index: {pre_index}
pre_units: {pre_units}
dividend_amount: {dividend_amount}
cash_amount: {cash_amount}
post_units: {post_units}
post_index: {post_index}
"""
    )

    update_inventory_from_transaction(memo.inventory, transaction)
    return memo


def close_inventory(memo: NavMemo, close_date: date):
    fill_gap_days(memo, close_date)

    pre_balance = balance_at(
        memo.inventory, memo.price_map, memo.target_currency, close_date
    )
    pre_units = memo.units
    if abs(pre_balance.number) < 0.01:
        post_index = memo.index
    else:
        post_index = pre_balance.number / pre_units
    memo.index = post_index
    memo.history[close_date] = Nav(index=post_index, units=pre_units)
    memo.last_date = close_date

    logger.debug(
        f"""close
pre_balance: {pre_balance}
pre_units: {pre_units}
post_index: {post_index}
"""
    )
    return memo


def reduce_dividend_transaction(memo: NavMemo, transaction: Transaction) -> NavMemo:
    fill_gap_days(memo, transaction.date)

    inventory = Inventory()
    for posting in transaction.postings:
        if posting.meta["category"] == Cat.CASH:
            inventory.add_amount(posting.units)

    cash_amount = convert_amount(
        inventory.get_only_position().units,
        target_currency=memo.target_currency,
        price_map=memo.price_map,
        date=transaction.date,
        via=["USD", "HKD", "CNY"],
    )

    pre_balance = balance_at(
        memo.inventory, memo.price_map, memo.target_currency, transaction.date
    )

    pre_units = memo.units
    assert pre_balance.currency == cash_amount.currency
    in_dividend_balance = data.Amount(
        pre_balance.number + cash_amount.number, pre_balance.currency
    )

    post_index = in_dividend_balance.number / pre_units
    changed_units = cash_amount.number / post_index
    logger.debug(
        f"""reduce_dividend_transaction: {transaction.date}
pre_balance: {pre_balance}
pre_units: {pre_units}
cash_amount: {cash_amount}
in_dividend_balance: {in_dividend_balance}
post_index: {post_index}
changed_units: {changed_units}
"""
    )
    memo.units = pre_units - changed_units
    memo.index = post_index

    if abs(pre_balance.number - memo.units * memo.index) >= 0.0001:
        raise ValueError("Inconsistent balance after dividend adjustment")

    memo.history[transaction.date] = Nav(index=memo.index, units=memo.units)
    memo.last_date = transaction.date
    return memo


nav_processor.register(
    categories_list=[
        [Cat.ASSET, Cat.CASH],
        [Cat.ASSET, Cat.CASH, Cat.EXPENSES],
        [Cat.ASSET, Cat.CASH, Cat.INCOME],
        [Cat.ASSET, Cat.CASH, Cat.EXPENSES, Cat.INCOME],
    ],
    description="基础的资产买卖交易",
    func=reduce_asset_transaction,
)

nav_processor.register(
    categories_list=[
        [Cat.ASSET, Cat.CASH, Cat.DIVIDEND],
    ],
    description="存款到期",
    func=reduce_close_saving,
)
nav_processor.register(
    categories_list=[
        [Cat.CASH, Cat.DIVIDEND],
        [Cat.CASH, Cat.DIVIDEND, Cat.EXPENSES],
    ],
    description="除息",
    func=reduce_dividend_transaction,
)

nav_processor.register(
    categories_list=[
        [Cat.ASSET, Cat.DIVIDEND],
    ],
    description="合股",
    func=lambda memo, _: memo,
)
