from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import logzero
import pytest
from beancount.core.data import Commodity, Directive, Price
from beancount.core.inventory import Inventory
from beancount.core.prices import build_price_map
from freezegun import freeze_time
from frozendict import frozendict
from logzero import logger, logging

from doujia.price.price_map import build_realtime_price_cache
from doujia.price.yahoo import get_realtime_prices, request_yahoo_finance
from doujia.report.investment import (
    InvestmentHolding,
    get_investment_holdings,
)
from doujia.report.portfolio.portfolio import (
    create_portfolio_report,
)

EMPTY_MAP = frozendict()

_I = Inventory.from_string


@pytest.fixture(autouse=True)
def set_loglevel():
    original_loglevel = logger.level
    logzero.loglevel(logging.INFO)

    yield

    logzero.loglevel(original_loglevel)


def get_realtime_price_map(entries: list[Directive]):  # type: ignore
    commodities = []
    symbols = []
    symbol_to_commodity = {}
    for entry in entries:
        if isinstance(entry, Commodity):
            if "price" in entry.meta and "yahoo" in entry.meta["price"]:
                commodities.append(entry)
                symbol = entry.meta["price"].split("/")[-1]
                symbols.append(symbol)
                symbol_to_commodity[symbol] = entry

    symbol_to_prices = get_realtime_prices(symbols)

    # 遍历 symbol_to_commodity 生成当日的 price_map
    price_entries = []
    for symbol, commodity_entry in symbol_to_commodity.items():
        if symbol not in symbol_to_prices:
            logger.warning(f"no price for {symbol}")
            continue

        price = Price(
            date=date.today(),
            meta=None,
            currency=commodity_entry.currency,
            amount=symbol_to_prices[symbol],
        )
        price_entries.append(price)

    return build_price_map(price_entries)


@pytest.mark.skip
def test_fetch_yahoo_finance():
    resp = request_yahoo_finance(["CNY=X"])
    print(resp)
    assert False


def quote_resp(
    symbol: str,
    market_state: str,
    currency: str,
    regular_market: tuple[float, int],
    pre_market: tuple[float, int] = None,
    post_market: tuple[float, int] = None,
):
    if (pre_market is not None and post_market is None) or (
        pre_market is None and post_market is not None
    ):
        raise ValueError("pre_market 和 post_market 必须同时为 None 或者同时不为 None")

    return {
        "symbol": symbol,
        "marketState": market_state,
        "hasPrePostMarketData": pre_market is not None and post_market is not None,
        "currency": currency,
        "regularMarketPrice": {"raw": regular_market[0]},
        "regularMarketTime": {"raw": regular_market[1]},
        "preMarketPrice": {"raw": pre_market[0]} if pre_market else None,
        "preMarketTime": {"raw": pre_market[1]} if pre_market else None,
        "postMarketPrice": {"raw": post_market[0]} if post_market else None,
        "postMarketTime": {"raw": post_market[1]} if post_market else None,
    }


