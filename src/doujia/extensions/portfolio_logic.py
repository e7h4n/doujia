import datetime
from collections import namedtuple
from pathlib import Path
from typing import Any, List, Dict, Tuple

import beangrow.config as configlib
import beangrow.returns as returnslib
from beancount.core import prices, getters
from beancount.core.data import Directive
from beangrow import investments
from fava.core import FavaLedger

Config = namedtuple("Config", ["beangrow_config_path"])
GroupPerformanceDigest = namedtuple("GroupPerformanceDigest", ["irr"])
GroupPerformance = namedtuple(
    "GroupPerformance",
    [
        "units",
        "market_value",
        "returns",
        "irr",
        "irr_exdiv",
        "irr_div",
    ],
)


def extract_beangrow_config_from_fava(
    ledger: FavaLedger, end_date: datetime.date
) -> Tuple[returnslib.Pricer, Dict, Dict[investments.Account, investments.AccountData]]:
    beangrow_config_path = ledger.join_path("beangrow.pbtxt")
    entries = ledger.all_entries
    dcontext = ledger.options["dcontext"]
    return extract_beangrow_config(entries, beangrow_config_path, end_date, dcontext)


def extract_beangrow_config(
    entries: list[Directive],  # type: ignore
    beangrow_config_path: Path,
    end_date: datetime.date,
    dcontext: Any,
) -> Tuple[returnslib.Pricer, Dict, Dict[investments.Account, investments.AccountData]]:
    accounts = getters.get_accounts(entries)

    price_map = prices.build_price_map(entries)
    pricer = returnslib.Pricer(price_map)

    beangrow_config = configlib.read_config(str(beangrow_config_path), [], accounts)

    account_data_map = investments.extract(
        entries,
        dcontext,
        beangrow_config,
        end_date,
        False,
        "",
    )

    return pricer, beangrow_config.groups.group, account_data_map


def overview_report(
    pricer: returnslib.Pricer,
    groups: Dict,
    account_data_map: Dict[investments.Account, investments.AccountData],
    start_date: datetime.date,
    end_date: datetime.date,
) -> list[Dict]:
    group_performances = []
    for group in groups:
        adlist = [
            account_data_map[name]
            for name in group.investment
            if name in account_data_map
        ]

        performance = _calculate_simple_group_performance(
            pricer, adlist, start_date, end_date, group.currency
        )
        group_performances.append(dict(name=group.name, irr=performance.irr))

    return group_performances


def _calculate_simple_group_performance(
    pricer: returnslib.Pricer,
    adlist: List[investments.AccountData],
    start_date: datetime.date,
    end_date: datetime.date,
    target_currency: str,
) -> GroupPerformanceDigest:
    truncated_cash_flows = returnslib.truncate_and_merge_cash_flows(
        pricer, adlist, start_date, end_date
    )
    irr = returnslib.compute_returns(
        truncated_cash_flows, pricer, target_currency, end_date
    )

    return GroupPerformanceDigest(irr=irr.total)
