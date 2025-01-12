from dataclasses import dataclass
from datetime import datetime, date
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Tuple

import beangrow.config as configlib
from matplotlib.dates import relativedelta
import yaml
from beancount.core import getters
from beangrow import investments
from beangrow.config_pb2 import Config
from beancount.core.data import Directive, Transaction
from beancount.core.inventory import Inventory
from beangrow.investments import CashFlow
import beangrow.returns as returnslib
from doujia.report.portfolio.data import (
    InvestmentHolding,
)
from beangrow.reports import compute_returns_table


def _extract_beangrow_config(
    entries: list[Directive],  # type: ignore
    beangrow_config_path: Path,
) -> Config:  # type: ignore
    accounts = getters.get_accounts(entries)
    return configlib.read_config(str(beangrow_config_path), [], accounts)


def get_investment_holdings(  # noqa: C901
    entries: list[Directive],  # type: ignore
    beangrow_config_path: Path,
    investment_config_path: Path,
    options_map: dict,
    end_date: datetime.date,
) -> list[InvestmentHolding]:
    beangrow_config: Config = _extract_beangrow_config(entries, beangrow_config_path)  # type: ignore

    account_data_map = investments.extract(
        entries,
        options_map["dcontext"],
        beangrow_config,
        end_date,
        False,
        "",
    )

    with open(investment_config_path, "r", encoding="utf-8") as f:
        investment_config = yaml.safe_load(f)

    results = []
    for group in beangrow_config.groups.group:
        # 如果投资组合在 investment_config 中不存在，则跳过
        if not any(
            investment["group"] == group.name
            for investment in investment_config["investments"]
        ):
            continue

        inventory = Inventory()
        expected_ratio = next(
            (
                investment["ratio"]
                for investment in investment_config["investments"]
                if investment["group"] == group.name
            ),
            0,
        )

        adlist = [
            account_data_map[name]
            for name in group.investment
            if name in account_data_map
        ]

        for data in adlist:
            for transaction in data.transactions:
                for posting in transaction.postings:
                    if posting.account == data.account:
                        inventory.add_position(posting)

        results.append(
            InvestmentHolding(
                name=group.name, expected_ratio=expected_ratio, inventory=inventory
            )
        )

    if "cash" in investment_config:
        cash_config = investment_config["cash"]
        inventory = Inventory()
        for account_name in cash_config["account"]:
            for entry in entries:
                if not isinstance(entry, Transaction):
                    continue
                if entry.date > end_date:
                    continue

                for posting in entry.postings:
                    if posting.account == account_name:
                        inventory.add_position(posting)

        for group in results:
            if group.name == cash_config["group"]:
                group.inventory.add_inventory(inventory)

    return results


@dataclass
class InvestmentPerformance:
    name: str
    pnl: Decimal
    currency: str


def investments_performance(
    cash_flows: List[CashFlow],
) -> Tuple[List[InvestmentPerformance], List[InvestmentPerformance]]:
    account_map: Dict[str, List[CashFlow]] = {}

    # Group cash flows by account
    for cf in cash_flows:
        if cf.account not in account_map:
            account_map[cf.account] = []
        account_map[cf.account].append(cf)

    profitable_investments = []
    unprofitable_investments = []

    for account, flows in account_map.items():
        income = Decimal("0")
        outcome = Decimal("0")
        balance = Decimal("0")
        currency = None

        for cf in flows:
            if currency is None:
                currency = cf.amount.currency
            assert cf.amount.currency == currency
            if cf.source == "close":
                balance = cf.amount.number
            elif cf.amount.number < 0:
                income += cf.amount.number
            else:
                outcome += cf.amount.number

        pnl = balance + outcome + income
        performance = InvestmentPerformance(
            name=account,
            pnl=balance + outcome + income,
            currency=currency,
        )
        if pnl > 0:
            profitable_investments.append(performance)
        else:
            unprofitable_investments.append(performance)

    profitable_investments.sort(
        key=lambda x: (
            x.pnl / 7
            if x.currency.upper() == "CNY"
            else x.pnl * Decimal("0.13") if x.currency.upper() == "HKD" else x.pnl
        ),
        reverse=True,
    )
    unprofitable_investments.sort(
        key=lambda x: (
            x.pnl / 7
            if x.currency.upper() == "CNY"
            else x.pnl * Decimal("0.13") if x.currency.upper() == "HKD" else x.pnl
        )
    )
    return (profitable_investments, unprofitable_investments)