def test_get_investment_groups(entries: list[Directive]):  # type: ignore # 获取投资持仓
    """
    @@@/main.bean
    1970-01-01 commodity USD
        price: "CNY:pricehist.beanprice.yahoo/CNY=X"

    2020-01-09 commodity HSETF
        price: "CNY:pricehist.beanprice.yahoo/510310.SS"

    2009-11-20 commodity VOO
        price: "USD:pricehist.beanprice.yahoo/VOO"

    1993-01-29 commodity VWO
        price: "USD:pricehist.beanprice.yahoo/VWO"

    2023-07-18 price USD 7.170600 CNY

    2024-01-01 open Assets:Stock:US:VOO
    2024-01-01 open Assets:Current:US
    2024-05-06 price VOO 474.72 USD
    2024-05-06 *
        Assets:Stock:US:VOO 100.00 VOO { 474.72 USD }
        Assets:Current:US

    2024-01-01 open Assets:Stock:US:VWO
    2024-04-02 price VWO 42.18 USD
    2024-04-02 *
        Assets:Stock:US:VWO 100.00 VWO { 42.18 USD }
        Assets:Current:US

    2024-01-01 open Assets:Stock:CN
    2024-01-01 open Assets:Current:CN
    2024-04-08 price HSETF 1.7360 CNY
    2024-04-08 *
        Assets:Stock:CN 100.00 HSETF { 1.7360 CNY }
        Assets:Current:CN

    @@@/beangrow.pbtxt
    investments {
        investment {
            currency: "VOO"
            asset_account: "Assets:Stock:US:VOO"
            cash_accounts: "Assets:Current:US"
        }
        investment {
            currency: "VWO"
            asset_account: "Assets:Stock:US:VWO"
            cash_accounts: "Assets:Current:US"
        }
        investment {
            currency: "HSETF"
            asset_account: "Assets:Stock:CN"
            cash_accounts: "Assets:Current:CN"
        }
    }
    groups {
        group {
            name: "CN"
            investment: "Assets:Stock:CN"
            currency: "CNY"
        }
        group {
            name: "US"
            investment: "Assets:Stock:US:VOO"
            investment: "Assets:Stock:US:VWO"
            currency: "USD"
        }
    }

    @@@/config/investment_distribution.yaml
    currency: USD
    investments:
      - group: CN
        ratio: 0.50
        xirr: 0.10
      - group: US
        ratio: 0.50
        xirr: 0.10
    """

    investment_groups = get_investment_holdings(
        entries,
        Path("./beangrow.pbtxt"),
        Path("./config/investment_distribution.yaml"),
        {"dcontext": None},
        date.today(),
    )
    assert len(investment_groups) == 2
    assert investment_groups[0].name == "CN"
    assert investment_groups[1].name == "US"
    assert investment_groups[0].expected_ratio == 0.5
    assert len(investment_groups[0].inventory) == 1
    assert len(investment_groups[1].inventory) == 2


@patch("doujia.price.yahoo.request_yahoo_finance")
@freeze_time("2024-10-21")
def test_get_investment_report(mock_request_yahoo_finance, entries: list[Directive]):  # type: ignore # 验证通过 yahoo finance 获取实时价格
    """
    @@@/main.bean
    1970-01-01 commodity USD
        price: "CNY:pricehist.beanprice.yahoo/CNY=X"

    2020-01-09 commodity HSETF
        price: "CNY:pricehist.beanprice.yahoo/510310.SS"

    2009-11-20 commodity VOO
        price: "USD:pricehist.beanprice.yahoo/VOO"

    1993-01-29 commodity VWO
        price: "USD:pricehist.beanprice.yahoo/VWO"

    2023-07-18 price USD 7.170600 CNY

    2024-01-01 open Assets:Stock:US:VOO
    2024-01-01 open Assets:Current:US
    2024-05-06 price VOO 474.72 USD
    2024-05-06 *
        Assets:Stock:US:VOO 100.00 VOO { 474.72 USD }
        Assets:Current:US

    2024-01-01 open Assets:Stock:US:VWO
    2024-04-02 price VWO 42.18 USD
    2024-04-02 *
        Assets:Stock:US:VWO 100.00 VWO { 42.18 USD }
        Assets:Current:US

    2024-01-01 open Assets:Stock:CN
    2024-01-01 open Assets:Current:CN
    2024-04-08 price HSETF 1.7360 CNY
    2024-04-08 *
        Assets:Stock:CN 100.00 HSETF { 1.7360 CNY }
        Assets:Current:CN

    @@@/config/investment_distribution.yaml
    currency: USD
    investments:
      - group: US
        ratio: 0.50
        xirr: 0.10
    """

    mock_request_yahoo_finance.return_value = {
        "quoteResponse": {
            "result": [
                quote_resp(
                    "VOO",
                    "PRE",
                    "USD",
                    (537.36, 1729281600),
                    (536.41, 1729503326),
                    (537.36, 1729295982),
                ),
                quote_resp(
                    "VWO",
                    "PRE",
                    "USD",
                    (47.83, 1729281600),
                    (47.80, 1729503326),
                    (47.83, 1729295982),
                ),
                quote_resp(
                    "510310.SS",
                    "POST",
                    "CNY",
                    (3.8590, 1729494001),
                ),
                quote_resp(
                    "CNY=X",
                    "REGULAR",
                    "CNY",
                    (7.1109, 1729501324),
                ),
            ],
            "error": None,
        }
    }

    investment_groups = [
        InvestmentHolding(
            name="CN",
            expected_ratio=0.5,
            inventory=_I("300000.00 HSETF {1 CNY}, 300000.00 HSETF { 2 CNY }"),
        ),
        InvestmentHolding(
            name="US",
            expected_ratio=0.5,
            inventory=_I(
                "100.00 VOO {400 USD}, 100.00 VOO {500 USD},100.00 VWO {500 USD}"
            ),
        ),
    ]

    build_realtime_price_cache(entries)

    report = create_portfolio_report(entries, investment_groups, "USD")
    portfolio_groups = report.groups
    assert len(portfolio_groups) == 2
    assert portfolio_groups[0].name == "CN"
    assert portfolio_groups[0].target_ratio == 0.5
    assert abs(portfolio_groups[0].realtime_ratio - 0.74396) < Decimal("0.01")
    assert portfolio_groups[0].realtime_market_value.currency == "USD"
    assert len(portfolio_groups[0].holdings) == 1


