import datetime
from decimal import Decimal
from pathlib import Path

from fava.core import FavaLedger
from freezegun import freeze_time

from doujia.report.daily import DailyReport, daily_report, report_to_message


@freeze_time("2022-01-01")
def test_daily_report(doc_ledger: FavaLedger):
    """
    @@@/main.bean
    1970-01-01 open Assets:Short:Current:CMB
    1970-01-01 open Liabilities:Short:CreditCard:CMB
    1970-01-01 open Equity:Opening-Balance

    2022-01-01 *
        Assets:Short:Current:CMB 100.00 CNY
        Equity:Opening-Balance

    2022-01-01 *
        Liabilities:Short:CreditCard:CMB -10.00 CNY
        Equity:Opening-Balance

    @@@/beangrow.pbtxt
    """
    report = daily_report(
        doc_ledger.all_entries,
        {"dcontext": None},
        Path("/beangrow.pbtxt"),
        ["Assets:Short:Current:CMB"],
        ["Liabilities:Short:CreditCard:CMB"],
    )
    assert report.cash_balance == 100
    assert report.credit_card_balance == -10
    assert report.date == datetime.date(2022, 1, 1)
    assert report.xirr == 0


@freeze_time("2022-01-01")
def test_daily_report_exclude_future_transaction(
    doc_ledger: FavaLedger,
):  # 不计算未来的交易
    """
    @@@/main.bean
    1970-01-01 open Assets:Short:Current:CMB
    1970-01-01 open Liabilities:Short:CreditCard:CMB
    1970-01-01 open Equity:Opening-Balance

    2022-01-01 *
        Assets:Short:Current:CMB 100.00 CNY
        Equity:Opening-Balance

    2022-01-02 *
        Assets:Short:Current:CMB 100.00 CNY
        Equity:Opening-Balance

    2022-01-01 *
        Liabilities:Short:CreditCard:CMB -10.00 CNY
        Equity:Opening-Balance

    @@@/beangrow.pbtxt
    """
    report = daily_report(
        doc_ledger.all_entries,
        {"dcontext": None},
        Path("/beangrow.pbtxt"),
        ["Assets:Short:Current:CMB"],
        ["Liabilities:Short:CreditCard:CMB"],
    )
    assert report.cash_balance == 100
    assert report.credit_card_balance == -10
    assert report.date == datetime.date(2022, 1, 1)


def test_format_message():
    report = DailyReport(
        cash_balance=100.00,
        credit_card_balance=-100.00,
        date=datetime.date(2024, 1, 3),
        xirr=Decimal(0.10396),
        today_change=-59.23,
        yesterday_change=-1273.82,
    )
    ret = report_to_message(report)

    assert ret == "[2024 年 1 月 3 日] 目前现金类权益 0.00 元，XIRR 10.40%。"


@freeze_time("2022-01-03")
def test_daily_report_today_and_yesterday_change(
    doc_ledger: FavaLedger,
):  # 计算今日和昨日的账户变化
    """
    @@@/main.bean
    1970-01-01 open Assets:Short:Current:CMB
    1970-01-01 open Liabilities:Short:CreditCard:CMB
    1970-01-01 open Equity:Opening-Balance

    2022-01-01 *
        Assets:Short:Current:CMB 100.00 CNY
        Equity:Opening-Balance

    2022-01-01 *
        Assets:Short:Current:CMB 100.00 CNY
        Equity:Opening-Balance

    2022-01-01 *
        Liabilities:Short:CreditCard:CMB -10.00 CNY
        Equity:Opening-Balance

    ; Yesterday Change
    2022-01-02 *
        Assets:Short:Current:CMB -50.00 CNY
        Equity:Opening-Balance

    ; Today Change
    2022-01-03 *
        Liabilities:Short:CreditCard:CMB -30.00 CNY
        Equity:Opening-Balance

    @@@/beangrow.pbtxt
    """
    report = daily_report(
        doc_ledger.all_entries,
        {"dcontext": None},
        Path("/beangrow.pbtxt"),
        ["Assets:Short:Current:CMB"],
        ["Liabilities:Short:CreditCard:CMB"],
    )
    assert report.yesterday_change == -50.00
    assert report.today_change == -30.00
