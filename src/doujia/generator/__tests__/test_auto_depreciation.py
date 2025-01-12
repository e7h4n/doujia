from datetime import date
from decimal import Decimal

from beancount.core import data
from beancount.core.data import Directive
from beancount.core.number import D

from doujia.generator.auto_depreciation import (
    auto_depreciation,
    calculate_linear_value,
    calculate_parabola_value,
)


def test_auto_depreciation(entries: list[Directive]):  # type: ignore
    """
    @@@/main.bean
    2024-03-05 open Assets:Long:Fixed:Digital
    2024-03-05 open Liabilities:CreditCard:CMB
    2024-03-05 * "Sony A7C2"
      Liabilities:CreditCard:CMB -13,993.00 CNY
      Assets:Long:Fixed:Digital 1.00 SONY.A7C2 { 13,993.00 CNY }
        useful_life: "36m"
        residual_value: 8395.8
    """

    depreciation_entries, price_entries = auto_depreciation(
        entries,
        None,
        {
            "expenses": "Expenses:Depreciation",
            "assets": [
                "Assets:Long:Fixed:Digital",
            ],
        },
    )

    # 验证生成了折旧分录
    assert len(depreciation_entries) == 36  # 36个月的折旧分录

    # 验证价格分录
    assert len(price_entries) == 36

    first_price = price_entries[0]
    assert isinstance(first_price, data.Price)
    assert first_price.date == date(2024, 4, 5)
    assert first_price.currency == "SONY.A7C2"
    assert first_price.amount.currency == "CNY"
    assert abs(first_price.amount.number - D("13681")) < D("0.01")

    last_price = price_entries[-1]
    assert isinstance(last_price, data.Price)
    assert last_price.date == date(2027, 3, 5)
    assert last_price.currency == "SONY.A7C2"
    assert last_price.amount.currency == "CNY"
    assert abs(last_price.amount.number - D("8395.8")) < D("1")

    # 验证第一个月的折旧分录
    first_entry = depreciation_entries[0]
    assert isinstance(first_entry, data.Transaction)
    assert first_entry.date == date(2024, 4, 5)
    assert first_entry.narration == "Sony A7C2 自动折旧"
    assert len(first_entry.postings) == 3

    # 验证折旧金额
    posting = first_entry.postings[2]  # 第三个posting是折旧费用
    assert posting.account == "Expenses:Depreciation"
    assert posting.units.currency == "CNY"
    assert posting.units.number == D("13993") - first_price.amount.number


def test_calculate_parabola_value():
    """测试抛物线折旧算法"""
    start_value = 10000
    end_value = 4000
    days = 100

    # 测试起始点
    assert calculate_parabola_value(0, start_value, end_value, days) == start_value

    # 测试中间点
    mid_value = calculate_parabola_value(50, start_value, end_value, days)
    assert mid_value < start_value
    assert mid_value > end_value

    # 测试终点
    final_value = calculate_parabola_value(days, start_value, end_value, days)
    assert abs(final_value - end_value) <= 1  # 允许1的误差


def test_calculate_linear_value():
    """测试线性折旧算法"""
    start_value = 10000
    end_value = 4000
    days = 100

    # 测试起始点
    assert calculate_linear_value(0, start_value, end_value, days) == start_value

    # 测试中间点
    mid_value = calculate_linear_value(50, start_value, end_value, days)
    expected_mid = (start_value + end_value) / 2
    assert abs(mid_value - expected_mid) <= 1  # 允许1的误差

    # 测试终点
    final_value = calculate_linear_value(days, start_value, end_value, days)
    assert abs(final_value - end_value) <= 1  # 允许1的误差
