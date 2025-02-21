from datetime import datetime, timedelta, timezone

import requests
from beancount.core.data import Amount, Decimal
from pytz import utc

from doujia.price.cache import symbol_price_cache

ACCEPT = "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7"  # noqa: E501
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"  # noqa: E501
FIELDS = "regularMarketPrice,postMarketPrice,preMarketPrice,marketCap,regularMarketTime,postMarketTime,preMarketTime"


def _get_crumbs_and_cookies():
    with requests.session():
        # 发一个请求到 https://query1.finance.yahoo.com/v1/test/getcrumb?lang=en-US&region=US 获取 crumb
        header = {
            "accept": ACCEPT,
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "zh-CN,zh;q=0.9",
            "dnt": "1",
            "priority": "u=0, i",
            "sec-ch-ua": '"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"macOS"',
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "none",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
            "user-agent": USER_AGENT,
        }
        url = "https://query1.finance.yahoo.com/v1/test/getcrumb?lang=en-US&region=US"

        website = requests.get(url, headers=header)

        return (header, website.text, website.cookies)


def request_yahoo_finance(symbols: list[str]):
    header, crumb, cookies = _get_crumbs_and_cookies()
    params = {
        "fields": FIELDS,
        "formatted": "true",
        "symbols": ",".join(symbols),
        "lang": "en-US",
        "region": "US",
        "crumb": crumb,
    }

    url = "https://query1.finance.yahoo.com/v7/finance/quote"
    resp = requests.get(url, headers=header, cookies=cookies, params=params).json()

    if "quoteResponse" not in resp:
        raise ValueError(f"no quoteResponse in {resp}")

    return resp


def get_realtime_prices(symbols: list[str]):
    """
    从缓存中获取价格, 如果缓存中没有则返回0
    """
    if not symbols:
        return {}

    prices = {}
    for symbol in symbols:
        cached = symbol_price_cache.get(symbol)
        if cached:
            prices[symbol] = cached.price
        else:
            print(f"no price for {symbol}")
            raise ValueError(f"no price for {symbol}")

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
    for result in resp["quoteResponse"]["result"]:
        symbol = result["symbol"]

        if result["hasPrePostMarketData"] and result["marketState"] == "PRE" and "preMarketPrice" in result:
            price = result["preMarketPrice"]["raw"]
            time = result["preMarketTime"]["raw"]
        # elif (
        #     result["hasPrePostMarketData"]
        #     and result["marketState"] == "POST"
        #     and "postMarketPrice" in result
        # ):
        #     price = result["postMarketPrice"]["raw"]
        #     time = result["postMarketTime"]["raw"]
        else:
            if "regularMarketPrice" not in result:
                print(f"no regularMarketPrice in {result}, symbol: {symbol}")
                continue
            price = result["regularMarketPrice"]["raw"]
            time = result["regularMarketTime"]["raw"]

        time = datetime.fromtimestamp(time, tz=utc).astimezone(timezone(timedelta(hours=8)))
        price = Amount(Decimal(price), result["currency"])
        prices[symbol] = price

    # 更新缓存
    symbol_price_cache.update_batch(prices)
