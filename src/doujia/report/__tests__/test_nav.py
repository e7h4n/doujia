from typing import TypeVar

from datetime import date
from decimal import Decimal
from pathlib import Path

from beancount.core import data
from doujia.extensions.portfolio_logic import extract_beangrow_config
from doujia.report.nav import gen_nav_index_data
import logzero

logzero.loglevel(logzero.DEBUG)

Directive = TypeVar("Directive", bound=data.Directive)  # type: ignore


def test_twr_history_simple(entries: list[Directive]):
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

    nav_index = gen_nav_index_data(
        list(account_data_map.values()),
        price_map=pricer.price_map,
        end_date=end_date,
        target_currency="USD",
        fill_gap_days=False,
    )

    assert len(nav_index) == 2
    assert nav_index[0][0] == date(2021, 2, 1)
    assert nav_index[0][1] == Decimal("1")
    assert nav_index[1][0] == date(2022, 1, 1)
    assert nav_index[1][1] == Decimal("1.5")


def test_twr_history_multiple_transactions(entries: list[Directive]):
    """
    @@@/main.bean
    2020-01-01 commodity AAPL
    2020-01-01 open Assets:Stock:Current
    2020-01-01 open Assets:Stock:AAPL

    2021-01-01 price AAPL      100 USD

    2021-02-01 * "Buy AAPL 100"
        Assets:Stock:AAPL      100 AAPL {100 USD}
        Assets:Stock:Current -10,000 USD

    2021-02-15 * "Buy AAPL 100"
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

    nav_index = gen_nav_index_data(
        list(account_data_map.values()),
        price_map=pricer.price_map,
        end_date=end_date,
        target_currency="USD",
        fill_gap_days=False,
    )
    assert len(nav_index) == 3
    assert nav_index[0][0] == date(2021, 2, 1)
    assert nav_index[0][1] == Decimal("1")
    assert nav_index[1][0] == date(2021, 2, 15)
    assert nav_index[1][1] == Decimal("1")
    assert nav_index[2][0] == date(2022, 1, 1)
    assert nav_index[2][1] == Decimal("1.5")


# 清仓再买入的情况
def test_twr_history_rebuild_inventory(entries: list[Directive]):
    """
    @@@/main.bean
    2020-01-01 commodity AAPL
    2020-01-01 open Assets:Stock:Current
    2020-01-01 open Assets:Stock:AAPL

    2021-01-01 price AAPL      100 USD

    2021-02-01 * "Buy AAPL 100"
        Assets:Stock:AAPL      100 AAPL {100 USD}
        Assets:Stock:Current -10,000 USD

    2021-02-10 * "Sell AAPL 100"
        Assets:Stock:AAPL -100 AAPL {100 USD}
        Assets:Stock:Current 10,000 USD

    2021-02-15 * "Buy AAPL 100"
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
    pricer, groups, account_data_map = extract_beangrow_config(
        entries,
        Path("/beangrow.pbtxt"),
        end_date,
        dict(),
    )

    nav_index = gen_nav_index_data(
        list(account_data_map.values()),
        price_map=pricer.price_map,
        end_date=end_date,
        target_currency="USD",
        fill_gap_days=False,
    )
    assert len(nav_index) == 4
    assert nav_index[0][0] == date(2021, 2, 1)
    assert nav_index[0][1] == Decimal("1")
    assert nav_index[1][0] == date(2021, 2, 10)
    assert nav_index[1][1] == Decimal("1")
    assert nav_index[2][0] == date(2021, 2, 15)
    assert nav_index[2][1] == Decimal("1")
    assert nav_index[3][0] == date(2022, 1, 1)
    assert nav_index[3][1] == Decimal("1.5")


