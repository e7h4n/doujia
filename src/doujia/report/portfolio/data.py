from dataclasses import dataclass
from decimal import Decimal

from beancount.core.data import Amount
from beancount.core.inventory import Inventory


@dataclass
class MarketValuePnl:
    realtime_ratio: Decimal  # 实时占比
    unrealized_pnl: Amount  # 未实现盈亏
    unrealized_pnl_ratio: Decimal  # 未实现盈亏率
    realtime_market_value: Amount  # 实时市值
    last_market_value: Amount  # 昨日市值


@dataclass
class Holding(MarketValuePnl):
    name: str
    position: Decimal  # 持仓数量
    average_cost: Amount  # 持仓成本
    realtime_price: Amount  # 当前价格
    last_price: Amount  # 昨日价格
    today_price_change: Amount  # 今日变化
    today_price_change_ratio: Decimal  # 今日变化率
    realtime_price_change: Amount  # 实时价格相对成本变化
    realtime_price_change_ratio: Decimal  # 实时价格相对成本变化率
    last_price_change: Amount  # 昨日价格相对成本变化
    last_price_change_ratio: Decimal  # 昨日价格相对成本变化率


@dataclass
class HoldingGroup(MarketValuePnl):
    name: str
    target_ratio: Decimal  # 目标占比
    target_diff: Amount  # 调仓到目标的差额
    holdings: list[Holding]
    today_market_value_change: Amount  # 今日市值变化
    today_market_value_change_ratio: Decimal  # 今日市值变化率


@dataclass
class Portfolio:
    groups: list[HoldingGroup]
    unrealized_pnl: Amount  # 未实现盈亏
    realtime_market_value: Amount  # 实时市值
    last_market_value: Amount  # 昨日市值
    today_market_value_change: Amount  # 今日市值变化
    today_market_value_change_ratio: Decimal  # 今日市值变化率
    index: Decimal  # 偏离率标准差


@dataclass
class TotalPositionWithCost:
    """
    总持仓和总成本
    """

    units: Decimal
    cost: Amount


@dataclass
class InvestmentHolding:
    name: str
    inventory: Inventory
    expected_ratio: float
