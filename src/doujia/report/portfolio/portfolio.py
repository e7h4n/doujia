from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from math import sqrt

from beancount.core.convert import get_cost
from beancount.core.data import Amount, D, Directive
from beancount.core.inventory import Inventory

from doujia.price.price_map import get_last_and_realtime_price_map
from doujia.report.portfolio.data import HoldingGroup, InvestmentHolding, Portfolio
from doujia.report.portfolio.holding import create_holding
from doujia.report.portfolio.stat import fill_stat_fields


def calc_portfolio_ratio_report(
    entries: list[Directive],  # type: ignore
    investment_groups: list[InvestmentHolding],
    target_currency: str,
) -> list[HoldingGroup]:
    last_price_map, realtime_price_map = get_last_and_realtime_price_map(entries)
    portofolio_groups = _create_portfolio_groups(investment_groups, last_price_map, realtime_price_map, target_currency)
    fill_stat_fields(portofolio_groups, target_currency)

    portofolio_groups.sort(
        key=lambda group: (
            group.name.lower().find("cash") != -1,
            -group.realtime_market_value.number,
        )
    )
    return portofolio_groups


def _create_portfolio_groups(
    investment_groups: list[InvestmentHolding],
    last_price_map,
    realtime_price_map,
    target_currency: str,
):
    portofolio_groups = []
    for group in investment_groups:
        portofolio_group = _create_portfolio_group(group, target_currency)
        _add_portfolios_to_group(
            portofolio_group,
            group.inventory,
            last_price_map,
            realtime_price_map,
            target_currency,
        )
        portofolio_groups.append(portofolio_group)
    return portofolio_groups


def _create_portfolio_group(group: InvestmentHolding, target_currency: str):
    return HoldingGroup(
        name=group.name,
        target_ratio=group.expected_ratio,
        target_diff=Amount(D(0), target_currency),
        holdings=[],
        unrealized_pnl=Amount(D(0), target_currency),
        unrealized_pnl_ratio=0.0,
        realtime_market_value=Amount(D(0), target_currency),
        last_market_value=Amount(D(0), target_currency),
        realtime_ratio=0.0,
        today_market_value_change=Amount(D(0), target_currency),
        today_market_value_change_ratio=0.0,
    )


def _add_portfolios_to_group(
    portofolio_group: HoldingGroup,
    inventory: Inventory,
    last_price_map,
    realtime_price_map,
    target_currency: str,
):
    commodity_total_positions = _group_position_by_commodity(inventory)

    for commodity, total_position in commodity_total_positions.items():
        position = total_position.units
        total_cost = total_position.cost
        portfolio = create_holding(
            commodity,
            position,
            total_cost,
            last_price_map,
            realtime_price_map,
            target_currency,
        )
        portofolio_group.holdings.append(portfolio)

    portofolio_group.holdings.sort(key=lambda h: h.realtime_market_value.number, reverse=True)


@dataclass
class TotalPositionWithCost:
    """
    总持仓和总成本
    """

    units: Decimal
    cost: Amount


def _group_position_by_commodity(
    inventory: Inventory,
) -> dict[str, TotalPositionWithCost]:
    total_costs = defaultdict(D)
    position_counts = defaultdict(D)
    position_cost_currencies = defaultdict(str)

    for position in inventory:
        cost = get_cost(position)
        commodity = position.units.currency
        if commodity not in position_cost_currencies:
            position_cost_currencies[commodity] = cost.currency
        assert position_cost_currencies[commodity] == cost.currency

        total_costs[commodity] += cost.number
        position_counts[commodity] += position.units.number

    return {
        commodity: TotalPositionWithCost(
            units=position_counts[commodity],
            cost=Amount(total_costs[commodity], position_cost_currencies[commodity]),
        )
        for commodity in total_costs
    }


def create_portfolio_report(
    entries: list[Directive],  # type: ignore
    investment_groups: list[InvestmentHolding],
    target_currency: str,
) -> Portfolio:
    portfolio_groups = calc_portfolio_ratio_report(entries, investment_groups, target_currency)

    total_unrealized_pnl = D(0)
    total_realtime_market_value = D(0)
    total_last_market_value = D(0)
    total_today_market_value_change = D(0)
    for group in portfolio_groups:
        total_unrealized_pnl += group.unrealized_pnl.number
        total_realtime_market_value += group.realtime_market_value.number
        total_last_market_value += group.last_market_value.number
        total_today_market_value_change += group.today_market_value_change.number

    index = 0
    for group in portfolio_groups:
        index += pow(group.target_diff.number / total_realtime_market_value, 2)

    index = sqrt(index)

    return Portfolio(
        groups=portfolio_groups,
        unrealized_pnl=Amount(total_unrealized_pnl, target_currency),
        realtime_market_value=Amount(total_realtime_market_value, target_currency),
        last_market_value=Amount(total_last_market_value, target_currency),
        today_market_value_change=Amount(total_today_market_value_change, target_currency),
        today_market_value_change_ratio=total_today_market_value_change / total_last_market_value,
        index=index,
    )
