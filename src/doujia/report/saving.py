from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from beancount.core.data import Directive, Transaction
from beancount.parser import printer
from logzero import logger


@dataclass
class SavingPeriodStat:
    start_date_inclusive: date
    end_date_exclusive: date
    total_income: Decimal
    total_saving: Decimal


def calc_saving(  # noqa: C901
    entries: list[Directive],  # type: ignore
    start_date_inclusive: date,
    end_date_exclusive: date,
    salary_accounts: list[str],
    current_accounts: list[str],
    saving_accounts: list[str],
    debug_output=False,
) -> SavingPeriodStat:
    total_income = Decimal(0)
    total_saving = Decimal(0)
    income_entries: list[Directive] = []  # type: ignore
    saving_entries: list[Directive] = []  # type: ignore

    for entry in entries:
        if not isinstance(entry, Transaction):
            continue

        if entry.date < start_date_inclusive or entry.date >= end_date_exclusive:
            continue

        hasSalaryAccount = False
        hasSavingAccount = False
        hasCurrentAccount = False
        current_amount = Decimal(0)
        for posting in entry.postings:
            if posting.account in salary_accounts:
                hasSalaryAccount = True
            elif posting.account in current_accounts:
                hasCurrentAccount = True
                current_amount = current_amount + posting.units.number
            elif posting.account in saving_accounts:
                hasSavingAccount = True

        if hasSalaryAccount and hasCurrentAccount:
            income_entries.append(entry)
            total_income += current_amount
        elif hasSavingAccount and hasCurrentAccount:
            saving_entries.append(entry)
            total_saving += current_amount

        continue

    if debug_output:
        logger.debug("Income Entries:")
        for entry in income_entries:
            logger.debug(printer.format_entry(entry))

        logger.debug("Saving Entries:")
        for entry in saving_entries:
            logger.debug(printer.format_entry(entry))

    return SavingPeriodStat(
        start_date_inclusive=start_date_inclusive,
        end_date_exclusive=end_date_exclusive,
        total_income=total_income,
        total_saving=(0 - total_saving),
    )


def calc_period_saving(
    entries: list[Directive],  # type: ignore
    periods: list[tuple[date, date]],
    salary_accounts: list[str],
    current_accounts: list[str],
    saving_accounts: list[str],
    debug_output=False,
) -> list[SavingPeriodStat]:
    return [
        calc_saving(
            entries=entries,
            start_date_inclusive=start,
            end_date_exclusive=end,
            salary_accounts=salary_accounts,
            current_accounts=current_accounts,
            saving_accounts=saving_accounts,
            debug_output=debug_output,
        )
        for (start, end) in periods
    ]


@dataclass
class SavingSummary:
    current_periods: list[SavingPeriodStat]


def get_first_days(start_year, start_month):
    today = datetime.today().date()
    next_month = today.replace(day=28) + timedelta(days=4)  # 确保跨月
    next_month = next_month.replace(day=1)

    first_days = []
    current_date = date(start_year, start_month, 1)

    while current_date <= next_month:
        first_days.append(current_date)
        if current_date.month == 12:
            current_date = current_date.replace(
                year=current_date.year + 1, month=1, day=1
            )
        else:
            current_date = current_date.replace(month=current_date.month + 1, day=1)

    return first_days


def get_first_day_pairs(start_year, start_month):
    first_days = get_first_days(start_year, start_month)
    first_day_pairs = [
        (first_days[i], first_days[i + 1]) for i in range(len(first_days) - 1)
    ]

    return first_day_pairs


def calc_saving_summary(
    entries: list[Directive],  # type: ignore
    salary_accounts: list[str],
    current_accounts: list[str],
    saving_accounts: list[str],
    debug_output=False,
) -> SavingSummary:

    periods = get_first_day_pairs(2024, 2)

    return SavingSummary(
        current_periods=calc_period_saving(
            entries=entries,
            periods=periods,
            salary_accounts=salary_accounts,
            current_accounts=current_accounts,
            saving_accounts=saving_accounts,
            debug_output=debug_output,
        )
    )
