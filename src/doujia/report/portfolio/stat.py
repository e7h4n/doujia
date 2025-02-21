from dataclasses import dataclass
from decimal import Decimal

from beancount.core.data import Amount

from doujia.report.portfolio.data import HoldingGroup


def fill_stat_fields(portofolio_groups: list[HoldingGroup], target_currency: str):
    """
    填充 PortfolioGroup 中的统计字段, 这些统计字段需要计算所有 Group 以及 Group 下所有 Portfolio 的数据统计得来
    例如累计市值、各个投资标的的占比
    """
    total_realtime_market_value = _fill_group_market_values_and_sum_total_value(portofolio_groups, target_currency)
    _fill_ratios(portofolio_groups, total_realtime_market_value)


@dataclass
class GroupValues:
    """临时传递数据的 DTO, 传递一个投资组合下所有的累加数据"""

    realtime_market_value: Decimal
    last_market_value: Decimal
    unrealized_pnl: Decimal


def _fill_group_market_values_and_sum_total_value(
    portofolio_groups: list[HoldingGroup], target_currency: str
) -> Decimal:
    """填充每个投资组合组的市值相关字段, 并返回总实时市值"""
    total_realtime_market_value = Decimal(0)

    for portofolio_group in portofolio_groups:
        group_values = _sum_group_values(portofolio_group)
        _set_group_amounts(portofolio_group, group_values, target_currency)
        total_realtime_market_value += group_values.realtime_market_value

    return total_realtime_market_value


def _sum_group_values(portofolio_group: HoldingGroup) -> GroupValues:
    """计算投资组合组内各项市值总和"""
    group_realtime_market_value = Decimal(0)
    group_last_market_value = Decimal(0)
    group_unrealized_pnl = Decimal(0)

    for portfolio in portofolio_group.holdings:
        group_realtime_market_value += portfolio.realtime_market_value.number
        group_last_market_value += portfolio.last_market_value.number
        group_unrealized_pnl += portfolio.unrealized_pnl.number

    return GroupValues(
        realtime_market_value=group_realtime_market_value,
        last_market_value=group_last_market_value,
        unrealized_pnl=group_unrealized_pnl,
    )


def _set_group_amounts(portofolio_group: HoldingGroup, values: GroupValues, target_currency: str):
    """
    填充 portfolio_group 的市值相关字段, 包括 realtime_market_value, last_market_value,
    unrealized_pnl, today_market_value_change, 这几个字段来自于 portfolioGroup 下所有 portfolio 的市值相关字段
    """

    portofolio_group.realtime_market_value = Amount(values.realtime_market_value, target_currency)
    portofolio_group.last_market_value = Amount(values.last_market_value, target_currency)
    portofolio_group.unrealized_pnl = Amount(values.unrealized_pnl, target_currency)
    portofolio_group.today_market_value_change = Amount(
        values.realtime_market_value - values.last_market_value, target_currency
    )
    portofolio_group.today_market_value_change_ratio = (
        portofolio_group.today_market_value_change.number / values.last_market_value
    )
    portofolio_group.unrealized_pnl_ratio = values.unrealized_pnl / (
        values.realtime_market_value - values.unrealized_pnl
    )


def _fill_ratios(portofolio_groups: list[HoldingGroup], total_realtime_market_value: Decimal):
    """
    计算并填充各投资组合的实时市值占比
    """
    for portofolio_group in portofolio_groups:
        portofolio_group.realtime_ratio = float(
            portofolio_group.realtime_market_value.number / total_realtime_market_value
        )

        portofolio_group.target_diff = Amount(
            Decimal(portofolio_group.realtime_ratio - portofolio_group.target_ratio) * total_realtime_market_value,
            portofolio_group.target_diff.currency,
        )

        for portfolio in portofolio_group.holdings:
            portfolio.realtime_ratio = float(portfolio.realtime_market_value.number / total_realtime_market_value)
