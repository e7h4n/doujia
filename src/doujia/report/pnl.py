from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import TypeVar

from beancount.core import data
from beancount.core.amount import Amount
from beancount.core.convert import convert_amount
from beancount.core.inventory import Inventory
from beancount.core.prices import PriceMap
from beangrow.investments import AccountData, Cat
from logzero import logger

from doujia.portfolio.processor import TransactionProcessor
from doujia.report.util import prepare_inventory_and_transactions

Directive = TypeVar("Directive", bound=data.Directive)  # type: ignore
Transaction = TypeVar("Transaction", bound=data.Transaction)  # type: ignore

pnl_processor = TransactionProcessor()


@dataclass
class PnL:
    realized_pnl_ex_fee: Decimal
    fee: Decimal
    dividend_ex_tax: Decimal
    dividend_tax: Decimal
    unrealized_pnl: Decimal
    currency: str


@dataclass
class PnlMemo:
    price_map: PriceMap
    target_currency: str
    inventory: Inventory
    realized_pnl: Decimal
    fee: Decimal
    dividend: Decimal
    dividend_tax: Decimal
    end_date: date


def _finalize_pnl(memo: PnlMemo) -> PnL:
    unrealized_pnl = _get_unrealized_pnl(memo.inventory, memo.price_map, memo.target_currency, memo.end_date)

    return PnL(
        realized_pnl_ex_fee=memo.realized_pnl - memo.fee,
        fee=memo.fee,
        dividend_ex_tax=memo.dividend - memo.dividend_tax,
        dividend_tax=memo.dividend_tax,
        unrealized_pnl=unrealized_pnl,
        currency=memo.target_currency,
    )


def gen_pnl_data(
    account_datas: list[AccountData],
    price_map: PriceMap,
    target_currency: str,
    begin_date: date | None = None,
    end_date: date | None = None,
):
    if end_date is None:
        end_date = date.today()

    inventory, transactions = prepare_inventory_and_transactions(account_datas, begin_date)

    return pnl_processor.reduce_transactions(
        PnlMemo(
            price_map=price_map,
            target_currency=target_currency,
            inventory=inventory,
            realized_pnl=Decimal("0"),
            fee=Decimal("0"),
            dividend=Decimal("0"),
            dividend_tax=Decimal("0"),
            end_date=end_date,
        ),
        transactions,
        finalize=_finalize_pnl,
    )


def _get_unrealized_pnl(inventory: Inventory, price_map: PriceMap, target_currency: str, end_date: date) -> Decimal:
    total_cost_amount = Decimal("0")
    market_value = Decimal("0")
    for position in inventory.average():
        logger.debug(f"unrealized_pnl position: {position}")
        if position.cost is None:
            cost_amount = position.units
        else:
            cost_amount = Amount(position.units.number * position.cost.number, position.cost.currency)

        cost_amount = convert_amount(
            cost_amount,
            target_currency=target_currency,
            price_map=price_map,
            date=end_date,
            via=["USD", "HKD", "CNY"],
        )
        market_value_amount = convert_amount(
            position.units,
            target_currency=target_currency,
            price_map=price_map,
            date=end_date,
            via=["USD", "HKD", "CNY"],
        )
        assert market_value_amount.currency == target_currency
        market_value += market_value_amount.number
        total_cost_amount += cost_amount.number

    return market_value - total_cost_amount


def reduce_dividend_transaction(memo: PnlMemo, transaction: Transaction) -> PnlMemo:
    for posting in transaction.postings:
        if posting.meta["category"] == Cat.DIVIDEND:
            memo.dividend += (
                Decimal("0")
                - convert_amount(
                    posting.units,
                    target_currency=memo.target_currency,
                    price_map=memo.price_map,
                ).number
            )
        elif posting.meta["category"] == Cat.EXPENSES:
            tax = convert_amount(
                posting.units,
                target_currency=memo.target_currency,
                price_map=memo.price_map,
                date=transaction.date,
                via=["USD", "HKD", "CNY"],
            ).number
            memo.dividend_tax += tax
    return memo


def reduce_split_transaction(memo: PnlMemo, transaction: Transaction) -> PnlMemo:
    for posting in transaction.postings:
        if posting.meta["category"] == Cat.ASSET:
            memo.inventory.add_position(posting)

    return memo


def reduce_asset_transaction(memo: PnlMemo, transaction: Transaction) -> PnlMemo:
    for posting in transaction.postings:
        if posting.meta["category"] == Cat.ASSET:
            memo.inventory.add_position(posting)
        elif posting.meta["category"] == Cat.INCOME:
            memo.realized_pnl += (
                Decimal("0")
                - convert_amount(
                    posting.units,
                    target_currency=memo.target_currency,
                    price_map=memo.price_map,
                    date=transaction.date,
                    via=["USD", "HKD", "CNY"],
                ).number
            )
        elif posting.meta["category"] == Cat.EXPENSES:
            fee = convert_amount(
                posting.units,
                target_currency=memo.target_currency,
                price_map=memo.price_map,
                date=transaction.date,
                via=["USD", "HKD", "CNY"],
            ).number
            memo.fee += fee

    return memo


pnl_processor.register(
    categories_list=[
        [Cat.ASSET, Cat.CASH],
        [Cat.ASSET, Cat.CASH, Cat.EXPENSES],
        [Cat.ASSET, Cat.CASH, Cat.INCOME],
        [Cat.ASSET, Cat.CASH, Cat.EXPENSES, Cat.INCOME],
    ],
    description="基础的资产买卖交易",
    func=reduce_asset_transaction,
)

pnl_processor.register(
    categories_list=[
        [Cat.CASH, Cat.DIVIDEND],
        [Cat.ASSET, Cat.CASH, Cat.DIVIDEND],
        [Cat.CASH, Cat.DIVIDEND, Cat.EXPENSES],
    ],
    description="除息",
    func=reduce_dividend_transaction,
)

pnl_processor.register(
    categories_list=[
        [Cat.ASSET, Cat.DIVIDEND],
    ],
    description="合股",
    func=reduce_split_transaction,
)
