from beancount.core.data import Directive

from doujia.post_processor.truncate_meta import truncate_meta


# 测试在 balance 之前的三行数据
def test_truncate_meta(entries: list[Directive]):  # type: ignore
    """
    @@@/main.bean
    2024-11-12 open Liabilities:Short:CreditCard:CMB
    2024-11-12 open Expenses:Living:Transportation
    2024-11-12 * "嘀嘀" "打车"
        time: "08:09:45"
        card: "5384"
        uniqueNo: "CMB_WLXTAN11050X7090000CAAIZ"
        Liabilities:Short:CreditCard:CMB                                                  -1.50 CNY
        Expenses:Living:Transportation                                                     1.50 CNY
    2024-11-13 balance Liabilities:Short:CreditCard:CMB -1.50 CNY
    """

    truncate_meta(entries)

    with open("main.bean", "r", encoding="utf-8") as f:
        actual = f.read()

    assert (
        actual
        == """2024-11-12 open Liabilities:Short:CreditCard:CMB
2024-11-12 open Expenses:Living:Transportation
2024-11-12 * "嘀嘀" "打车"
    Liabilities:Short:CreditCard:CMB                                                  -1.50 CNY
    Expenses:Living:Transportation                                                     1.50 CNY
2024-11-13 balance Liabilities:Short:CreditCard:CMB -1.50 CNY"""
    )


# 测试在 balance 之后的三行数据
def test_truncate_meta_2(entries: list[Directive]):  # type: ignore
    """
    @@@/main.bean
    2024-11-12 open Liabilities:Short:CreditCard:CMB
    2024-11-12 open Expenses:Living:Transportation
    2024-11-12 * "嘀嘀" "打车"
        time: "08:09:45"
        card: "5384"
        uniqueNo: "CMB_WLXTAN11050X7090000CAAIZ"
        Liabilities:Short:CreditCard:CMB                                                  -1.50 CNY
        Expenses:Living:Transportation                                                     1.50 CNY
    2024-11-13 balance Liabilities:Short:CreditCard:CMB -1.50 CNY
    2024-11-13 * "嘀嘀" "打车"
        time: "08:09:45"
        card: "5384"
        uniqueNo: "CMB_WLXTAN11050X7090000CAAIZ"
        Liabilities:Short:CreditCard:CMB                                                  -1.50 CNY
        Expenses:Living:Transportation                                                     1.50 CNY
    """

    truncate_meta(entries)

    with open("main.bean", "r", encoding="utf-8") as f:
        actual = f.read()

    assert (
        actual
        == """2024-11-12 open Liabilities:Short:CreditCard:CMB
2024-11-12 open Expenses:Living:Transportation
2024-11-12 * "嘀嘀" "打车"
    Liabilities:Short:CreditCard:CMB                                                  -1.50 CNY
    Expenses:Living:Transportation                                                     1.50 CNY
2024-11-13 balance Liabilities:Short:CreditCard:CMB -1.50 CNY
2024-11-13 * "嘀嘀" "打车"
    time: "08:09:45"
    card: "5384"
    uniqueNo: "CMB_WLXTAN11050X7090000CAAIZ"
    Liabilities:Short:CreditCard:CMB                                                  -1.50 CNY
    Expenses:Living:Transportation                                                     1.50 CNY"""
    )


# 测试在 balance 之后的三行数据
def test_truncate_meta_for_multiple_account(entries: list[Directive]):  # type: ignore
    """
    @@@/main.bean
    2024-11-12 open Liabilities:Short:CreditCard:CMB
    2024-11-12 open Liabilities:Short:CreditCard:HSBC
    2024-11-12 open Expenses:Living:Transportation
    2024-11-12 * "嘀嘀" "打车"
        time: "08:09:45"
        card: "5384"
        uniqueNo: "CMB_WLXTAN11050X7090000CAAIZ"
        Liabilities:Short:CreditCard:CMB                                                  -1.50 CNY
        Expenses:Living:Transportation                                                     1.50 CNY
    2024-11-12 * "嘀嘀" "打车"
        time: "08:09:45"
        card: "5384"
        uniqueNo: "HSBC_WLXTAN11050X7090000CAAIZ"
        Liabilities:Short:CreditCard:HSBC                                                  -1.50 CNY
        Expenses:Living:Transportation                                                     1.50 CNY
    2024-11-13 balance Liabilities:Short:CreditCard:CMB -1.50 CNY
    """

    truncate_meta(entries)

    with open("main.bean", "r", encoding="utf-8") as f:
        actual = f.read()

    assert (
        actual
        == """2024-11-12 open Liabilities:Short:CreditCard:CMB
2024-11-12 open Liabilities:Short:CreditCard:HSBC
2024-11-12 open Expenses:Living:Transportation
2024-11-12 * "嘀嘀" "打车"
    Liabilities:Short:CreditCard:CMB                                                  -1.50 CNY
    Expenses:Living:Transportation                                                     1.50 CNY
2024-11-12 * "嘀嘀" "打车"
    time: "08:09:45"
    card: "5384"
    uniqueNo: "HSBC_WLXTAN11050X7090000CAAIZ"
    Liabilities:Short:CreditCard:HSBC                                                  -1.50 CNY
    Expenses:Living:Transportation                                                     1.50 CNY
2024-11-13 balance Liabilities:Short:CreditCard:CMB -1.50 CNY"""
    )
