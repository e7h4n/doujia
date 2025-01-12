from typing import TypeVar

from datetime import date
from decimal import Decimal
from pathlib import Path

from beancount.core import data
from doujia.extensions.portfolio_logic import extract_beangrow_config
from doujia.report.pnl import gen_pnl_data

Directive = TypeVar("Directive", bound=data.Directive)  # type: ignore


def test_pnl_unrealized_pnl(entries: list[Directive]):
    """
    @@@/main.bean
    2020-01-01 commodity AAPL
    2020-01-01 open Assets:Stock:Current
    2020-01-01 open Assets:Stock:AAPL

    2021-01-01 price AAPL      100 USD

    2021-02-01 * "Buy AAPL 100"
        Assets:Stock:AAPL      100 AAPL {100 USD}
        Assets:Stock:Current -10,000 USD

    2021-03-01 price AAPL      150 USD

    @@@/beangrow.pbtxt
    investments {
        investment {
            currency: "AAPL"
            asset_account: "Assets:Stock:AAPL"
            cash_accounts: "Assets:Stock:Current"
            dividend_accounts: "Income:Dividends:AAPL"
        }
    }
    groups {
        group {
            name: "All"
            investment: "Assets:*"
            currency: "USD"
        }
    }
    """

    _, end_date = (date(2021, 1, 1), date(2022, 1, 1))
    pricer, _, account_data_map = extract_beangrow_config(
        entries,
        Path("/beangrow.pbtxt"),
        end_date,
        dict(),
    )

    pnl = gen_pnl_data(
        list(account_data_map.values()),
        price_map=pricer.price_map,
        end_date=end_date,
        target_currency="USD",
    )

    assert pnl.unrealized_pnl == Decimal("5000")
    assert pnl.currency == "USD"


def test_pnl_realized_pnl(entries: list[Directive]):
    """
    @@@/main.bean
    2020-01-01 commodity AAPL
    2020-01-01 open Assets:Stock:Current
    2020-01-01 open Assets:Stock:AAPL
    2020-01-01 open Income:PnL

    2021-01-01 price AAPL      100 USD

    2021-02-01 * "Buy AAPL 100"
        Assets:Stock:AAPL      100 AAPL {100 USD}
        Assets:Stock:Current -10,000 USD

    2021-02-03 * "Sell AAPL 100"
        Assets:Stock:AAPL     -50 AAPL {} @ 110 USD
        Income:PnL            -500 USD
        Assets:Stock:Current  5,500 USD

    2021-03-01 price AAPL      150 USD

    @@@/beangrow.pbtxt
    investments {
        investment {
            currency: "AAPL"
            asset_account: "Assets:Stock:AAPL"
            cash_accounts: "Assets:Stock:Current"
            dividend_accounts: "Income:Dividends:AAPL"
        }
    }
    groups {
        group {
            name: "All"
            investment: "Assets:*"
            currency: "USD"
        }
    }
    """

    _, end_date = (date(2021, 1, 1), date(2022, 1, 1))
    pricer, _, account_data_map = extract_beangrow_config(
        entries,
        Path("/beangrow.pbtxt"),
        end_date,
        dict(),
    )

    pnl = gen_pnl_data(
        list(account_data_map.values()),
        price_map=pricer.price_map,
        end_date=end_date,
        target_currency="USD",
    )

    assert pnl.unrealized_pnl == Decimal("2500")
    assert pnl.currency == "USD"
    assert pnl.realized_pnl_ex_fee == Decimal("500")


def test_pnl_with_fee(entries: list[Directive]):
    """
    @@@/main.bean
    2020-01-01 commodity AAPL
    2020-01-01 open Assets:Stock:Current
    2020-01-01 open Assets:Stock:AAPL
    2020-01-01 open Income:PnL
    2020-01-01 open Expenses:Fees

    2021-01-01 price AAPL      100 USD

    2021-02-01 * "Buy AAPL 100"
        Assets:Stock:AAPL      100 AAPL {100 USD}
        Assets:Stock:Current -10,000 USD
        Expenses:Fees           2.00 USD
        Assets:Stock:Current  -2.00 USD


    2021-02-03 * "Sell AAPL 100"
        Assets:Stock:AAPL     -50 AAPL {} @ 110 USD
        Income:PnL            -500 USD
        Assets:Stock:Current  5,500 USD
        Expenses:Fees           2.00 USD
        Assets:Stock:Current  -2.00 USD


    2021-03-01 price AAPL      150 USD

    @@@/beangrow.pbtxt
    investments {
        investment {
            currency: "AAPL"
            asset_account: "Assets:Stock:AAPL"
            cash_accounts: "Assets:Stock:Current"
            dividend_accounts: "Income:Dividends:AAPL"
        }
    }
    groups {
        group {
            name: "All"
            investment: "Assets:*"
            currency: "USD"
        }
    }
    """

    _, end_date = (date(2021, 1, 1), date(2022, 1, 1))
    pricer, _, account_data_map = extract_beangrow_config(
        entries,
        Path("/beangrow.pbtxt"),
        end_date,
        dict(),
    )

    pnl = gen_pnl_data(
        list(account_data_map.values()),
        price_map=pricer.price_map,
        end_date=end_date,
        target_currency="USD",
    )

    assert pnl.unrealized_pnl == Decimal("2500")
    assert pnl.currency == "USD"
    assert pnl.realized_pnl_ex_fee == Decimal("496")
    assert pnl.fee == Decimal("4")


