import datetime
import os
from typing import Any, Dict, Tuple, TypeVar

import beangrow.config as configlib
import beangrow.returns as returnslib
from beancount.core import data, getters
from beangrow import investments
from flask import Blueprint, abort, jsonify, request

from doujia.price.price_map import get_last_and_realtime_price_map
from doujia.report.investment import (
    calendar_returns,
    cumulative_returns,
    get_investment_holdings,
    investments_performance,
    irr_summary,
)
from doujia.report.nav import gen_nav_index_data
from doujia.report.pnl import gen_pnl_data
from doujia.report.portfolio.portfolio import create_portfolio_report
from doujia.server.app import current_app
from doujia.server.filter.auth import require_auth

Directive = TypeVar("Directive", bound=data.Directive)  # type: ignore

bp = Blueprint("portfolio", __name__, url_prefix="/portfolio")


def _extract_beangrow_config(
    entries: list[Directive],
    end_date: datetime.date,
    dcontext: Any,
) -> Tuple[returnslib.Pricer, Dict, Dict[investments.Account, investments.AccountData]]:
    accounts = getters.get_accounts(entries)

    _, price_map = get_last_and_realtime_price_map(entries)
    pricer = returnslib.Pricer(price_map)

    config_path = current_app.doujia_config.beangrow_config
    beangrow_config = configlib.read_config(config_path, [], accounts)

    account_data_map = investments.extract(
        entries,
        dcontext,
        beangrow_config,
        end_date,
        False,
        "",
    )

    return pricer, beangrow_config.groups.group, account_data_map


def _extract_beangrow_config_from_fava(
    end_date: datetime.date,
) -> Tuple[returnslib.Pricer, Dict, Dict[investments.Account, investments.AccountData]]:
    dcontext = current_app.options_map["dcontext"]
    return _extract_beangrow_config(current_app.entries, end_date, dcontext)


def _get_group_and_config(group_name=None):
    begin_date, end_date = [datetime.date(2021, 7, 26), datetime.date.today()]
    pricer, groups, account_data_map = _extract_beangrow_config_from_fava(end_date)

    if group_name is None:
        group_name = request.args.get("group", groups[0].name)

    for group in groups:
        if group.name == group_name:
            break
    else:
        abort(404, description="Group not found")

    adlist = [
        account_data_map[name] for name in group.investment if name in account_data_map
    ]

    return begin_date, end_date, pricer, group, adlist


@bp.get("/irr_summary")
@require_auth
def get_irr_summary():
    begin_date, end_date, pricer, group, adlist = _get_group_and_config()

    return jsonify(
        irr_summary(
            pricer=pricer,
            adlist=adlist,
            start_date=begin_date,
            end_date=end_date,
            target_currency=group.currency,
        )
    )


@bp.get("/pnl")
@require_auth
def get_pnl():
    begin_date, end_date, pricer, group, adlist = _get_group_and_config()

    pnl = gen_pnl_data(
        account_datas=adlist,
        price_map=pricer.price_map,
        begin_date=begin_date,
        end_date=end_date,
        target_currency=group.currency,
    )

    return jsonify(pnl)


@bp.get("/nav_index")
@require_auth
def get_nav_index():
    begin_date, end_date, pricer, group, adlist = _get_group_and_config()

    nav_index = gen_nav_index_data(
        account_datas=adlist,
        price_map=pricer.price_map,
        begin_date=begin_date,
        end_date=end_date,
        target_currency=group.currency,
    )

    return jsonify(nav_index)


@bp.get("/cash_flows")
@require_auth
def get_cash_flows():
    begin_date, end_date, pricer, _, adlist = _get_group_and_config()

    cash_flows = returnslib.truncate_and_merge_cash_flows(
        pricer, adlist, begin_date, end_date
    )

    return jsonify(cash_flows)


@bp.get("/investments")
@require_auth
def get_investments():
    begin_date, end_date, pricer, _, adlist = _get_group_and_config()

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


@bp.get("/calendar_returns")
@require_auth
def get_calendar_returns():
    begin_date, end_date, pricer, group, adlist = _get_group_and_config()

    return jsonify(
        calendar_returns(pricer, adlist, begin_date, end_date, group.currency)
    )


@require_auth
@bp.get("/cumulative_returns")
def get_cumulative_returns():
    begin_date, end_date, pricer, group, adlist = _get_group_and_config()

    return jsonify(
        cumulative_returns(pricer, adlist, begin_date, end_date, group.currency)
    )


@require_auth
@bp.get("/holding")
def get_holding():
    entries = current_app.entries

    beangrow_path = current_app.doujia_config.beangrow_config
    distribution_path = os.path.join(
        current_app.ledger_root, current_app.doujia_config.investment_config
    )
    investment_groups = get_investment_holdings(
        entries,
        beangrow_path,
        distribution_path,
        current_app.options_map,
        datetime.date.today() + datetime.timedelta(days=1),
    )

    return jsonify(create_portfolio_report(entries, investment_groups, "USD"))
