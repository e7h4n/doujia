"""合成器代码测试"""

import io
from datetime import date
from textwrap import dedent
from beancount.parser import printer
from beancount.parser.parser import parse_string
from doujia.post_processor.merger import (
    _find_insert_position,
    _merge_beancount_content,
    _merge_beancount_file,
    _find_balance_insert_position,
)


def unify_content(entry_content: str):
    entries, _, _ = parse_string(dedent(entry_content))
    return "\n".join([printer.format_entry(x) for x in entries])


# 一个工具函数，去掉一个字符串的行尾空格
def remove_trailing_whitespace(text: str) -> str:
    return "\n".join([x.rstrip() for x in text.splitlines()])


def test_merge_beancount_entries(doc_fs_ledger_filename):  # 测试记录导入
    """
    @@@/main.bean
    2023-03-19 balance Liabilities:CreditCard:CMB 0.00 CNY
    2023-03-19 balance Assets:Current:CMB 0.00 CNY

    2023-03-19 * "美团单车" "自行车"
      Liabilities:CreditCard:CMB -1.50 CNY
      Expenses:Living:Transportation

    2023-03-20 balance Liabilities:CreditCard:CMB -0.00 CNY
    2023-03-20 balance Assets:Current:CMS 0.00 CNY

    @@@/imported_content.bean
    2023-03-19 ! "快捷支付" "张小龙"
      Assets:Current:CMB -28.40 CNY
      Equity:UFO

    2023-03-20 balance Assets:Current:CMB 0.00 CNY

    2023-03-20 * "饿了么" "早餐午餐晚餐"
      Liabilities:CreditCard:CMB -33.00 CNY
      Expenses:Living:Meal:Restaurant

    2023-03-21 balance Liabilities:CreditCard:CMB -0.00 CNY

    """

    output = io.StringIO()
    _merge_beancount_file(
        doc_fs_ledger_filename,
        "/imported_content.bean",
        output,
    )

    actual = unify_content(output.getvalue())
    expect = unify_content(
        """
        2023-03-19 balance Liabilities:CreditCard:CMB 0.00 CNY
        2023-03-19 balance Assets:Current:CMB 0.00 CNY

        2023-03-19 * "美团单车" "自行车"
          Liabilities:CreditCard:CMB -1.50 CNY
          Expenses:Living:Transportation

        2023-03-19 ! "快捷支付" "张小龙"
          Assets:Current:CMB  -28.40 CNY
          Equity:UFO

        2023-03-20 balance Liabilities:CreditCard:CMB -0.00 CNY
        2023-03-20 balance Assets:Current:CMS 0.00 CNY
        2023-03-20 balance Assets:Current:CMB                              0.00 CNY

        2023-03-20 * "饿了么" "早餐午餐晚餐"
          Liabilities:CreditCard:CMB       -33.00 CNY
          Expenses:Living:Meal:Restaurant

        2023-03-21 balance Liabilities:CreditCard:CMB                      0.00 CNY
    """
    )

    assert actual == expect


def test_merge_beancount_entries_1():
    output = io.StringIO()

    _merge_beancount_content(
        """1970-01-01 open A:Foo
1970-01-01 open A:Bar
2024-01-29 balance A:Foo 1.00 CNY

2024-01-29 *
    A:Foo -1.00 CNY
    A:Bar
""",
        """2024-01-29 *
    A:Foo -2.00 CNY
    A:Bar

2024-01-30 *
    A:Foo -3.00 CNY
    A:Bar
""",
        output,
    )

    assert unify_content(output.getvalue()) == unify_content(
        """
    1970-01-01 open A:Foo
    1970-01-01 open A:Bar
    2024-01-29 balance A:Foo 1.00 CNY

    2024-01-29 *
        A:Foo -1.00 CNY
        A:Bar

    2024-01-29 *
      A:Foo  -2.00 CNY
      A:Bar

    2024-01-30 *
      A:Foo  -3.00 CNY
      A:Bar
    """
    )


def test_merge_beancount_entries_2():
    output = io.StringIO()

    _merge_beancount_content(
        """2024-01-01 balance A:Foo 1.00 CNY

2024-01-29 balance A:Foo 1.00 CNY

2024-01-29 *
    A:Foo -1.00 CNY
    A:Bar
""",
        """
2024-01-30 *
    A:Foo -3.10 CNY
    A:Bar

2024-01-30 *
    A:Foo -3.20 CNY
    A:Bar

2024-01-29 *
    A:Foo -2.10 CNY
    A:Bar

2024-01-29 *
    A:Foo -2.20 CNY
    A:Bar""",
        output,
    )

    result = remove_trailing_whitespace(output.getvalue())
    assert (
        result
        == """2024-01-01 balance A:Foo 1.00 CNY

2024-01-29 balance A:Foo 1.00 CNY

2024-01-29 *
    A:Foo -1.00 CNY
    A:Bar

2024-01-29 *
  A:Foo  -2.20 CNY
  A:Bar

2024-01-29 *
  A:Foo  -2.10 CNY
  A:Bar

2024-01-30 *
  A:Foo  -3.20 CNY
  A:Bar

2024-01-30 *
  A:Foo  -3.10 CNY
  A:Bar"""
    )


