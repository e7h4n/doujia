import re
from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from fava.application import create_app
from flask.app import Flask
from flask.testing import FlaskClient
from freezegun import freeze_time


@pytest.fixture(scope="session")
def app(test_data_dir: Path) -> Flask:
    """Get the Fava Flask app."""
    fava_app = create_app(
        [test_data_dir / "dashboard.bean"],
        load=True,
    )
    fava_app.testing = True
    return fava_app


@pytest.fixture()
def test_client(app: Flask) -> FlaskClient:
    """Get the test client for the Fava Flask app."""
    return app.test_client()


@freeze_time("2022-01-01")
def test_load_dashboard_render_html(test_client: FlaskClient):
    result = test_client.get("/example/extension/Dashboard/")
    assert result.status_code == 200

    soup = BeautifulSoup(result.data, "html.parser")
    found = soup.find(string=re.compile("Net Worth"))
    assert found
