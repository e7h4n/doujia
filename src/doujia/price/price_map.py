from beancount.core.data import Directive, Price
from beancount.core.getters import get_commodity_directives
from beancount.core.prices import PriceMap, build_price_map, get_price

from doujia.price.yahoo import get_realtime_prices, update_price_cache


def get_last_and_realtime_price_map(entries: list[Directive]):  # type: ignore
    commodity_map = get_commodity_directives(entries)
    symbols = _get_yahoo_symbols(commodity_map)
    last_price_map = build_price_map(entries)
    realtime_price_map: PriceMap = _build_realtime_price_map(entries, symbols)

    latest_date = None
    for pair in realtime_price_map.forward_pairs:
        if pair[0] not in symbols:
            continue

        for price_date, _ in realtime_price_map[pair]:
            if not latest_date or price_date > latest_date:
                latest_date = price_date

    if latest_date is not None:
        for pair in last_price_map.forward_pairs:
            if pair[0] not in symbols:
                continue

            last_price_map[pair] = [
                (price_date, price) for price_date, price in last_price_map[pair] if price_date < latest_date
            ]
            reversed_pair = (pair[1], pair[0])
            last_price_map[reversed_pair] = [
                (price_date, price) for price_date, price in last_price_map[reversed_pair] if price_date < latest_date
            ]

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
        if symbol not in symbol_to_price:
            continue

        cached_price = symbol_to_price[symbol]
        symbol_price = cached_price.price

        existed_price = get_price(
            build_price_map(entries),
            (currency, symbol_price.currency),
            date=cached_price.price_date,
        )
        if existed_price and existed_price[0] == cached_price.price_date:
            continue

        price = Price(
            date=cached_price.price_date,
            meta=None,
            currency=currency,
            amount=symbol_price,
        )
        new_entries.append(price)

    return build_price_map(new_entries)