def test_pnl_with_dividends(entries: list[Directive]):
    """
    @@@/main.bean
    2020-01-01 commodity AAPL
    2020-01-01 open Assets:Stock:Current
    2020-01-01 open Assets:Stock:AAPL
    2020-01-01 open Income:PnL
    2020-01-01 open Expenses:Fees
    2020-01-01 open Income:Dividends:AAPL

    2021-01-01 price AAPL      100 USD

    2021-02-01 * "Buy AAPL 100"
        Assets:Stock:AAPL      100 AAPL {100 USD}
        Assets:Stock:Current -10,000 USD
        Expenses:Fees           2.00 USD
        Assets:Stock:Current  -2.00 USD


    2021-02-03 * "Sell AAPL 100"
        Assets:Stock:AAPL     -50 AAPL {} @ 110 USD
        Income:PnL            -500 USD
        Assets:Stock:Current  5,500 USD
        Expenses:Fees           2.00 USD
        Assets:Stock:Current  -2.00 USD

    2021-02-04 * "Dividend AAPL 100"
        Income:Dividends:AAPL  -100.00 USD
        Assets:Stock:Current  100.00 USD
        Expenses:Fees          10.00 USD
        Assets:Stock:Current  -10.00 USD

    2021-02-05 * "Dividend AAPL 10"
        Income:Dividends:AAPL  -10.00 USD
        Assets:Stock:Current  10.00 USD


    2021-03-01 price AAPL      150 USD

    @@@/beangrow.pbtxt
    investments {
        investment {
            currency: "AAPL"
            asset_account: "Assets:Stock:AAPL"
            cash_accounts: "Assets:Stock:Current"
            dividend_accounts: "Income:Dividends:AAPL"
        }
    }
    groups {
        group {
            name: "All"
            investment: "Assets:*"
            currency: "USD"
        }
    }
    """

    _, end_date = (date(2021, 1, 1), date(2022, 1, 1))
    pricer, _, account_data_map = extract_beangrow_config(
        entries,
        Path("/beangrow.pbtxt"),
        end_date,
        dict(),
    )

    pnl = gen_pnl_data(
        list(account_data_map.values()),
        price_map=pricer.price_map,
        end_date=end_date,
        target_currency="USD",
    )

    assert pnl.unrealized_pnl == Decimal("2500")
    assert pnl.currency == "USD"
    assert pnl.fee == Decimal("4")
    assert pnl.dividend_ex_tax == Decimal("100")
    assert pnl.dividend_tax == Decimal("10")
    assert pnl.realized_pnl_ex_fee == Decimal("496")


def test_pnl_with_no_transactions(entries: list[Directive]):
    """
    @@@/main.bean
    2020-01-01 commodity AAPL
    2020-01-01 open Assets:Stock:Current
    2020-01-01 open Assets:Stock:AAPL
    2020-01-01 open Income:PnL
    2020-01-01 open Expenses:Fees
    2020-01-01 open Income:Dividends:AAPL

    2021-01-01 price AAPL      100 USD

    2021-02-01 * "Buy AAPL 100"
        Assets:Stock:AAPL      100 AAPL {100 USD}
        Assets:Stock:Current -10,000 USD
        Expenses:Fees           2.00 USD
        Assets:Stock:Current  -2.00 USD

    2021-03-01 price AAPL      150 USD

    @@@/beangrow.pbtxt
    investments {
        investment {
            currency: "AAPL"
            asset_account: "Assets:Stock:AAPL"
            cash_accounts: "Assets:Stock:Current"
            dividend_accounts: "Income:Dividends:AAPL"
        }
    }
    groups {
        group {
            name: "All"
            investment: "Assets:*"
            currency: "USD"
        }
    }
    """

    begin_date, end_date = (date(2021, 2, 28), date(2021, 3, 1))
    pricer, _, account_data_map = extract_beangrow_config(
        entries,
        Path("/beangrow.pbtxt"),
        end_date,
        dict(),
    )

    pnl = gen_pnl_data(
        list(account_data_map.values()),
        price_map=pricer.price_map,
        begin_date=begin_date,
        end_date=end_date,
        target_currency="USD",
    )

    assert pnl.unrealized_pnl == Decimal("5000")
    assert pnl.currency == "USD"
    assert pnl.fee == Decimal("0")
    assert pnl.dividend_ex_tax == Decimal("0")
    assert pnl.dividend_tax == Decimal("0")
    assert pnl.realized_pnl_ex_fee == Decimal("0")


