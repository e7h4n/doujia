import argparse
import datetime
from decimal import Decimal
from pathlib import Path
from typing import NamedTuple

from beancount.core import getters
from beancount.core.data import Directive
from beancount.loader import load_file
from logzero import logger

from doujia.price.price_map import get_last_and_realtime_price_map
from doujia.report.pushover import Pushover
from doujia.report.summerize import sum_single_amount_between, calc_xirr


class DailyReport(NamedTuple):
    date: datetime.date
    credit_card_balance: Decimal
    cash_balance: Decimal
    xirr: Decimal
    today_change: Decimal
    yesterday_change: Decimal


def daily_report(
    entries: list[Directive],  # type: ignore
    options: dict,
    beangrow_config_path: Path,
    cash_account_prefix_list: list[str],
    credit_card_prefix_list: list[str],
) -> DailyReport:
    _, price_map = get_last_and_realtime_price_map(entries)
    min_date, _ = getters.get_min_max_dates(entries)
    max_date = datetime.date.today() + datetime.timedelta(days=1)

    cash_balance = sum_single_amount_between(
        entries, price_map, cash_account_prefix_list, [(min_date, max_date)], "CNY"
    )[0]
    credit_card_balance = sum_single_amount_between(
        entries, price_map, credit_card_prefix_list, [(min_date, max_date)], "CNY"
    )[0]

    all_cash_accounts = cash_account_prefix_list + credit_card_prefix_list
    [yesterday_change, today_change] = sum_single_amount_between(
        entries,
        price_map,
        all_cash_accounts,
        [
            (datetime.date.today() - datetime.timedelta(days=1), datetime.date.today()),
            (datetime.date.today(), datetime.date.today() + datetime.timedelta(days=1)),
        ],
        target_currency="CNY",
    )

    xirr = calc_xirr(entries, beangrow_config_path, options, max_date, "CNY")

    return DailyReport(
        cash_balance=cash_balance.amount,
        credit_card_balance=credit_card_balance.amount,
        date=datetime.date.today(),
        xirr=xirr,
        yesterday_change=yesterday_change.amount,
        today_change=today_change.amount,
    )


def report_to_message(report: DailyReport) -> str:
    formatted_report = (
        f"[{report.date.year} 年 {report.date.month} 月 {report.date.day} 日] "
        f"目前现金类权益 {(report.cash_balance + report.credit_card_balance):,.2f} 元，"
        f"XIRR {(report.xirr * 100):.2f}%。"
    )
    return formatted_report


def main():
    parser = argparse.ArgumentParser(description="获取每日账户资产报告")
    parser.add_argument("--token", help="Pushover Token", required=True)
    parser.add_argument("--user-key", help="Pushover User key", required=True)
    parser.add_argument("--dry-run", required=False, action="store_true")
    args = parser.parse_args()

    entries, _, options_map = load_file("./main.bean")
    report = daily_report(
        entries,
        options_map,
        Path("./config/beangrow.pbtxt"),
        [
            "Assets:Short:Current:CMB",
            "Assets:Short:Current:HSBC",
            "Assets:Receivables",
            "Assets:Short:Current:Alipay",
        ],
        ["Liabilities:Short:CreditCard:CMB", "Liabilities:Short:CreditCard:HSBC"],
    )
    message = report_to_message(report)

    if args.dry_run:
        logger.info(message)
    else:
        po = Pushover(args.token)
        po.user(args.user_key)
        po.send(po.msg(message))


if __name__ == "__main__":
    main()
