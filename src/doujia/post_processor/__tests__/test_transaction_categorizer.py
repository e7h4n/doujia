"""测试文件自动分类器"""

import io

from beancount.parser import parser

from doujia.post_processor.transaction_categorizer import (
    Rule,
    _apply_rule_to_transaction,
    _is_transaction_matching_rule,
    _parse_beancount_converter_dsl,
    _process_beancount,
)

# 用于测试的 Beancount 事务
BEANCOUNT_EXAMPLE = """
2021-08-04 * "Tencent - Purchase" ""
  Assets:Checking:Bank      -3.14 CNY
  Equity:UFO
"""

# 用于测试的自动分类规则
RULE_DSL = """
Assets:Expenses:Example
  "Tencent - Purchase" -> payee "Tencent" narration "Example Expense" flag "!"
"""


def test_rule_init():
    """测试 Rule 类"""

    rule = Rule(
        "Assets:Expenses:Example",
        {"summary": "Tencent - Purchase"},
        {"payee": "Tencent"},
    )
    assert rule.account == "Assets:Expenses:Example"
    assert rule.matcher == {"summary": "Tencent - Purchase"}
    assert rule.target == {"payee": "Tencent"}


def test_parse_beancount_converter_dsl():
    """测试解析 DSL"""

    rules = _parse_beancount_converter_dsl(RULE_DSL)
    assert len(rules) == 1
    assert rules[0].account == "Assets:Expenses:Example"
    assert rules[0].matcher == {"summary": "Tencent - Purchase", "amount": None}
    assert rules[0].target == {
        "payee": "Tencent",
        "narration": "Example Expense",
        "flag": "!",
    }


def test_is_transaction_matching_rule():
    """测试事务与规则的匹配"""

    rules = _parse_beancount_converter_dsl(RULE_DSL)
    transaction = parser.parse_string(BEANCOUNT_EXAMPLE)[0][0]
    assert _is_transaction_matching_rule(transaction, rules[0])


def test_apply_rule_to_transaction():
    """测试应用规则到事务"""

    rules = _parse_beancount_converter_dsl(RULE_DSL)
    transaction = parser.parse_string(BEANCOUNT_EXAMPLE)[0][0]
    modified_transaction = _apply_rule_to_transaction(transaction, rules[0])
    assert modified_transaction.payee == "Tencent"
    assert modified_transaction.narration == "Example Expense"
    assert modified_transaction.flag == "!"
    assert modified_transaction.postings[1].account == "Assets:Expenses:Example"


def test_process_beancount():
    """测试整个处理流程"""

    rules = _parse_beancount_converter_dsl(
        """
Assets:Expenses:Example
    "Tencent - Purchase" -> payee "Tencent" narration "Example Expense" flag "!"
"""
    )
    output_buffer = io.StringIO()

    _process_beancount(
        """
2021-08-04 * "Tencent - Purchase" ""
    Assets:Checking:Bank      -3.14 CNY
    Equity:UFO
""",
        rules,
        output_buffer,
    )

    expected = """2021-08-04 ! "Tencent" "Example Expense"
  Assets:Checking:Bank     -3.14 CNY
  Assets:Expenses:Example

"""

    assert output_buffer.getvalue() == expected


def test_process_beancount_with_amount_matching():
    """测试整个处理流程，包括匹配金额"""

    rules = _parse_beancount_converter_dsl(
        """
Assets:Expenses:Example
    "Tencent - Purchase", amount -3.14 -> payee "Tencent" narration "Example Expense"
"""
    )
    output_buffer = io.StringIO()

    _process_beancount(
        """
2021-08-04 * "Tencent - Purchase" ""
    Assets:Checking:Bank      -3.14 CNY
    Equity:UFO
""",
        rules,
        output_buffer,
    )

    expected = """2021-08-04 * "Tencent" "Example Expense"
  Assets:Checking:Bank     -3.14 CNY
  Assets:Expenses:Example

"""

    assert output_buffer.getvalue() == expected


def test_process_beancount_with_amount_not_matching():
    """测试整个处理流程，当金额不匹配时，规则不会被应用"""

    rules = _parse_beancount_converter_dsl(
        """
Assets:Expenses:Example
    "Tencent - Purchase", amount -3.15 -> payee "Tencent" narration "Example Expense"
"""
    )
    output_buffer = io.StringIO()

    _process_beancount(
        """
2021-08-04 * "Tencent - Purchase" ""
    Assets:Checking:Bank      -3.14 CNY
    Equity:UFO
""",
        rules,
        output_buffer,
    )

    expected = """2021-08-04 * "Tencent - Purchase" ""
  Assets:Checking:Bank  -3.14 CNY
  Equity:UFO

"""

    assert output_buffer.getvalue() == expected


def test_process_beancount_with_balance():
    """测试整个处理流程，包括处理 Balance"""

    rules = _parse_beancount_converter_dsl(
        """
Assets:Expenses:Example
    "Tencent - Purchase" -> payee "Tencent" narration "Example Expense"
"""
    )
    output_buffer = io.StringIO()

    _process_beancount(
        """
2021-08-04 * "Tencent - Purchase" ""
    Assets:Checking:Bank      -3.14 CNY
    Equity:UFO

2021-08-05 balance Assets:Checking:Bank      100.00 CNY
""",
        rules,
        output_buffer,
    )

    expected = """2021-08-04 * "Tencent" "Example Expense"
  Assets:Checking:Bank     -3.14 CNY
  Assets:Expenses:Example

2021-08-05 balance Assets:Checking:Bank                            100.00 CNY

"""

    assert output_buffer.getvalue() == expected


def test_parse_beancount_converter_dsl_without_empty_lines():
    """测试解析不带空行的 beancount converter DSL"""

    rules = _parse_beancount_converter_dsl(
        """
Assets:Expenses:Example
    "Tencent - Purchase" -> payee "Tencent" narration "Example Expense"

Assets:Expenses:Another
    "Alipay - Payment" -> payee "Alipay" narration "Another Expense"
"""
    )

    expected_rules = [
        Rule(
            account="Assets:Expenses:Example",
            matcher={"summary": "Tencent - Purchase", "amount": None},
            target={
                "payee": "Tencent",
                "narration": "Example Expense",
                "flag": None,
            },
        ),
        Rule(
            account="Assets:Expenses:Another",
            matcher={"summary": "Alipay - Payment", "amount": None},
            target={
                "payee": "Alipay",
                "narration": "Another Expense",
                "flag": None,
            },
        ),
    ]

    assert rules[0] == expected_rules[0]


def test_process_beancount_with_summary_not_match():
    rules = _parse_beancount_converter_dsl(
        """
Assets:Expenses:Example
    "Tencent - Purchase", amount -3.14 -> payee "Tencent" narration "Example Expense"
"""
    )
    output_buffer = io.StringIO()

    _process_beancount(
        """
2021-08-04 * "Tencent - not match" ""
    Assets:Checking:Bank      -3.14 CNY
    Equity:UFO
""",
        rules,
        output_buffer,
    )

    expected = """2021-08-04 * "Tencent - not match" ""
  Assets:Checking:Bank  -3.14 CNY
  Equity:UFO

"""

    assert output_buffer.getvalue() == expected