def test_pnl_510310(entries: list[Directive]):
    """
    @@@/main.bean
    2020-01-01 commodity SS510310
    2020-01-01 open Assets:Stock:Current
    2020-01-01 open Assets:Short:Stock:CN:SS510310
    2020-01-01 open Income:Passive:PnL
    2020-01-01 open Income:Passive:Dividends:SS510310

    2024-04-08 *
        Assets:Short:Stock:CN:SS510310                                                10,600.00 SS510310 { 1.7360 CNY }
        Assets:Short:Stock:CN:Current

    2024-09-23 *
        Assets:Short:Stock:CN:SS510310                                               -10,600.00 SS510310 {1.7360 CNY, 2024-04-08}
        Assets:Short:Stock:CN:SS510310                                                20,000.00 SS510310 { 3.552105964 CNY }
        Income:Passive:Dividends:SS510310

    2024-09-30 * "招商证券" "清仓沪深 300"
        Assets:Short:Stock:CN:SS510310                                               -20,000.00 SS510310 {} @ 3.8960 CNY
        Assets:Short:Stock:CN:Current                                                 77,920.00 CNY
        Income:Passive:PnL

    @@@/beangrow.pbtxt
    investments {
        investment {
            currency: "SS510310"
            asset_account: "Assets:Short:Stock:CN:SS510310"
            cash_accounts: "Assets:Short:Stock:CN:Current"
            dividend_accounts: "Income:Passive:Dividends:SS510310"
        }
    }
    groups {
        group {
            name: "All"
            investment: "Assets:*"
            currency: "CNY"
        }
    }
    """

    begin_date, end_date = (date(2024, 1, 1), date(2024, 12, 31))
    pricer, _, account_data_map = extract_beangrow_config(
        entries,
        Path("/beangrow.pbtxt"),
        end_date,
        dict(),
    )

    pnl = gen_pnl_data(
        list(account_data_map.values()),
        price_map=pricer.price_map,
        begin_date=begin_date,
        end_date=end_date,
        target_currency="CNY",
    )

    assert pnl.unrealized_pnl == Decimal("0")


# 存款到期
def test_twr_saving(entries: list[Directive]):
    """
    @@@/main.bean
    2021-02-01 open Assets:Current
    2021-02-01 open Assets:Saving
    2021-02-01 open Income:Dividends

    2021-02-01 *
        Assets:Current -10.00 USD
        Assets:Saving 10.00 USD

    2021-02-02 *
        Income:Dividends -10.00 USD
        Assets:Saving -10.00 USD
        Assets:Current 20.00 USD

    @@@/beangrow.pbtxt
    investments {
        investment {
            asset_account: "Assets:Saving"
            cash_accounts: "Assets:Current"
            dividend_accounts: "Income:Dividends"
        }
    }
    groups {
        group {
            name: "All"
            investment: "Assets:Saving"
            currency: "USD"
        }
    }
    """

    begin_date, end_date = (date(2021, 2, 1), date(2021, 2, 3))
    pricer, _, account_data_map = extract_beangrow_config(
        entries,
        Path("/beangrow.pbtxt"),
        end_date,
        dict(),
    )

    pnl_data = gen_pnl_data(
        list(account_data_map.values()),
        price_map=pricer.price_map,
        begin_date=begin_date,
        end_date=end_date,
        target_currency="USD",
    )

    assert pnl_data.unrealized_pnl == Decimal("0")
    assert pnl_data.currency == "USD"
    assert pnl_data.fee == Decimal("0")
    assert pnl_data.dividend_ex_tax == Decimal("10")


# 存款到期
def test_twr_saving_2(entries: list[Directive]):
    """
    @@@/main.bean
    2021-02-01 open Assets:Current
    2021-02-01 open Assets:Saving
    2021-02-01 open Income:Dividends

    2021-02-01 *
        Assets:Current -10.00 USD
        Assets:Saving 10.00 USD

    2021-02-02 *
        Income:Dividends -10.00 USD
        Assets:Current 10.00 USD

    2021-02-02 *
        Assets:Saving -10.00 USD
        Assets:Current 10.00 USD

    @@@/beangrow.pbtxt
    investments {
        investment {
            asset_account: "Assets:Saving"
            cash_accounts: "Assets:Current"
            dividend_accounts: "Income:Dividends"
        }
    }
    groups {
        group {
            name: "All"
            investment: "Assets:Saving"
            currency: "USD"
        }
    }
    """

    begin_date, end_date = (date(2021, 2, 1), date(2021, 2, 3))
    pricer, _, account_data_map = extract_beangrow_config(
        entries,
        Path("/beangrow.pbtxt"),
        end_date,
        dict(),
    )

    pnl_data = gen_pnl_data(
        list(account_data_map.values()),
        price_map=pricer.price_map,
        begin_date=begin_date,
        end_date=end_date,
        target_currency="USD",
    )

    assert pnl_data.unrealized_pnl == Decimal("0")
    assert pnl_data.currency == "USD"
    assert pnl_data.fee == Decimal("0")
    assert pnl_data.dividend_ex_tax == Decimal("10")
