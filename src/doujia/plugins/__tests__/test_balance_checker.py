from beancount.parser import parser

from doujia.plugins.balance_checker import balance_checker


def test__find_first_unbalanced_entry():
    entries, options_map, _ = parser.parse_string(
        """
        2023-01-01 open Liability:CreditCard:CMB CNY
        2023-03-22 ! "尾号1089 消费 财付通-Creeper+Coffee" ""
  Liabilities:Short:CreditCard:CMB  -20.00 CNY
  Equity:UFO
  """
    )

    _, errors = balance_checker(
        entries, options_map, "{'Liabilities:Short:CreditCard:CMB': 'UNRESOLVED'}"
    )

    assert len(errors) == 1


# 找到当天的第一个
def test__find_first_unbalanced_entry_2():
    entries, options_map, _ = parser.parse_string(
        """
        2023-01-01 open Liability:CreditCard:CMB CNY
        2023-03-22 ! "尾号1089 消费 财付通-Creeper+Coffee" "" #UNRESOLVED
  Liabilities:Short:CreditCard:CMB  -20.00 CNY
  Equity:UFO

        2023-03-22 ! "尾号1089 消费 财付通-Creeper+Coffee" ""
  Liabilities:Short:CreditCard:CMB  -21.00 CNY
  Equity:UFO

        2023-03-22 ! "尾号1089 消费 财付通-Creeper+Coffee" "" #UNRESOLVED
  Liabilities:Short:CreditCard:CMB  -23.00 CNY
  Equity:UFO

  """
    )

    _, errors = balance_checker(
        entries, options_map, "{'Liabilities:Short:CreditCard:CMB': 'UNRESOLVED'}"
    )

    assert errors[0].source["lineno"] == 7


# 按照时间找到第一次出现的交易
def test__find_first_unbalanced_entry_3():
    entries, options_map, _ = parser.parse_string(
        """
        2023-01-01 open Liability:CreditCard:CMB CNY
        2023-03-22 ! "尾号1089 消费 财付通-Creeper+Coffee" "" #UNRESOLVED
  Liabilities:Short:CreditCard:CMB  -20.00 CNY
  Equity:UFO

        2023-03-22 ! "尾号1089 消费 财付通-Creeper+Coffee" ""
  Liabilities:Short:CreditCard:CMB  -21.00 CNY
  Equity:UFO

        2023-03-20 ! "尾号1089 消费 财付通-Creeper+Coffee" ""
  Liabilities:Short:CreditCard:CMB  -23.00 CNY
  Equity:UFO

  """
    )

    _, errors = balance_checker(
        entries, options_map, "{'Liabilities:Short:CreditCard:CMB': 'UNRESOLVED'}"
    )

    assert errors[0].source["lineno"] == 11


# 时间交错的 case
def test__find_first_unbalanced_entry_4():
    entries, options_map, _ = parser.parse_string(
        """
2023-01-01 open Assets:Receivables CNY
2023-01-02 *
  Assets:Receivables  1.00 CNY
  Equity:UFO

2023-01-03 * #UNRESOLVED
  Assets:Receivables  11.00 CNY
  Equity:UFO

2023-01-04 *
  Assets:Receivables  -1.00 CNY
  Equity:UFO

2023-01-04 *
  Assets:Receivables  -11.00 CNY
  Equity:UFO

2023-01-06 * #UNRESOLVED
  Assets:Receivables  -111.00 CNY
  Equity:UFO

  """
    )

    _, errors = balance_checker(
        entries, options_map, "{'Assets:Receivables': 'UNRESOLVED'}"
    )

    assert len(errors) == 1
    assert errors[0].source["lineno"] == 15