# 空仓时有价格的情况
def test_twr_history_sell_with_price(entries: list[Directive]):
    """
    @@@/main.bean
    2020-01-01 commodity AAPL
    2020-01-01 open Assets:Stock:Current
    2020-01-01 open Assets:Stock:AAPL

    2021-01-01 price AAPL      100 USD

    2021-02-01 * "Buy AAPL 100"
        Assets:Stock:AAPL      100 AAPL {100 USD}
        Assets:Stock:Current -10,000 USD

    2021-02-11 * "Sell AAPL 100"
        Assets:Stock:AAPL -100 AAPL {100 USD} @ 105 USD
        Assets:Stock:Current 10,500 USD

    2021-02-15 * "Buy AAPL 100"
        Assets:Stock:AAPL      100 AAPL {107 USD}
        Assets:Stock:Current -10,700 USD

    2021-03-01 price AAPL 100 USD

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
    pricer, groups, account_data_map = extract_beangrow_config(
        entries,
        Path("/beangrow.pbtxt"),
        end_date,
        dict(),
    )

    nav_index = gen_nav_index_data(
        list(account_data_map.values()),
        price_map=pricer.price_map,
        end_date=end_date,
        target_currency="USD",
        fill_gap_days=False,
    )
    assert len(nav_index) == 4
    assert nav_index[0][0] == date(2021, 2, 1)
    assert nav_index[0][1] == Decimal("1")
    assert nav_index[1][0] == date(2021, 2, 11)
    assert nav_index[1][1] == Decimal("1.05")
    assert nav_index[2][0] == date(2021, 2, 15)
    assert nav_index[2][1] == Decimal("1.05")
    assert abs(nav_index[3][1] - Decimal("0.98")) < 0.01


# 卖出价格超过前一日收盘价的情况
def test_twr_history_higher_than_last_close(entries: list[Directive]):
    """
    @@@/main.bean
    2020-01-01 commodity AAPL
    2020-01-01 open Assets:Stock:Current
    2020-01-01 open Assets:Stock:AAPL
    2020-01-01 open Income:PnL

    2021-02-01 * "Buy AAPL 100"
        Assets:Stock:AAPL      100 AAPL {100 USD}
        Assets:Stock:Current -10,000 USD

    2021-02-11 * "Sell AAPL 100"
        Assets:Stock:AAPL -100 AAPL {100 USD} @ 106 USD
        Income:PnL -600 USD
        Assets:Stock:Current 10,600 USD

    2021-02-11 price AAPL      106 USD
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
    pricer, groups, account_data_map = extract_beangrow_config(
        entries,
        Path("/beangrow.pbtxt"),
        end_date,
        dict(),
    )

    nav_index = gen_nav_index_data(
        list(account_data_map.values()),
        price_map=pricer.price_map,
        end_date=end_date,
        target_currency="USD",
        fill_gap_days=False,
    )
    assert len(nav_index) == 3
    assert nav_index[0][0] == date(2021, 2, 1)
    assert nav_index[0][1] == Decimal("1")
    assert nav_index[1][0] == date(2021, 2, 11)
    assert nav_index[1][1] == Decimal("1.06")
    assert nav_index[2][0] == date(2022, 1, 1)
    assert nav_index[2][1] == Decimal("1.06")


# 卖出价格超过前一日收盘价的情况
def test_twr_history_with_fees(entries: list[Directive]):
    """
    @@@/main.bean
    2020-01-01 commodity AAPL
    2020-01-01 open Assets:Stock:Current
    2020-01-01 open Assets:Stock:AAPL
    2020-01-01 open Expenses:Fees
    2020-01-01 open Income:PnL

    2021-02-01 * "Buy AAPL 100"
        Assets:Stock:AAPL      100 AAPL {100 USD}
        Assets:Stock:Current -10,000 USD
        Expenses:Fees 10 USD
        Assets:Stock:Current -10 USD

    2021-02-11 * "Sell AAPL 100"
        Assets:Stock:AAPL -100 AAPL {100 USD} @ 106 USD
        Income:PnL -600 USD
        Assets:Stock:Current 10,600 USD
        Expenses:Fees 10 USD
        Assets:Stock:Current -10 USD

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

    nav_index = gen_nav_index_data(
        list(account_data_map.values()),
        price_map=pricer.price_map,
        end_date=end_date,
        target_currency="USD",
        fill_gap_days=False,
    )
    assert len(nav_index) == 3
    assert nav_index[0][0] == date(2021, 2, 1)
    assert abs(nav_index[0][1] - Decimal("1")) < 0.01
    assert nav_index[1][0] == date(2021, 2, 11)
    assert abs(nav_index[1][1] - Decimal("1.057")) < 0.01
    assert nav_index[2][0] == date(2022, 1, 1)
    assert abs(nav_index[2][1] - Decimal("1.057")) < 0.01


# 除息
def test_twr_history_with_dividend(entries: list[Directive]):
    """
    @@@/main.bean
    2020-01-01 commodity AAPL
    2020-01-01 open Assets:Stock:Current
    2020-01-01 open Assets:Stock:AAPL
    2020-01-01 open Expenses:Fees
    2020-01-01 open Income:Dividends:AAPL

    2021-02-01 * "Buy AAPL 100"
        Assets:Stock:AAPL      100 AAPL {100 USD}
        Assets:Stock:Current -10,000 USD
        Expenses:Fees 10 USD
        Assets:Stock:Current -10 USD

    2021-02-15 * "Dividend AAPL"
        Income:Dividends:AAPL -100 USD
        Assets:Stock:Current 100 USD

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

    nav_index = gen_nav_index_data(
        list(account_data_map.values()),
        price_map=pricer.price_map,
        end_date=end_date,
        target_currency="USD",
        fill_gap_days=False,
    )
    assert len(nav_index) == 3
    assert nav_index[0][0] == date(2021, 2, 1)
    assert abs(nav_index[0][1] - Decimal("1")) < 0.01
    assert nav_index[1][0] == date(2021, 2, 15)
    assert abs(nav_index[1][1] - Decimal("1.0099")) < 0.01
    assert nav_index[2][0] == date(2022, 1, 1)
    assert abs(nav_index[2][1] - Decimal("1.0099")) < 0.01


