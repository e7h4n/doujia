import datetime

from fava.ext import FavaExtensionBase
from fava.helpers import FavaAPIError
from fava.util.date import parse_date
from fava.ext import extension_endpoint
from flask import jsonify, request

from doujia.extensions.portfolio_logic import (
    overview_report,
    extract_beangrow_config_from_fava,
)
from doujia.report.investment import (
    calendar_returns,
    cumulative_returns,
    investments_performance,
    irr_summary,
)
from doujia.report.nav import gen_nav_index_data
from doujia.report.pnl import gen_pnl_data
import beangrow.returns as returnslib


class Portfolio(FavaExtensionBase):
    report_title = "Portfolio"
    has_js_module = True

    def _get_date_range(self):
        begin, end = parse_date(
            request.args.get("time", "2021-07-26 - day"),
            self.ledger.fava_options.fiscal_year_end,
        )

        end = end - datetime.timedelta(days=1)
        if begin is None:
            begin = datetime.date(2017, 1, 1)
        if end is None:
            end = datetime.date.today()

        return begin, end

    def _get_group_and_config(self, group_name=None):
        begin_date, end_date = self._get_date_range()
        pricer, groups, account_data_map = extract_beangrow_config_from_fava(
            self.ledger, end_date
        )

        if group_name is None:
            group_name = request.args.get("group", groups[0].name)

        for group in groups:
            if group.name == group_name:
                break
        else:
            raise FavaAPIError("Group not found")

        adlist = [
            account_data_map[name]
            for name in group.investment
            if name in account_data_map
        ]

        return begin_date, end_date, pricer, group, adlist

    def overview(self) -> list[dict[str, float]]:
        begin_date, end_date = self._get_date_range()
        pricer, groups, account_data_map = extract_beangrow_config_from_fava(
            self.ledger,
            end_date,
        )

        return overview_report(pricer, groups, account_data_map, begin_date, end_date)

    @extension_endpoint
    def irr_summary(self):
        begin_date, end_date, pricer, group, adlist = self._get_group_and_config()

        return jsonify(
            irr_summary(
                pricer=pricer,
                adlist=adlist,
                start_date=begin_date,
                end_date=end_date,
                target_currency=group.currency,
            )
        )

    @extension_endpoint
    def pnl(self):
        begin_date, end_date, pricer, group, adlist = self._get_group_and_config()

        pnl = gen_pnl_data(
            account_datas=adlist,
            price_map=pricer.price_map,
            begin_date=begin_date,
            end_date=end_date,
            target_currency=group.currency,
        )

        return jsonify(pnl)

    @extension_endpoint
    def nav_index(self):
        begin_date, end_date, pricer, group, adlist = self._get_group_and_config()

        nav_index = gen_nav_index_data(
            account_datas=adlist,
            price_map=pricer.price_map,
            begin_date=begin_date,
            end_date=end_date,
            target_currency=group.currency,
        )

        return jsonify(nav_index)

    @extension_endpoint
    def cash_flows(self):
        begin_date, end_date, pricer, _, adlist = self._get_group_and_config()

        cash_flows = returnslib.truncate_and_merge_cash_flows(
            pricer, adlist, begin_date, end_date
        )

        return jsonify(cash_flows)

    @extension_endpoint
    def investments(self):
        begin_date, end_date, pricer, _, adlist = self._get_group_and_config()

        cash_flows = returnslib.truncate_and_merge_cash_flows(
            pricer, adlist, begin_date, end_date
        )

        (profitable_investments, unprofitable_investments) = investments_performance(
            cash_flows
        )

        return jsonify(
            {
                "profitable": profitable_investments,
                "unprofitable": unprofitable_investments,
            }
        )

    @extension_endpoint
    def calendar_returns(self):
        begin_date, end_date, pricer, group, adlist = self._get_group_and_config()
        return jsonify(
            calendar_returns(pricer, adlist, begin_date, end_date, group.currency)
        )

    @extension_endpoint
    def cumulative_returns(self):
        begin_date, end_date, pricer, group, adlist = self._get_group_and_config()
        return jsonify(
            cumulative_returns(pricer, adlist, begin_date, end_date, group.currency)
        )
