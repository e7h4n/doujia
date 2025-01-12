from dataclasses import dataclass
from beancount.core.number import D


from beancount.core.data import Directive
from beancount.core.amount import Amount
from beancount.core.inventory import Inventory
from beanquery import query


@dataclass
class Holding:
    unit: Amount
    average_cost: Amount
    book_value: Amount
    market_value: Amount
    unrealized_profit_pct: D


def holdings_at(
    entries: list[Directive],  # type: ignore
    options_map: dict,
    account_prefix_list: list[str],
) -> Inventory:
    account_cond = (
        "(" + " OR ".join(['account ~ "^' + x + '"' for x in account_prefix_list]) + ")"
    )

    holdings_query = (
        """
        SELECT
            units(sum(position)) as units,
            SAFEDIV(number(only(first(cost_currency), cost(sum(position)))), number(only(first(currency), units(sum(position))))) as average_cost,
            cost(sum(position)) as book_value,
            value(sum(position)) as market_value,
            safediv((abs(sum(number(value(position)))) - abs(sum(number(cost(position))))), sum(number(cost(position)))) * 100 as unrealized_profit_pct
        WHERE """
        + account_cond
        + """
        GROUP BY currency, cost_currency
"""
    )

    ret = query.run_query(entries, options_map, holdings_query)

    return ret[1]
