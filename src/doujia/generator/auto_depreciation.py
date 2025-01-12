"""
Fixed assets depreciation plugin for beancount.

在交易账户下，如果资产账户有 `useful_life` 和 `residual_value` 元数据，则自动生成折旧交易。
例如：
```python
2024-03-05 * "京东" "Sony A7C2" #FIXED_EXPENSE ^202403-SONY-A7C2
  Liabilities:Short:CreditCard:CMB                                             -13,993.00 CNY
  Assets:Long:Fixed:Digital                                                          1.00 SONY.A7C2 { 13,993.00 CNY }
    useful_life: "36m"
    residual_value: 8395.8 ; 三年折旧 60%
```
执行
pdm run python -m doujia.generator.auto_depreciation
会输出所有的折旧信息到控制台
"""

import decimal
import re
from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Optional, Tuple

from beancount.core import amount, convert, data
from beancount.core.number import D
from beancount.core.number import Decimal
from beancount.loader import load_file
from beancount.parser.printer import print_entries
from dateutil.relativedelta import relativedelta


@dataclass
class DepreciationConfig:
    """折旧配置"""

    assets_account: List[str]
    expenses_account: str
    method: str

    @classmethod
    def from_dict(cls, config: Optional[dict] = None) -> "DepreciationConfig":
        """从配置字典创建配置对象"""
        if config is None:
            config = {}

        return cls(
            assets_account=config.get("assets", ["Assets:Wealth:Fixed-Assets"]),
            expenses_account=config.get(
                "expenses", "Expenses:Property-Expenses:Depreciation"
            ),
            method=config.get("method", "parabola"),
        )


@dataclass
class DepreciationResult:
    """折旧计算结果"""

    dates: List[date]
    current_values: List[float]
    depreciation_values: List[Decimal]


def calculate_depreciation(
    start_value: float, end_value: float, buy_date: date, months: int, method: str
) -> DepreciationResult:
    """计算折旧值序列"""
    methods = {
        "parabola": calculate_parabola_value,
        "linear": calculate_linear_value,
    }
    get_current_value = methods[method]

    dates_list = [buy_date + relativedelta(months=x) for x in range(1, months + 1)]
    days_list = [(x - buy_date).days for x in dates_list]
    depreciation_days = days_list[-1]

    current_values = [
        get_current_value(x, start_value, end_value, depreciation_days)
        for x in days_list
    ]

    depreciation_values = []
    for i, value in enumerate(current_values):
        previous_value = current_values[i - 1] if i > 0 else start_value
        depreciation_values.append(
            D(previous_value - value).quantize(decimal.Decimal("0.00"))
        )

    return DepreciationResult(dates_list, current_values, depreciation_values)


def calculate_parabola_value(
    x: int, start_value: float, end_value: float, days: int
) -> float:
    """使用抛物线方法计算当前价值"""
    a = (start_value - end_value) / days**2
    b = -2 * (start_value - end_value) / days
    c = start_value
    return round(a * x**2 + b * x + c)


def calculate_linear_value(
    x: int, start_value: float, end_value: float, days: int
) -> float:
    """使用线性方法计算当前价值"""
    k = -(start_value - end_value) / days
    b = start_value
    return round(k * x + b)


def parse_useful_life(useful_life: str) -> int:
    """解析使用寿命字符串，返回月数"""
    m = re.match(r"([0-9]+)([my])", str.lower(useful_life))
    months = int(m.group(1))
    if m.group(2) == "y":
        months *= 12
    return months


def create_depreciation_posting(
    original_posting: data.Posting,
    date: date,
    current_value: float,
    expenses_account: str,
    depreciation_value: Decimal,
) -> List[data.Posting]:
    """创建折旧相关的过账"""
    # 移除折旧相关的元数据
    new_meta = original_posting.meta.copy()
    try:
        del new_meta["useful_life"]
        del new_meta["residual_value"]
    except KeyError:
        pass

    # 卖出原资产
    units = convert.get_units(original_posting)
    sell_posting = original_posting._replace(
        units=amount.mul(units, Decimal(-1)), meta=new_meta
    )

    # 买入新资产
    new_cost = original_posting.cost._replace(date=date, number=Decimal(current_value))
    buy_posting = original_posting._replace(cost=new_cost, meta=new_meta)

    # 记录折旧费用
    expense_units = amount.Amount(
        original_posting.units.number * depreciation_value,
        original_posting.cost.currency,
    )
    expense_posting = original_posting._replace(
        account=expenses_account, units=expense_units, cost=None, meta=new_meta
    )

    return [sell_posting, buy_posting, expense_posting]


