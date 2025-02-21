import datetime
from decimal import Decimal
from pathlib import Path
from typing import NamedTuple

import beangrow.config as configlib
import beangrow.returns as returnslib
from beancount.core import convert, getters
from beancount.core.data import Directive, Transaction
from beancount.core.inventory import Inventory
from beangrow import investments
from beangrow.config_pb2 import Config
from frozendict import frozendict

from doujia.price.price_map import get_last_and_realtime_price_map

EMPTY_MAP = frozendict()


class PeriodInventory(NamedTuple):
    start_inclusive: datetime.date
    end_exclusive: datetime.date
    inventory: Inventory


class PeriodAmount(NamedTuple):
    start_inclusive: datetime.date
    end_exclusive: datetime.date
    amount: Decimal
    currency: str


def _sum_inventory_between(
    entries: list[Directive],  # type: ignore
    account_prefix_list: list[str],
    date_range: tuple[datetime.date, datetime.date],
) -> Inventory:
    result = Inventory()
    for entry in entries:
        if isinstance(entry, Transaction) and date_range[0] <= entry.date < date_range[1]:
            for posting in entry.postings:
                founds = False
                for account_prefix in account_prefix_list:
                    if posting.account.startswith(account_prefix):
                        founds = True
                        break

                if founds:
                    result.add_position(posting)

    return result


def _get_only_amount_number(inventory: Inventory, expect_currency: str) -> Decimal:
    pos = inventory.get_only_position()
    if pos:
        assert pos.units.currency == expect_currency
        return pos.units.number

    return Decimal(0)


def sum_inventory_between(
    entries: list[Directive],  # type: ignore
    account_prefix_list: list[str],
    date_range: list[tuple[datetime.date, datetime.date]],
) -> list[PeriodInventory]:
    return [(PeriodInventory(x[0], x[1], _sum_inventory_between(entries, account_prefix_list, x))) for x in date_range]


def sum_single_amount_between(
    entries: list[Directive],  # type: ignore
    price_map: dict,  # type: ignore
    account_prefix_list: list[str],
    date_range: list[tuple[datetime.date, datetime.date]],
    target_currency: str,
) -> list[PeriodAmount]:
    return [
        convert_period_inventory(x, price_map, target_currency)
        for x in sum_inventory_between(entries, account_prefix_list, date_range)
    ]


def convert_period_inventory(period_inventory: PeriodInventory, price_map: dict, target_currency: str) -> PeriodAmount:
    return PeriodAmount(
        start_inclusive=period_inventory.start_inclusive,
        end_exclusive=period_inventory.end_exclusive,
        amount=_get_only_amount_number(
            period_inventory.inventory.reduce(
                convert.convert_position,
                target_currency,
                price_map,
                period_inventory.end_exclusive - datetime.timedelta(days=1),
            ),
            target_currency,
        ),
        currency=target_currency,
    )


def _extract_beangrow_config(
    entries: list[Directive],  # type: ignore
    beangrow_config_path: Path,
) -> Config:  # type: ignore
    accounts = getters.get_accounts(entries)
    return configlib.read_config(str(beangrow_config_path), [], accounts)


def calc_xirr(
    entries: list[Directive],  # type: ignore
    beangrow_config_path: Path,
    options_map: dict,
    end_date: datetime.date,
    currency: str,
) -> Decimal:
    config: Config = _extract_beangrow_config(entries, beangrow_config_path)  # type: ignore
    _, price_map = get_last_and_realtime_price_map(entries)

    pricer = returnslib.Pricer(price_map)

    account_data_map = investments.extract(
        entries,
        options_map["dcontext"],
        config,
        end_date,
        False,
        "",
    )

    group = None
    for group in config.groups.group:
        if group.name == "All":
            break

    if group:
        adlist = [account_data_map[name] for name in group.investment if name in account_data_map]

        truncated_cash_flows = returnslib.truncate_and_merge_cash_flows(pricer, adlist, None, date_end=end_date)
        irr = returnslib.compute_returns(truncated_cash_flows, pricer, currency, end_date).total
    else:
        irr = Decimal(0)

    return irr
