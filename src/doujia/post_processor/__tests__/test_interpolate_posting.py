from beancount.core.data import Directive

from doujia.post_processor.interpolate_posting import interpolate_postings


# 测试补全 posting 中的记录
def test_posting_filler(entries: list[Directive]):  # type: ignore
    """
    @@@/main.bean

    2024-11-11 open Liabilities:Short:CreditCard:CMB
    2024-11-11 open Expenses:Health
    2024-11-11 * "好大夫在线" "挂号"
      Liabilities:Short:CreditCard:CMB -512.00 CNY
      Expenses:Health
    """

    interpolate_postings(entries)

    with open("main.bean", "r", encoding="utf-8") as f:
        actual = f.read()

    assert (
        actual
        == """
2024-11-11 open Liabilities:Short:CreditCard:CMB
2024-11-11 open Expenses:Health
2024-11-11 * "好大夫在线" "挂号"
  Liabilities:Short:CreditCard:CMB -512.00 CNY
  Expenses:Health 512.00 CNY
"""
    )


# 测试补全多个记录
def test_posting_filler_multiple_entries(entries: list[Directive]):  # type: ignore
    """
    @@@/main.bean

    2024-11-11 open Liabilities:Short:CreditCard:CMB
    2024-11-11 open Expenses:Health
    2024-11-11 * "好大夫在线" "挂号"
      Liabilities:Short:CreditCard:CMB -512.00 CNY
      Expenses:Health

    2024-11-11 * "京东" "买菜"
      Liabilities:Short:CreditCard:CMB -100 CNY
      Expenses:Food
    """

    interpolate_postings(entries)

    with open("main.bean", "r", encoding="utf-8") as f:
        actual = f.read()

    assert (
        actual
        == """
2024-11-11 open Liabilities:Short:CreditCard:CMB
2024-11-11 open Expenses:Health
2024-11-11 * "好大夫在线" "挂号"
  Liabilities:Short:CreditCard:CMB -512.00 CNY
  Expenses:Health 512.00 CNY

2024-11-11 * "京东" "买菜"
  Liabilities:Short:CreditCard:CMB -100 CNY
  Expenses:Food 100 CNY
"""
    )


# 测试补全多个多行记录
def test_posting_filler_multiple_entries_multiline(entries: list[Directive]):  # type: ignore
    """
    @@@/main.bean

    2024-11-11 open Liabilities:Short:CreditCard:CMB
    2024-11-11 open Expenses:Health
    2024-11-11 * "好大夫在线" "挂号"
      Liabilities:Short:CreditCard:CMB -512.00 CNY
      Liabilities:Short:CreditCard:CMB -100.00 CNY
      Expenses:Health

    2024-11-11 * "京东" "买菜"
      Liabilities:Short:CreditCard:CMB -100 CNY
      Expenses:Food
    """

    interpolate_postings(entries)

    with open("main.bean", "r", encoding="utf-8") as f:
        actual = f.read()

    assert (
        actual
        == """
2024-11-11 open Liabilities:Short:CreditCard:CMB
2024-11-11 open Expenses:Health
2024-11-11 * "好大夫在线" "挂号"
  Liabilities:Short:CreditCard:CMB -512.00 CNY
  Liabilities:Short:CreditCard:CMB -100.00 CNY
  Expenses:Health 612.00 CNY

2024-11-11 * "京东" "买菜"
  Liabilities:Short:CreditCard:CMB -100 CNY
  Expenses:Food 100 CNY
"""
    )


# 测试补全多个多行记录场景2
def test_posting_filler_multiple_entries_multiline_2(entries: list[Directive]):  # type: ignore
    """
    @@@/main.bean

    2024-11-11 open Liabilities:Short:CreditCard:CMB
    2024-11-11 open Expenses:Health
    2024-11-11 * "好大夫在线" "挂号"
      Liabilities:Short:CreditCard:CMB -512.00 CNY
      Expenses:Health 512.00 CNY
      Liabilities:Short:CreditCard:CMB -100.00 CNY
      Expenses:Health

    2024-11-11 * "京东" "买菜"
      Liabilities:Short:CreditCard:CMB -100 CNY
      Expenses:Food
    """

    interpolate_postings(entries)

    with open("main.bean", "r", encoding="utf-8") as f:
        actual = f.read()

    assert (
        actual
        == """
2024-11-11 open Liabilities:Short:CreditCard:CMB
2024-11-11 open Expenses:Health
2024-11-11 * "好大夫在线" "挂号"
  Liabilities:Short:CreditCard:CMB -512.00 CNY
  Expenses:Health 512.00 CNY
  Liabilities:Short:CreditCard:CMB -100.00 CNY
  Expenses:Health 100.00 CNY

2024-11-11 * "京东" "买菜"
  Liabilities:Short:CreditCard:CMB -100 CNY
  Expenses:Food 100 CNY
"""
    )


