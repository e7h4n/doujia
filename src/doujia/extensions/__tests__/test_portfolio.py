from datetime import date
from decimal import Decimal
from pathlib import Path

import beangrow.returns as returnslib
import pytest
from beancount.core.data import Directive
from fava.application import create_app
from flask.app import Flask
from flask.testing import FlaskClient
from freezegun import freeze_time

from doujia.extensions.portfolio_logic import (
    extract_beangrow_config,
)
from doujia.report.investment import investments_performance


@pytest.fixture(scope="session")
def app(test_data_dir: Path) -> Flask:
    """Get the Fava Flask app."""
    fava_app = create_app(
        [test_data_dir / "portfolio.bean"],
        load=True,
    )
    fava_app.testing = True
    return fava_app


@pytest.fixture()
def test_client(app: Flask) -> FlaskClient:
    """Get the test client for the Fava Flask app."""
    return app.test_client()


@freeze_time("2022-01-01")
@pytest.mark.skip(reason="TODO: fix this test")
def test_load_extension_reports(test_client: FlaskClient):
    result = test_client.get("/example/extension/Portfolio/")
    assert result.status_code == 200


@pytest.mark.skip(reason="TODO: fix this test")
def test_investments_performance(entries: list[Directive]):  # type: ignore
    """
    @@@/main.bean
    2020-01-01 commodity AAPL
    2020-01-01 open Assets:Stock:Current

    2020-01-01 open Assets:Stock:AAPL

    2021-01-01 price AAPL      100 USD

    2021-01-01 * "Buy AAPL 100"
        Assets:Stock:AAPL      100 AAPL {100 USD}
        Assets:Stock:Current

    2021-12-31 price AAPL      150 USD

    @@@/config/beangrow.pbtxt
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

    begin_date, end_date = (date(2021, 1, 1), date(2022, 1, 1))
    pricer, groups, account_data_map = extract_beangrow_config(
        entries,
        Path("/beangrow.pbtxt"),
        end_date,
        dict(),
    )

    account_data = [
        account_data_map[name]
        for name in groups[0].investment
        if name in account_data_map
    ]
    cash_flows = returnslib.truncate_and_merge_cash_flows(
        pricer, account_data, begin_date, end_date
    )

    (profitable_investments, _) = investments_performance(cash_flows)
    assert len(profitable_investments) > 0
    assert profitable_investments[0].name == "Assets:Stock:AAPL"
    assert abs(profitable_investments[0].pnl - Decimal("5000")) < 0.01


@pytest.mark.skip(reason="TODO: fix this test")
def test_investments_performance_realized(entries: list[Directive]):  # type: ignore
    """
    @@@/main.bean
    2020-01-01 commodity AAPL
    2020-01-01 open Assets:Stock:Current
    2020-01-01 open Assets:Stock:AAPL
    2020-01-01 open Expenses:Fee
    2020-01-01 open Income:PnL
    2020-01-01 open Income:Dividends:AAPL

    2021-01-01 price AAPL      100 USD

    2021-01-01 * "Buy AAPL 100"
        Assets:Stock:AAPL      100 AAPL {100 USD}
        Assets:Stock:Current -10,000 USD
        Expenses:Fee 2 USD
        Assets:Stock:Current -2 USD

    2021-01-01 * "Sell AAPL 100"
        Assets:Stock:AAPL -50 AAPL {100 USD} @ 105 USD
        Assets:Stock:Current 5,250 USD
        Income:PnL -250 USD
        Expenses:Fee 2 USD
        Assets:Stock:Current -2 USD

    2021-06-01 * "Dividend AAPL"
        Income:Dividends:AAPL -250 USD
        Assets:Stock:Current 250 USD
        Expenses:Fee 25 USD
        Assets:Stock:Current -25 USD

    2021-12-31 price AAPL      150 USD

    @@@/config/beangrow.pbtxt
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

    begin_date, end_date = (date(2021, 1, 1), date(2022, 1, 1))
    pricer, groups, account_data_map = extract_beangrow_config(
        entries,
        Path("/beangrow.pbtxt"),
        end_date,
        dict(),
    )

    account_data = [
        account_data_map[name]
        for name in groups[0].investment
        if name in account_data_map
    ]
    cash_flows = returnslib.truncate_and_merge_cash_flows(
        pricer, account_data, begin_date, end_date
    )

    (profitable_investments, _) = investments_performance(cash_flows)
    assert len(profitable_investments) > 0
    assert profitable_investments[0].name == "Assets:Stock:AAPL"
    assert abs(profitable_investments[0].pnl - Decimal("2971")) < 0.01


@pytest.mark.skip(reason="TODO: fix this test")
def test_investments_performance_realized_with_income_prefix(entries: list[Directive]):  # type: ignore
    """
    @@@/main.bean
    2020-01-01 commodity AAPL
    2020-01-01 open Assets:Stock:Current
    2020-01-01 open Assets:Stock:AAPL
    2020-01-01 open Expenses:Fee
    2020-01-01 open Income:PnL
    2020-01-01 open Income:Dividends:AAPL

    2021-01-01 price AAPL      100 USD

    2021-01-01 * "Buy AAPL 100"
        Assets:Stock:AAPL      100 AAPL {100 USD}
        Assets:Stock:Current -10,000 USD
        Expenses:Fee 2 USD
        Assets:Stock:Current -2 USD

    2021-01-01 * "Sell AAPL 100"
        Assets:Stock:AAPL -50 AAPL {100 USD} @ 105 USD
        Assets:Stock:Current 5,250 USD
        Income:PnL -250 USD
        Expenses:Fee 2 USD
        Assets:Stock:Current -2 USD

    2021-06-01 * "Dividend AAPL"
        Income:Dividends:AAPL -250 USD
        Assets:Stock:Current 250 USD
        Expenses:Fee 25 USD
        Assets:Stock:Current -25 USD

    2021-12-31 price AAPL      150 USD

    @@@/config/beangrow.pbtxt
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

    begin_date, end_date = (date(2021, 1, 1), date(2022, 1, 1))
    pricer, groups, account_data_map = extract_beangrow_config(
        entries,
        Path("/beangrow.pbtxt"),
        end_date,
        dict(),
    )

    account_data = [
        account_data_map[name]
        for name in groups[0].investment
        if name in account_data_map
    ]
    cash_flows = returnslib.truncate_and_merge_cash_flows(
        pricer, account_data, begin_date, end_date
    )

    (profitable_investments, _) = investments_performance(cash_flows)

    assert len(profitable_investments) > 0
    assert profitable_investments[0].name == "Assets:Stock:AAPL"
    assert profitable_investments[0].currency == "USD"
    assert abs(profitable_investments[0].pnl - Decimal("2971")) < 0.01