# 有手续费的除息
def test_twr_history_with_dividend_and_fees(entries: list[Directive]):
    """
    @@@/main.bean
    2020-01-01 commodity AAPL
    2020-01-01 open Assets:Stock:Current
    2020-01-01 open Assets:Stock:AAPL
    2020-01-01 open Expenses:Fees
    2020-01-01 open Income:Dividends:AAPL

    2021-02-01 * "Buy AAPL 100"
        Assets:Stock:AAPL      100 AAPL {100 USD}
        Assets:Stock:Current -10,000 USD
        Expenses:Fees 10 USD
        Assets:Stock:Current -10 USD

    2021-02-15 * "Dividend AAPL"
        Income:Dividends:AAPL -100 USD
        Assets:Stock:Current 100 USD
        Expenses:Fees 50 USD
        Assets:Stock:Current -50 USD

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

    nav_index = gen_nav_index_data(
        list(account_data_map.values()),
        price_map=pricer.price_map,
        end_date=end_date,
        target_currency="USD",
        fill_gap_days=False,
    )
    assert len(nav_index) == 3
    assert nav_index[0][0] == date(2021, 2, 1)
    assert abs(nav_index[0][1] - Decimal("1")) < 0.01
    assert nav_index[1][0] == date(2021, 2, 15)
    assert abs(nav_index[1][1] - Decimal("1.00499")) < 0.0001
    assert nav_index[2][0] == date(2022, 1, 1)
    assert abs(nav_index[2][1] - Decimal("1.00499")) < 0.0001


# 对没有交易的日期进行填充
def test_twr_history_with_gap_days(entries: list[Directive]):
    """
    @@@/main.bean
    2020-01-01 commodity AAPL
    2020-01-01 open Assets:Stock:Current
    2020-01-01 open Assets:Stock:AAPL

    2021-01-01 price AAPL      100 USD

    2021-02-01 * "Buy AAPL 100"
        Assets:Stock:AAPL      100 AAPL {100 USD}
        Assets:Stock:Current -10,000 USD

    2021-02-02 price AAPL      101 USD

    2021-02-03 price AAPL      102 USD

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

    _, end_date = (date(2021, 1, 1), date(2021, 2, 3))
    pricer, _, account_data_map = extract_beangrow_config(
        entries,
        Path("/beangrow.pbtxt"),
        end_date,
        dict(),
    )

    nav_index = gen_nav_index_data(
        list(account_data_map.values()),
        price_map=pricer.price_map,
        end_date=end_date,
        target_currency="USD",
        fill_gap_days=True,
    )

    assert len(nav_index) == 3
    assert nav_index[0][0] == date(2021, 2, 1)
    assert nav_index[0][1] == Decimal("1")
    assert nav_index[1][0] == date(2021, 2, 2)
    assert nav_index[1][1] == Decimal("1.01")
    assert nav_index[2][0] == date(2021, 2, 3)
    assert nav_index[2][1] == Decimal("1.02")


