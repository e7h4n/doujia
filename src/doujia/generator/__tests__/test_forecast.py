from textwrap import dedent
from typing import TypeVar

from beancount.core import data
from pyfakefs.fake_filesystem import FakeFilesystem

from doujia.generator.forecast import replace_forecast

Directive = TypeVar("Directive", bound=data.Directive)  # type: ignore


def test_forecast(entries: list[Directive], fs: FakeFilesystem):
    """
    @@@/main.bean
    2024-03-05 # "[MONTHLY REPEAT 6 TIMES]"
      Liabilities:CreditCard:CMB -100.00 CNY
      Assets:Long:Fixed:Digital
    """

    replace_forecast("main.bean", "forecast")

    assert fs.exists("forecast/Liabilities/CreditCard/CMB/2024-03-05.bean")
    with open("/main.bean") as f:
        content = f.read()
        assert (
            dedent(
                """include "forecast/Liabilities/CreditCard/CMB/2024-03-05.bean"
                """
            )
            == content
        )


def test_forecast_multiple(entries: list[Directive], fs: FakeFilesystem):
    """
    @@@/main.bean
    2024-03-05 # "[MONTHLY REPEAT 6 TIMES]"
      Liabilities:CreditCard:CMB -100.00 CNY
      Assets:Long:Fixed:Digital
    2022-03-05 # "[MONTHLY REPEAT 12 TIMES]"
      Liabilities:CreditCard:CMB -100.00 CNY
      Assets:Long:Fixed:Digital
    """

    replace_forecast("main.bean", "forecast")

    assert fs.exists("forecast/Liabilities/CreditCard/CMB/2024-03-05.bean")
    assert fs.exists("forecast/Liabilities/CreditCard/CMB/2022-03-05.bean")
    with open("/main.bean") as f:
        content = f.read()
        assert (
            """include "forecast/Liabilities/CreditCard/CMB/2024-03-05.bean"
include "forecast/Liabilities/CreditCard/CMB/2022-03-05.bean"
"""
        ) == content


def test_forecast_relative(entries: list[Directive], fs: FakeFilesystem):
    """
    @@@/main.bean
    include "ledgers/main.bean"

    @@@/ledgers/main.bean
    2024-03-05 # "[MONTHLY REPEAT 6 TIMES]"
      Liabilities:CreditCard:CMB -100.00 CNY
      Assets:Long:Fixed:Digital
    2022-03-05 # "[MONTHLY REPEAT 12 TIMES]"
      Liabilities:CreditCard:CMB -100.00 CNY
      Assets:Long:Fixed:Digital
    """

    replace_forecast("main.bean", "ledgers/forecast")

    assert fs.exists("ledgers/forecast/Liabilities/CreditCard/CMB/2024-03-05.bean")
    assert fs.exists("ledgers/forecast/Liabilities/CreditCard/CMB/2022-03-05.bean")
    with open("/ledgers/main.bean") as f:
        content = f.read()
        assert (
            """include "forecast/Liabilities/CreditCard/CMB/2024-03-05.bean"
include "forecast/Liabilities/CreditCard/CMB/2022-03-05.bean"
"""
        ) == content