@patch("doujia.price.yahoo.request_yahoo_finance")
@freeze_time("2024-10-21")
def test_portofolio_cash(mock_request_yahoo_finance, entries: list[Directive]):  # type: ignore # 验证现金账户应该被统计到持仓中
    """
    @@@/main.bean
    1970-01-01 commodity USD
        price: "CNY:pricehist.beanprice.yahoo/CNY=X"

    2009-11-20 commodity VOO
        price: "USD:pricehist.beanprice.yahoo/VOO"

    1993-01-29 commodity VWO
        price: "USD:pricehist.beanprice.yahoo/VWO"

    2023-07-18 price USD 7.170600 CNY

    2024-01-01 open Equity:Opening-Balances
    2024-01-01 open Assets:Stock:US:VOO
    2024-01-01 open Assets:Current:US

    2024-01-01 *
        Assets:Current:US 10000 USD
        Equity:Opening-Balances

    2024-05-06 price VOO 474.72 USD
    2024-05-06 *
        Assets:Stock:US:VOO 100.00 VOO { 474.72 USD }
        Assets:Current:US

    2024-01-01 open Assets:Stock:US:VWO
    2024-04-02 price VWO 42.18 USD
    2024-04-02 *
        Assets:Stock:US:VWO 100.00 VWO { 42.18 USD }
        Assets:Current:US

    @@@/beangrow.pbtxt
    investments {
        investment {
            currency: "VOO"
            asset_account: "Assets:Stock:US:VOO"
            cash_accounts: "Assets:Current:US"
        }
        investment {
            currency: "VWO"
            asset_account: "Assets:Stock:US:VWO"
            cash_accounts: "Assets:Current:US"
        }
    }
    groups {
        group {
            name: "US"
            investment: "Assets:Stock:US:VOO"
            investment: "Assets:Stock:US:VWO"
            currency: "USD"
        }
        group {
            name: "Cash Equivalent"
            currency: "USD"
        }
    }

    @@@/config/investment_distribution.yaml
    currency: USD
    investments:
      - group: US
        ratio: 0.50
        xirr: 0.10
      - group: Cash Equivalent
        ratio: 0.5
        xirr: 0.1
    cash:
      account: [Assets:Current:US]
      group: Cash Equivalent
    """

    investment_groups = get_investment_holdings(
        entries,
        Path("./beangrow.pbtxt"),
        Path("./config/investment_distribution.yaml"),
        {"dcontext": None},
        date.today(),
    )

    assert len(investment_groups) == 2
    assert investment_groups[0].name == "US"
    assert investment_groups[1].name == "Cash Equivalent"
    assert len(investment_groups[1].inventory) == 1
    assert investment_groups[1].inventory.get_only_position().units.number == -41690.0
    assert investment_groups[1].inventory.get_only_position().units.currency == "USD"
