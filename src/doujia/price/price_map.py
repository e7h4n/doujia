from datetime import date

from beancount.core.data import Directive, Price
from beancount.core.getters import get_commodity_directives
from beancount.core.prices import build_price_map, get_price

from doujia.price.yahoo import get_realtime_prices, update_price_cache


def get_last_and_realtime_price_map(entries: list[Directive]):  # type: ignore
    commodity_map = get_commodity_directives(entries)
    symbols = _get_yahoo_symbols(commodity_map)
    last_price_map = build_price_map(entries)
    realtime_price_map = _build_realtime_price_map(entries, symbols)
    return last_price_map, realtime_price_map


def build_realtime_price_cache(entries: list[Directive]):
    commodity_map = get_commodity_directives(entries)
    symbols = _get_yahoo_symbols(commodity_map)
    update_price_cache(list(symbols.values()))


def _get_yahoo_symbols(commodity_map):
    symbols = dict()
    for currency, commodity in commodity_map.items():
        if "price" not in commodity.meta or not isinstance(commodity.meta["price"], str):
            continue

        if "=X" in commodity.meta["price"]:
            continue

        if "price" in commodity.meta and "yahoo/" in commodity.meta["price"]:
            symbols[currency] = commodity.meta["price"].split("/")[-1]
    return symbols


def _build_realtime_price_map(entries: list[Directive], symbols: dict):  # type: ignore
    symbol_to_price = get_realtime_prices(list(symbols.values()))
    new_entries = entries.copy()

    for currency, symbol in symbols.items():
        symbol_price = symbol_to_price[symbol]
        existed_price = get_price(
            build_price_map(entries),
            (currency, symbol_price.currency),
            date=date.today(),
        )
        if existed_price and existed_price[0] == date.today():
            continue

        price = Price(
            date=date.today(),
            meta=None,
            currency=currency,
            amount=symbol_to_price[symbol],
        )
        new_entries.append(price)

    return build_price_map(new_entries)