def test_merge_beancount_entries_3():
    """测试记录导入"""

    output = io.StringIO()
    _merge_beancount_content(
        """2024-01-01 balance Assets:CMS 0.00 CNY

2024-01-02 *
    Assets:CMS -1.00 CNY
    Equity:UFO
""",
        """2024-01-02 *
    Assets:CMS -2.00 CNY
    Equity:UFO
""",
        output,
    )

    assert (
        remove_trailing_whitespace(output.getvalue())
        == """2024-01-01 balance Assets:CMS 0.00 CNY

2024-01-02 *
    Assets:CMS -1.00 CNY
    Equity:UFO

2024-01-02 *
  Assets:CMS  -2.00 CNY
  Equity:UFO"""
    )


def test_merge_beancount_entries_4():
    """测试记录导入"""

    output = io.StringIO()
    _merge_beancount_content(
        """
2024-01-01 *
    Assets:CMS -1.00 CNY
    Equity:UFO

2024-01-20 balance Assets:CMS 0.00 CNY
""",
        """2024-01-30 *
    Assets:CMS -2.00 CNY
    Equity:UFO
""",
        output,
    )

    assert (
        remove_trailing_whitespace(output.getvalue())
        == """
2024-01-01 *
    Assets:CMS -1.00 CNY
    Equity:UFO

2024-01-20 balance Assets:CMS 0.00 CNY

2024-01-30 *
  Assets:CMS  -2.00 CNY
  Equity:UFO"""
    )


def test_merge_beancount_entries_5():
    """测试记录导入，导入的记录大于已经存在的所有时间"""

    output = io.StringIO()
    _merge_beancount_content(
        """
2024-01-01 *
    Assets:CMS -1.00 CNY
    Equity:UFO

2024-01-20 *
    Assets:CMS -1.00 CNY
    Equity:UFO

""",
        """2024-01-30 *
    Assets:CMS -2.00 CNY
    Equity:UFO
""",
        output,
    )

    assert (
        remove_trailing_whitespace(output.getvalue())
        == """
2024-01-01 *
    Assets:CMS -1.00 CNY
    Equity:UFO

2024-01-20 *
    Assets:CMS -1.00 CNY
    Equity:UFO

2024-01-30 *
  Assets:CMS  -2.00 CNY
  Equity:UFO"""
    )


def test_merge_insert_position_future_date():
    """测试插入位置，插入一个未来的时间"""

    lines = [
        "2023-03-19 balance Liabilities:CreditCard:CMB 0.00 CNY",
        "2023-03-19 balance Assets:Current:CMB 0.00 CNY",
        "",
        '2023-03-19 * "美团单车" "自行车"',
        "    Liabilities:CreditCard:CMB -1.50 CNY",
        "    Expenses:Living:Transportation",
        "",
        "2023-03-20 balance Liabilities:CreditCard:CMB -0.00 CNY",
        "2023-03-20 balance Assets:Current:CMS 0.00 CNY",
    ]

    assert _find_insert_position(lines, len(lines), date(2023, 3, 31)) == len(lines)


def test_merge_insert_position_prev_date():
    """测试插入位置，插入上一个交易日的记录"""

    lines = [
        "2023-03-19 balance Liabilities:CreditCard:CMB 0.00 CNY",
        "2023-03-19 balance Assets:Current:CMB 0.00 CNY",
        "",
        '2023-03-19 * "美团单车" "自行车"',
        "    Liabilities:CreditCard:CMB -1.50 CNY",
        "    Expenses:Living:Transportation",
        "",
        "2023-03-20 balance Liabilities:CreditCard:CMB -0.00 CNY",
        "2023-03-20 balance Assets:Current:CMS 0.00 CNY",
    ]

    assert _find_insert_position(lines, len(lines), date(2023, 3, 18)) == 0


