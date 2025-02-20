from typing import TypeVar
import datetime
from flask import Blueprint, jsonify, request
from beancount.core import data
from doujia.price.price_map import get_last_and_realtime_price_map
from doujia.report.balance import balance_at
from doujia.report.cumulative_balance import gen_cumulative_balances
from doujia.server.filter.auth import require_auth
from doujia.server.app import current_app

Directive = TypeVar("Directive", bound=data.Directive)  # type: ignore

bp = Blueprint("balance", __name__, url_prefix="/balance")


@bp.get("/short_assets")
@require_auth
def get_short_assets():
    today = datetime.date.today() + datetime.timedelta(days=1)
    first_day_of_year = datetime.date(today.year, 1, 1)

    _, price_map = get_last_and_realtime_price_map(current_app.entries)

    return jsonify(
        (
            first_day_of_year,
            balance_at(
                entries=current_app.entries,
                at_date=first_day_of_year,
                account_prefixes=["Assets:Short", "Liabilities:Short"],
                target_currency="CNY",
                price_map=price_map,
            ),
        ),
        (
            today,
            balance_at(
                entries=current_app.entries,
                at_date=today,
                account_prefixes=["Assets:Short", "Liabilities:Short"],
                target_currency="CNY",
                price_map=price_map,
            ),
        ),
    )


@bp.get("/investments")
@require_auth
def get_investments():
    today = datetime.date.today() + datetime.timedelta(days=1)
    first_day_of_year = datetime.date(today.year, 1, 1)
    _, price_map = get_last_and_realtime_price_map(current_app.entries)

    return jsonify(
        (
            first_day_of_year,
            balance_at(
                entries=current_app.entries,
                at_date=first_day_of_year,
                account_prefixes=["Assets:Short:Stock", "Assets:Short:Investment"],
                target_currency="CNY",
                price_map=price_map,
            ),
        ),
        (
            today,
            balance_at(
                entries=current_app.entries,
                at_date=today,
                account_prefixes=["Assets:Short:Stock", "Assets:Short:Investment"],
                target_currency="CNY",
                price_map=price_map,
            ),
        ),
    )


@bp.get("/current")
@require_auth
def get_current():
    today = datetime.date.today() + datetime.timedelta(days=1)
    _, price_map = get_last_and_realtime_price_map(current_app.entries)

    return jsonify(
        (
            today,
            balance_at(
                entries=current_app.entries,
                at_date=today,
                account_prefixes=[
                    "Assets:Short:Current:CMB",
                    "Assets:Receivables",
                    "Assets:Short:Current:Alipay",
                    "Liabilities:Short:CreditCard:CMB",
                ],
                target_currency="CNY",
                price_map=price_map,
            ),
        ),
    )


@bp.get("/cumulative")
@require_auth
def get_cumulative():
    today = datetime.date.today()
    end_date = datetime.date(today.year, 12, 31)
    begin_date = datetime.date(today.year, 1, 1)
    account_prefix = request.args.get("account_prefix", "Expenses:")

    return jsonify(
        gen_cumulative_balances(
            entries=current_app.entries,
            account_prefix=account_prefix,
            begin_date=begin_date,
            end_date_inclusive=end_date,
        )
    )
