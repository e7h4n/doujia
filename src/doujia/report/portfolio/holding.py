from datetime import date
from decimal import Decimal

from beancount.core.convert import convert_amount
from beancount.core.data import Amount
from beancount.core.prices import PriceMap, get_price

from doujia.report.portfolio.data import Holding


def _get_price_and_market_value(
    commodity: str,
    cost_currency: str,
    units_number: Decimal,
    price_map,
    target_currency: str,
):
    price = get_price(price_map, (commodity, cost_currency), date=date.today())[1]
    market_value = convert_amount(
        Amount(price * units_number, cost_currency),
        target_currency,
        price_map,
        date=date.today(),
        via=["USD", "CNY", "HKD"],
    )
    return price, market_value


def create_holding(
    commodity: str,
    position: Decimal,
    total_cost: Amount,
    last_price_map: PriceMap,
    realtime_price_map: PriceMap,
    target_currency: str,
) -> Holding:
    """获取价格和市值

    Args:
        commodity: 投资标的名称
        cost_currency: 成本货币, 该投资标的的所有买卖必须在同一货币下进行
        units_number: 当前持仓数量
        last_price_map: 价格映射表, 不包括正在进行中的市场上的报价
        realtime_price_map: 价格映射表, 包括正在进行中的市场上的报价
        target_currency: 目标货币, 用于计算市值、盈亏
    Returns:
        Portfolio: 返回该投资标的的收益报告
    """

    cost_currency = total_cost.currency
    average_cost = Amount(total_cost.number / position, cost_currency)

    realtime_price, realtime_market_value = _get_price_and_market_value(
        commodity,
        cost_currency,
        position,
        realtime_price_map,
        target_currency,
    )

    last_price, last_market_value = _get_price_and_market_value(
        commodity,
        cost_currency,
        position,
        last_price_map,
        target_currency,
    )

    today_change = realtime_price - last_price
    today_change_ratio = today_change / last_price

    realtime_change = realtime_price - average_cost.number
    realtime_change_ratio = realtime_change / average_cost.number

    last_change = last_price - average_cost.number
    last_change_ratio = last_change / average_cost.number

    return Holding(
        name=commodity,
        position=position,
        average_cost=average_cost,
        realtime_price=Amount(realtime_price, cost_currency),
        last_price=Amount(last_price, cost_currency),
        realtime_market_value=realtime_market_value,
        last_market_value=last_market_value,
        today_price_change=Amount(today_change, cost_currency),
        today_price_change_ratio=today_change_ratio,
        realtime_ratio=0.0,
        unrealized_pnl=convert_amount(
            Amount(realtime_change * position, cost_currency),
            target_currency,
            realtime_price_map,
            date=date.today(),
            via=["USD", "CNY", "HKD"],
        ),
        unrealized_pnl_ratio=realtime_change_ratio,
        realtime_price_change=Amount(realtime_change, cost_currency),
        realtime_price_change_ratio=realtime_change_ratio,
        last_price_change=Amount(last_change, cost_currency),
        last_price_change_ratio=last_change_ratio,
    )