def create_depreciation_entry(
    original_entry: data.Transaction,  # type: ignore
    date: date,
    label: Optional[str],
    postings: List[data.Posting],
) -> data.Transaction:  # type: ignore
    """创建折旧交易"""
    if original_entry.narration and label:
        new_narration = f"{original_entry.narration} 自动折旧:{label}"
    elif original_entry.narration:
        new_narration = f"{original_entry.narration} 自动折旧"
    elif label:
        new_narration = f"自动折旧:{label}"
    else:
        new_narration = "自动折旧"

    return original_entry._replace(
        date=date, narration=new_narration, flag="*", postings=postings
    )


def create_price_entry(
    entry: data.Transaction,  # type: ignore
    date: date,
    posting: data.Posting,
    current_value: float,
) -> data.Price:  # type: ignore
    """创建价格记录"""
    return data.Price(
        entry.meta,
        date,
        posting.units.currency,
        amount.Amount(D(current_value), posting.cost.currency),
    )


def generate_directives(
    entry: data.Transaction,  # type: ignore
    posting: data.Posting,
    txn_date: date,
    current_value: float,
    expenses_account: str,
    depreciation_value: Decimal,
) -> Tuple[data.Transaction, data.Price]:  # type: ignore
    """生成折旧和价格指令"""
    # 创建折旧过账
    postings = create_depreciation_posting(
        posting,
        txn_date,
        current_value,
        expenses_account,
        depreciation_value,
    )

    # 创建折旧交易
    depreciation_entry = create_depreciation_entry(
        entry, txn_date, posting.cost.label, postings
    )

    # 创建价格记录
    price_entry = create_price_entry(entry, txn_date, posting, current_value)

    return depreciation_entry, price_entry


def process_fixed_asset_posting(
    entry: data.Transaction,  # type: ignore
    posting: data.Posting,
    config: DepreciationConfig,
) -> Tuple[List[data.Transaction], List[data.Price]]:  # type: ignore
    """处理单个固定资产过账"""
    original_value = float(posting.cost.number)
    end_value = float(posting.meta.get("residual_value", 0))
    months = parse_useful_life(posting.meta["useful_life"])

    depreciation_result = calculate_depreciation(
        original_value, end_value, entry.date, months, config.method
    )

    depreciation_entries = []
    price_entries = []

    for i, txn_date in enumerate(depreciation_result.dates):
        depreciation_entry, price_entry = generate_directives(
            entry,
            posting,
            txn_date,
            depreciation_result.current_values[i],
            config.expenses_account,
            depreciation_result.depreciation_values[i],
        )
        depreciation_entries.append(depreciation_entry)
        price_entries.append(price_entry)

    return depreciation_entries, price_entries


def auto_depreciation(
    entries: List[data.Transaction], _, config: Optional[dict] = None  # type: ignore
) -> Tuple[Dict[str, List[data.Transaction]], Dict[str, List[data.Price]]]:  # type: ignore
    """自动生成固定资产折旧分录"""
    config = DepreciationConfig.from_dict(config)

    depreciation_entries: List[data.Transaction] = []  # type: ignore
    price_entries: List[data.Price] = []  # type: ignore

    for entry in entries:
        if not isinstance(entry, data.Transaction):
            continue

        for posting in entry.postings:
            if posting.account not in config.assets_account:
                continue

            if not (posting.meta and "useful_life" in posting.meta):
                continue

            new_entries, new_prices = process_fixed_asset_posting(
                entry, posting, config
            )

            if new_entries:
                depreciation_entries.extend(new_entries)
                price_entries.extend(new_prices)

    return depreciation_entries, price_entries


if __name__ == "__main__":
    entries, _, _ = load_file("main.bean")
    depreciation_entries, price_entries = auto_depreciation(
        entries,
        None,
        {
            "expenses": "Expenses:Depreciation",
            "assets": [
                "Assets:Long:Fixed:Car",
                "Assets:Long:Fixed:Digital",
                "Assets:Long:Fixed:Equipments",
            ],
        },
    )

    if depreciation_entries:
        print_entries(depreciation_entries)
    if price_entries:
        print_entries(price_entries)