def _get_calendar_intervals(
    begin_date: date, end_date: date
) -> List[Tuple[str, date, date]]:

    intervals = [
        (str(year), date(year, 1, 1), date(year + 1, 1, 1))
        for year in range(begin_date.year, end_date.year)
    ]
    intervals.append((str(end_date.year), date(end_date.year, 1, 1), end_date))
    return intervals


def _get_cumulative_intervals(
    begin_date: date, end_date: date
) -> list[Tuple[str, date, date]]:
    result: list[Tuple[str, date, date]] = []

    result.append((f"From {begin_date}", begin_date, end_date))

    if end_date.year - 15 >= begin_date.year:
        result.append(("15 Years", date(end_date.year - 15, 1, 1), end_date))
    if end_date.year - 10 >= begin_date.year:
        result.append(("10 Years", date(end_date.year - 10, 1, 1), end_date))
    if end_date.year - 5 >= begin_date.year:
        result.append(("5 Years", date(end_date.year - 5, 1, 1), end_date))
    if end_date.year - 4 >= begin_date.year:
        result.append(("4 Years", date(end_date.year - 4, 1, 1), end_date))
    if end_date.year - 3 >= begin_date.year:
        result.append(("3 Years", date(end_date.year - 3, 1, 1), end_date))
    if end_date.year - 2 >= begin_date.year:
        result.append(("2 Years", date(end_date.year - 2, 1, 1), end_date))
    if end_date.year - 1 >= begin_date.year:
        result.append(("1 Year", date(end_date.year - 1, 1, 1), end_date))
    result.append(("Ytd", date(end_date.year, 1, 1), end_date))
    result.append(("Rolling 6 months", end_date - relativedelta(months=6), end_date))
    result.append(("Rolling 3 months", end_date - relativedelta(months=3), end_date))

    return result


def _compute_returns_series(
    pricer: returnslib.Pricer,
    target_currency: str,
    account_data: List[investments.AccountData],
    intervals: List[Tuple[str, date, date]],
) -> list[list[Tuple[date, float]]]:
    series = [[], [], []]

    found = False
    for _, date1, date2 in intervals:
        cash_flows = returnslib.truncate_and_merge_cash_flows(
            pricer, account_data, date1, date2
        )
        returns = returnslib.compute_returns(cash_flows, pricer, target_currency, date2)
        if returns.total != 0:
            found = True

        if found:
            series[0].append([date2, returns.total])
            series[1].append([date2, returns.exdiv])
            series[2].append([date2, returns.div])
    return series


def calendar_returns(
    pricer: returnslib.Pricer,
    account_data: List[investments.AccountData],
    start_date: date,
    end_date: date,
    target_currency: str,
):

    return _compute_returns_series(
        pricer,
        target_currency,
        account_data,
        _get_calendar_intervals(start_date, end_date),
    )


def cumulative_returns(
    pricer: returnslib.Pricer,
    account_data: List[investments.AccountData],
    start_date: date,
    end_date: date,
    target_currency: str,
):

    return compute_returns_table(
        pricer,
        target_currency,
        account_data,
        _get_cumulative_intervals(start_date, end_date),
    )


@dataclass
class IrrSummary:
    target_currency: str
    total_returns: Decimal
    div_returns: Decimal
    years: Decimal
    first_date: datetime.date
    last_date: datetime.date


def irr_summary(
    pricer: returnslib.Pricer,
    adlist: List[investments.AccountData],
    start_date: datetime.date,
    end_date: datetime.date,
    target_currency: str,
) -> IrrSummary:
    cash_flows = returnslib.truncate_and_merge_cash_flows(
        pricer, adlist, start_date, end_date
    )

    returns = returnslib.compute_returns(cash_flows, pricer, target_currency, end_date)

    return IrrSummary(
        target_currency=target_currency,
        div_returns=returns.div,
        total_returns=returns.total,
        years=returns.years,
        first_date=returns.first_date,
        last_date=returns.last_date,
    )
