from datetime import datetime

import pytz
import requests
from beancount.core.data import Amount, Decimal

from doujia.price.cache import PriceCache, symbol_price_cache

ACCEPT = "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7"  # noqa: E501
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"  # noqa: E501
FIELDS = "regularMarketPrice,postMarketPrice,preMarketPrice,marketCap,regularMarketTime,postMarketTime,preMarketTime"


YAHOO_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",  # noqa: E501
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def _get_crumb():
    session = requests.Session()
    session.get("https://finance.yahoo.com", headers=YAHOO_HEADERS)

    crumb_response = session.get("https://query2.finance.yahoo.com/v1/test/getcrumb", headers=YAHOO_HEADERS)
    if crumb_response.status_code == 200 and crumb_response.text:
        return (crumb_response.text, session)

    return None


def request_yahoo_finance(symbols: list[str]):
    (crumb, session) = _get_crumb()

    params = {
        "lang": "en-US",
        "region": "US",
        "corsDomain": "finance.yahoo.com",
        "fields": FIELDS,
        "formatted": "true",
        "symbols": ",".join(symbols),
        "crumb": crumb,
    }

    url = "https://query1.finance.yahoo.com/v7/finance/quote"
    resp = session.get(url, params=params, headers=YAHOO_HEADERS)

    data = resp.json()

    if "quoteResponse" not in data:
        raise ValueError(f"no quoteResponse in {data}")

    return data


def get_realtime_prices(symbols: list[str]) -> dict[str, PriceCache]:
    """
    从缓存中获取价格, 如果缓存中没有则返回0
    """
    if not symbols:
        return {}

    prices: dict[str, PriceCache] = {}
    for symbol in symbols:
        cached = symbol_price_cache.get(symbol)
        if cached:
            prices[symbol] = cached
        else:
            print(f"no price for {symbol}")

    return prices


def update_price_cache(symbols: list[str]):
    """
    从Yahoo Finance获取最新价格并更新缓存
    """
    if not symbols:
        return

    for attempt in range(3):
        try:
            resp = request_yahoo_finance(symbols)
            break
        except ValueError as e:
            if attempt == 2:
                raise e

    prices = {}
    price_dates = {}
    for result in resp["quoteResponse"]["result"]:
        symbol = result["symbol"]

        # Get exchange timezone
        if "exchangeTimezoneName" not in result:
            exchange_tz = pytz.utc
        else:
            exchange_tz = pytz.timezone(result["exchangeTimezoneName"])

        if result["hasPrePostMarketData"] and result["marketState"] == "PRE" and "preMarketPrice" in result:
            price = result["preMarketPrice"]["raw"]
            time = result["preMarketTime"]["raw"]
        else:
            if "regularMarketPrice" not in result:
                print(f"no regularMarketPrice in {result}, symbol: {symbol}")
                continue
            price = result["regularMarketPrice"]["raw"]
            time = result["regularMarketTime"]["raw"]

        # Convert timestamp to exchange timezone
        time = datetime.fromtimestamp(time, tz=pytz.UTC).astimezone(exchange_tz).date()
        price = Amount(Decimal(price), result["currency"])
        prices[symbol] = price
        price_dates[symbol] = time

    # 更新缓存
    symbol_price_cache.update_batch(prices, price_dates)