def test_merge_insert_position_next_date():
    """测试插入位置，查找后一天的位置"""

    lines = [
        "2023-03-19 balance Liabilities:CreditCard:CMB 0.00 CNY",
        "2023-03-19 balance Assets:Current:CMB 0.00 CNY",
        "",
        '2023-03-19 * "美团单车" "自行车"',
        "    Liabilities:CreditCard:CMB -1.50 CNY",
        "    Expenses:Living:Transportation",
        "",
        "2023-03-20 balance Liabilities:CreditCard:CMB -0.00 CNY",
        "2023-03-20 balance Assets:Current:CMS 0.00 CNY",
    ]

    assert _find_insert_position(lines, len(lines) - 1, date(2023, 3, 21)) == len(lines)


def test_merge_insert_position_unexisted_next_date():
    """测试插入位置，查找后一天的位置"""

    lines = [
        "2023-03-19 balance Liabilities:CreditCard:CMB 0.00 CNY",
        "2023-03-19 balance Assets:Current:CMB 0.00 CNY",
        "",
        '2023-03-19 * "美团单车" "自行车"',
        "    Liabilities:CreditCard:CMB -1.50 CNY",
        "    Expenses:Living:Transportation",
    ]

    assert _find_insert_position(lines, len(lines) - 1, date(2023, 3, 21)) == len(lines)


def test_merge_insert_position_unexisted_middle_date():
    """测试插入位置，查找其中一天的位置"""

    lines = [
        "2023-03-19 balance Liabilities:CreditCard:CMB 0.00 CNY",
        "2023-03-19 balance Assets:Current:CMB 0.00 CNY",
        "",
        '2023-03-19 * "美团单车" "自行车"',
        "    Liabilities:CreditCard:CMB -1.50 CNY",
        "    Expenses:Living:Transportation",
        "2023-03-23 balance Assets:Current:CMB 0.00 CNY",
        "",
    ]

    assert _find_insert_position(lines, len(lines) - 1, date(2023, 3, 21)) == 6


def test_merge_insert_position_existed_balance():
    """测试插入位置，查找已经存在 balance 的日期"""

    lines = [
        "2023-03-19 balance Liabilities:CreditCard:CMB 0.00 CNY",
        "2023-03-19 balance Assets:Current:CMB 0.00 CNY",
        "",
        '2023-03-19 * "美团单车" "自行车"',
        "    Liabilities:CreditCard:CMB -1.50 CNY",
        "    Expenses:Living:Transportation",
        "",
        "2023-03-20 balance Liabilities:CreditCard:CMB -0.00 CNY",
        "2023-03-20 balance Assets:Current:CMS 0.00 CNY",
    ]

    assert _find_insert_position(lines, len(lines) - 1, date(2023, 3, 20)) == len(lines)


def test_merge_insert_position_existed_date():
    """测试插入位置，同一天的记录应该追加在最后"""

    lines = [
        "2023-03-19 balance Liabilities:CreditCard:CMB 0.00 CNY",
        "2023-03-19 balance Assets:Current:CMB 0.00 CNY",
        "",
        '2023-03-19 * "美团单车" "自行车"',
        "    Liabilities:CreditCard:CMB -1.50 CNY",
        "    Expenses:Living:Transportation",
        "",
        "2023-03-20 balance Liabilities:CreditCard:CMB -0.00 CNY",
        "2023-03-20 balance Assets:Current:CMS 0.00 CNY",
    ]

    assert _find_insert_position(lines, len(lines) - 1, date(2023, 3, 19)) == 7


def test_find_balance_insert_position():
    lines = """
2023-03-19 balance Liabilities:CreditCard:CMB 0.00 CNY
2023-03-19 balance Assets:Current:CMB 0.00 CNY

2023-03-19 * "美团单车" "自行车"
  Liabilities:CreditCard:CMB -1.50 CNY
  Expenses:Living:Transportation

2023-03-20 balance Liabilities:CreditCard:CMB -0.00 CNY
2023-03-20 balance Assets:Current:CMS 0.00 CNY
2023-03-21 balance Liabilities:CreditCard:CMB                      0.00 CNY
""".split(
        "\n"
    )

    assert _find_balance_insert_position(lines, len(lines), date(2023, 3, 20)) == 10


def test_find_transaction_insert_position():
    lines = """
2023-03-19 balance Liabilities:CreditCard:CMB 0.00 CNY
2023-03-19 balance Assets:Current:CMB 0.00 CNY

2023-03-19 * "美团单车" "自行车"
  Liabilities:CreditCard:CMB -1.50 CNY
  Expenses:Living:Transportation

2023-03-20 balance Liabilities:CreditCard:CMB -0.00 CNY
2023-03-20 balance Assets:Current:CMS 0.00 CNY
2023-03-21 balance Liabilities:CreditCard:CMB                      0.00 CNY
""".split(
        "\n"
    )

    assert _find_insert_position(lines, len(lines), date(2023, 3, 20)) == 10
