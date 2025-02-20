from decimal import Decimal
from typing import Tuple, TypeVar

from datetime import date

from beancount.core import data
from beancount.core.inventory import Inventory

from doujia.price.price_map import get_last_and_realtime_price_map
from doujia.report.util import balance_at


Directive = TypeVar("Directive", bound=data.Directive)  # type: ignore
Transaction = TypeVar("Transaction", bound=data.Transaction)  # type: ignore


def _filter_transactions(
    entries: list[Directive],
    account_prefix: str,
    begin_date: date,
    end_date: date,
) -> list[Transaction]:
    """筛选指定时间范围内的相关账户交易"""
    transactions = []
    for entry in entries:
        if isinstance(entry, data.Transaction):
            if entry.date < begin_date or entry.date > end_date:
                continue
            for posting in entry.postings:
                if posting.account.startswith(account_prefix):
                    transactions.append(entry)
                    break
    return transactions


def _calculate_balance_for_date(
    inventory: Inventory,
    price_map: dict,
    date: date,
    currency: str = "CNY",
) -> Decimal:
    """计算指定日期的余额"""
    balance = balance_at(inventory, price_map, currency, date)
    return balance.number


def _generate_balance_timeline(
    transactions: list[Transaction],
    account_prefix: str,
    inventory: Inventory,
    price_map: dict,
    begin_date: date,
    end_date: date,
) -> list[Tuple[date, Decimal]]:
    """生成余额时间线"""
    result = []
    last_date = None

    for transaction in transactions:
        current_date = transaction.date

        if current_date != last_date and last_date is not None:
            balance = _calculate_balance_for_date(inventory, price_map, last_date)
            result.append((last_date, balance))

        if last_date is None and current_date > begin_date:
            result.append((begin_date, Decimal(0)))

        last_date = current_date
        for posting in transaction.postings:
            if posting.account.startswith(account_prefix):
                inventory.add_amount(posting.units)

    # 处理最后的余额
    if last_date is not None:
        balance = _calculate_balance_for_date(inventory, price_map, last_date)
        result.append((last_date, balance))
        if last_date < end_date:
            result.append((end_date, balance))
    else:
        result.append((begin_date, Decimal(0)))
        result.append((end_date, Decimal(0)))

    return result


def gen_cumulative_balances(
    entries: list[Directive],
    account_prefix: str,
    begin_date: date,
    end_date_inclusive: date | None = None,
) -> list[Tuple[date, Decimal]]:
    """生成累计余额报表"""
    if end_date_inclusive is None:
        end_date_inclusive = date.today()

    transactions = _filter_transactions(
        entries, account_prefix, begin_date, end_date_inclusive
    )
    _, price_map = get_last_and_realtime_price_map(entries)
    inventory = Inventory()

    return _generate_balance_timeline(
        transactions,
        account_prefix,
        inventory,
        price_map,
        begin_date,
        end_date_inclusive,
    )
