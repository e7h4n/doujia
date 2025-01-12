from datetime import date
from beancount.core.data import Directive
from freezegun import freeze_time
import pytest

from doujia.report.saving import calc_period_saving, calc_saving, calc_saving_summary


def test_investment_report(entries: list[Directive]):
    """
    @@@/main.bean
    2021-01-01 open Assets:Current
    2021-01-01 open Assets:Investment
    2021-01-01 open Income:Salary

    2024-01-05 * "工资"
        Income:Salary -1,000.00 CNY
        Assets:Current

    2024-01-08 * "存钱"
        Assets:Current -500.00 CNY
        Assets:Investment

    2024-02-05 * "工资"
        Income:Salary -3,000.00 CNY
        Assets:Current

    2024-04-05 * "工资"
        Income:Salary -1,000.00 CNY
        Assets:Current
    """

    ret = calc_saving(
        entries,
        start_date_inclusive=date(2024, 1, 1),
        end_date_exclusive=date(2024, 4, 1),
        salary_accounts=["Income:Salary"],
        current_accounts=["Assets:Current"],
        saving_accounts=["Assets:Investment"],
    )
    assert (ret.total_saving / ret.total_income) == 0.125
    assert ret.total_saving == 500
    assert ret.total_income == 4000


def test_period_saving_report(entries: list[Directive]):
    """
    @@@/main.bean
    2021-01-01 open Assets:Current
    2021-01-01 open Assets:Investment
    2021-01-01 open Income:Salary

    2024-01-05 * "工资"
        Income:Salary -1,000.00 CNY
        Assets:Current

    2024-01-08 * "存钱"
        Assets:Current -500.00 CNY
        Assets:Investment

    2024-02-05 * "工资"
        Income:Salary -3,000.00 CNY
        Assets:Current

    2024-04-05 * "工资"
        Income:Salary -1,000.00 CNY
        Assets:Current
    """

    ret = calc_period_saving(
        entries,
        periods=[
            (date(2024, 1, 1), date(2024, 2, 1)),
            (date(2024, 2, 1), date(2024, 3, 1)),
            (date(2024, 3, 1), date(2024, 4, 1)),
            (date(2024, 4, 1), date(2024, 5, 1)),
        ],
        salary_accounts=["Income:Salary"],
        current_accounts=["Assets:Current"],
        saving_accounts=["Assets:Investment"],
    )
    assert (ret[0].total_saving / ret[0].total_income) == 0.5
    assert ret[0].total_saving == 500
    assert ret[0].total_income == 1000

    assert (ret[1].total_saving / ret[1].total_income) == 0
    assert ret[1].total_saving == 0
    assert ret[1].total_income == 3000

    assert ret[2].total_saving == 0
    assert ret[2].total_income == 0

    assert (ret[3].total_saving / ret[3].total_income) == 0
    assert ret[3].total_saving == 0
    assert ret[3].total_income == 1000


@freeze_time("2024-05-20")
def test_saving_summary(entries: list[Directive]):
    """
    @@@/main.bean
    2021-01-01 open Assets:Current
    2021-01-01 open Assets:Investment
    2021-01-01 open Income:Salary

    2024-01-05 * "工资"
        Income:Salary -1,000.00 CNY
        Assets:Current

    2024-01-08 * "存钱"
        Assets:Current -500.00 CNY
        Assets:Investment

    2024-02-05 * "工资"
        Income:Salary -3,000.00 CNY
        Assets:Current

    2024-04-05 * "工资"
        Income:Salary -1,000.00 CNY
        Assets:Current
    """

    ret = calc_saving_summary(
        entries,
        salary_accounts=["Income:Salary"],
        current_accounts=["Assets:Current"],
        saving_accounts=["Assets:Investment"],
    )

    assert len(ret.current_periods) == 4