# 对没有交易的日期进行填充
def test_twr_history_with_no_transactions(entries: list[Directive]):
    """
    @@@/main.bean
    2020-01-01 commodity AAPL
    2020-01-01 open Assets:Stock:Current
    2020-01-01 open Assets:Stock:AAPL

    2021-01-01 price AAPL      100 USD

    2021-02-01 * "Buy AAPL 100"
        Assets:Stock:AAPL      100 AAPL {100 USD}
        Assets:Stock:Current -10,000 USD

    2021-02-03 price AAPL      102 USD

    @@@/beangrow.pbtxt
    investments {
        investment {
            currency: "AAPL"
            asset_account: "Assets:Stock:AAPL"
            cash_accounts: "Assets:Stock:Current"
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

    begin_date, end_date = (date(2021, 2, 2), date(2021, 2, 3))
    pricer, _, account_data_map = extract_beangrow_config(
        entries,
        Path("/beangrow.pbtxt"),
        end_date,
        dict(),
    )

    nav_index = gen_nav_index_data(
        list(account_data_map.values()),
        price_map=pricer.price_map,
        begin_date=begin_date,
        end_date=end_date,
        target_currency="USD",
        fill_gap_days=True,
    )

    assert len(nav_index) == 2
    assert nav_index[0][0] == date(2021, 2, 2)
    assert abs(nav_index[0][1] - Decimal("1")) < 0.01
    assert nav_index[1][0] == date(2021, 2, 3)
    assert abs(nav_index[1][1] - Decimal("1.02")) < 0.01


# 起始日期有交易的情况
def test_twr_history_with_begin_date_has_transactions(entries: list[Directive]):
    """
    @@@/main.bean
    2020-01-01 commodity AAPL
    2020-01-01 open Assets:Stock:Current
    2020-01-01 open Assets:Stock:AAPL

    2021-01-01 price AAPL      100 USD

    2021-02-01 * "Buy AAPL 100"
        Assets:Stock:AAPL      100 AAPL {100 USD}
        Assets:Stock:Current -10,000 USD

    2021-02-02 * "Buy AAPL 100"
        Assets:Stock:AAPL      100 AAPL {101 USD}
        Assets:Stock:Current -10,100 USD

    2021-02-03 price AAPL      102 USD

    @@@/beangrow.pbtxt
    investments {
        investment {
            currency: "AAPL"
            asset_account: "Assets:Stock:AAPL"
            cash_accounts: "Assets:Stock:Current"
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

    begin_date, end_date = (date(2021, 2, 2), date(2021, 2, 3))
    pricer, _, account_data_map = extract_beangrow_config(
        entries,
        Path("/beangrow.pbtxt"),
        end_date,
        dict(),
    )

    nav_index = gen_nav_index_data(
        list(account_data_map.values()),
        price_map=pricer.price_map,
        begin_date=begin_date,
        end_date=end_date,
        target_currency="USD",
        fill_gap_days=True,
    )

    assert len(nav_index) == 2
    assert nav_index[0][0] == date(2021, 2, 2)
    assert abs(nav_index[0][1] - Decimal("1")) < 0.001
    assert nav_index[1][0] == date(2021, 2, 3)
    assert abs(nav_index[1][1] - Decimal("1.02")) < 0.01


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

    nav_index = gen_nav_index_data(
        list(account_data_map.values()),
        price_map=pricer.price_map,
        begin_date=begin_date,
        end_date=end_date,
        target_currency="USD",
        fill_gap_days=True,
    )

    assert len(nav_index) == 3
    assert nav_index[0][0] == date(2021, 2, 1)
    assert nav_index[0][1] == Decimal("1")
    assert nav_index[1][0] == date(2021, 2, 2)
    assert nav_index[1][1] == Decimal("2")
    assert nav_index[2][0] == date(2021, 2, 3)
    assert nav_index[2][1] == Decimal("2")


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

    nav_index = gen_nav_index_data(
        list(account_data_map.values()),
        price_map=pricer.price_map,
        begin_date=begin_date,
        end_date=end_date,
        target_currency="USD",
        fill_gap_days=True,
    )

    assert len(nav_index) == 3
    assert nav_index[0][0] == date(2021, 2, 1)
    assert nav_index[0][1] == Decimal("1")
    assert nav_index[1][0] == date(2021, 2, 2)
    assert nav_index[1][1] == Decimal("2")
    assert nav_index[2][0] == date(2021, 2, 3)
    assert nav_index[2][1] == Decimal("2")