# 测试补全多个多行记录场景3
def test_posting_filler_multiple_entries_multiline_3(entries: list[Directive]):  # type: ignore
    """
    @@@/main.bean

    2024-11-11 open Assets:Stock "FIFO"
    2024-11-11 open Assets:Cash
    2024-11-11 open Income:PnL
    2024-11-11 *
      Assets:Stock 1 AAPL { 1 USD }
      Assets:Stock 1 AAPL { 1.5 USD }
      Assets:Cash

    2024-11-11 *
      Assets:Stock -2 AAPL {} @ 2 USD
      Assets:Cash 4 USD
      Income:PnL
    """

    interpolate_postings(entries)

    with open("main.bean", "r", encoding="utf-8") as f:
        actual = f.read()

    assert (
        actual
        == """
2024-11-11 open Assets:Stock "FIFO"
2024-11-11 open Assets:Cash
2024-11-11 open Income:PnL
2024-11-11 *
  Assets:Stock 1 AAPL { 1 USD }
  Assets:Stock 1 AAPL { 1.5 USD }
  Assets:Cash -2.5 USD

2024-11-11 *
  Assets:Stock -2 AAPL {} @ 2 USD
  Assets:Cash 4 USD
  Income:PnL -1.5 USD
"""
    )


# 补全场景下带注释和 meta 的情况
def test_posting_filler_multiple_entries_with_comment(entries: list[Directive]):  # type: ignore
    """
    @@@/main.bean

    2024-11-11 open Assets:Stock "FIFO"
    2024-11-11 open Assets:Cash
    2024-11-11 open Income:PnL
    2024-11-11 * ; BUY AAPL
      broker: "IBKR"
      Assets:Stock 1 AAPL { 1 USD }
      Assets:Stock 1 AAPL { 1.5 USD }
      Assets:Cash
    """

    interpolate_postings(entries)

    with open("main.bean", "r", encoding="utf-8") as f:
        actual = f.read()

    assert (
        actual
        == """
2024-11-11 open Assets:Stock "FIFO"
2024-11-11 open Assets:Cash
2024-11-11 open Income:PnL
2024-11-11 * ; BUY AAPL
  broker: "IBKR"
  Assets:Stock 1 AAPL { 1 USD }
  Assets:Stock 1 AAPL { 1.5 USD }
  Assets:Cash -2.5 USD
"""
    )


# 补全存在文件 include 的场景
def test_posting_filler_multiple_entries_with_include(entries: list[Directive]):  # type: ignore
    """
    @@@/main.bean
    include "ledger.bean"

    @@@/ledger.bean

    2024-11-11 open Assets:Stock "FIFO"
    2024-11-11 open Assets:Cash
    2024-11-11 open Income:PnL
    2024-11-11 * ; BUY AAPL
      broker: "IBKR"
      Assets:Stock 1 AAPL { 1 USD }
      Assets:Stock 1 AAPL { 1.5 USD }
      Assets:Cash
    """

    interpolate_postings(entries)

    with open("ledger.bean", "r", encoding="utf-8") as f:
        actual = f.read()

    assert (
        actual
        == """
2024-11-11 open Assets:Stock "FIFO"
2024-11-11 open Assets:Cash
2024-11-11 open Income:PnL
2024-11-11 * ; BUY AAPL
  broker: "IBKR"
  Assets:Stock 1 AAPL { 1 USD }
  Assets:Stock 1 AAPL { 1.5 USD }
  Assets:Cash -2.5 USD
"""
    )


# 测试需要插入多条记录的场景
def test_posting_filler_multiple_entries_with_create_posting(entries: list[Directive]):  # type: ignore
    """
    @@@/main.bean

    2017-09-26 open Assets:Short:Stock:US:Current
    2017-09-26 open Expenses:Financing:Fee
    2017-09-26 * "IBKR" "手续费"
      Expenses:Financing:Fee 368.81 USD
      Expenses:Financing:Fee 313.73 HKD
      Assets:Short:Stock:US:Current
    """

    interpolate_postings(entries)

    with open("main.bean", "r", encoding="utf-8") as f:
        actual = f.read()

    assert (
        actual
        == """
2017-09-26 open Assets:Short:Stock:US:Current
2017-09-26 open Expenses:Financing:Fee
2017-09-26 * "IBKR" "手续费"
  Expenses:Financing:Fee 368.81 USD
  Expenses:Financing:Fee 313.73 HKD
  Assets:Short:Stock:US:Current -368.81 USD
  Assets:Short:Stock:US:Current -313.73 HKD
"""
    )


# 忽略 # 记录
def test_posting_filler_multiple_entries_with_hash_flag(entries: list[Directive]):  # type: ignore
    """
    @@@/main.bean

    2024-09-08 open Expenses:Education:Kid
    2024-09-08 # "妹妹兴趣班" "[MONTHLY REPEAT 4 TIMES]"
      Expenses:Education:Kid -1,280.00 CNY
      Expenses:Education:Kid
    """

    interpolate_postings(entries)

    with open("main.bean", "r", encoding="utf-8") as f:
        actual = f.read()

    assert (
        actual
        == """
2024-09-08 open Expenses:Education:Kid
2024-09-08 # "妹妹兴趣班" "[MONTHLY REPEAT 4 TIMES]"
  Expenses:Education:Kid -1,280.00 CNY
  Expenses:Education:Kid"""
    )
