import datetime
import json

from fava.ext import FavaExtensionBase
from flask import current_app

from doujia.report.investment import (
    get_investment_holdings,
)
from doujia.report.portfolio.portfolio import create_portfolio_report


class Holdings(FavaExtensionBase):
    report_title = "Holdings"

    has_js_module = True

    def report(self):
        entries = self.ledger.all_entries

        investment_groups = get_investment_holdings(
            entries,
            current_app.beangrow_config,
            current_app.investment_config,
            self.ledger.options,
            datetime.date.today() + datetime.timedelta(days=1),
        )

        return create_portfolio_report(entries, investment_groups, "USD")

    def fake(self):
        json_path = self.ledger.join_path("web/src/mocks/realtime_report.json")
        # load json to Portfolio
        with open(json_path, "r") as f:
            return json.load(f)

    def abs(self, value):
        return abs(value)
