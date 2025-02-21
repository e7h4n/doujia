"""An example of adding a forecasting feature to Beancount via a plugin.

This entry filter plugin uses existing syntax to define and automatically
inserted transactions in the future based on a convention. It serves mostly as
an example of how you can experiment by creating and installing a local filter,
and not so much as a serious forecasting feature (though the experiment is a
good way to get something more general kickstarted eventually, I think the
concept would generalize nicely and should eventually be added as a common
feature of Beancount).

A user can create a transaction like this:

    2014-03-08 # "Electricity bill [MONTHLY]"
      Expenses:Electricity 			50.10 USD
      Assets:Checking			       -50.10 USD

and new transactions will be created monthly for the following year.
Note the use of the '#' flag and the word 'MONTHLY' which defines the
periodicity.

The number of recurrences can optionally be specified either by providing an
end date or by specifying the number of times that the transaction will be
repeated. For example:

    2014-03-08 # "Electricity bill [MONTHLY UNTIL 2019-12-31]"
      Expenses:Electricity 			50.10 USD
      Assets:Checking			       -50.10 USD

    2014-03-08 # "Electricity bill [MONTHLY REPEAT 10 TIMES]"
      Expenses:Electricity 			50.10 USD
      Assets:Checking			       -50.10 USD

Transactions can also be repeated at yearly intervals, e.g.:

    2014-03-08 # "Electricity bill [YEARLY REPEAT 10 TIMES]"
      Expenses:Electricity 			50.10 USD
      Assets:Checking			       -50.10 USD

Other examples:

    2014-03-08 # "Electricity bill [WEEKLY SKIP 1 TIME REPEAT 10 TIMES]"
      Expenses:Electricity 			50.10 USD
      Assets:Checking			       -50.10 USD

    2014-03-08 # "Electricity bill [DAILY SKIP 3 TIMES REPEAT 1 TIME]"
      Expenses:Electricity 			50.10 USD
      Assets:Checking			       -50.10 USD
"""

__copyright__ = "Copyright (C) 2014-2017  Martin Blais"
__license__ = "GNU GPLv2"

import argparse
import datetime
import os
import re
from dataclasses import dataclass
from typing import TypeVar

from beancount.core import data
from beancount.loader import load_file
from beancount.parser.printer import print_entries
from dateutil import rrule

Directive = TypeVar("Directive", bound=data.Directive)  # type: ignore


@dataclass
class Forecast:
    key: str
    related_entry: Directive
    generated_entries: list[Directive]


def forecast_plugin(entries, options_map):
    """An example filter that piggybacks on top of the Beancount input syntax to
    insert forecast entries automatically. This functions accepts the return
    value of beancount.loader.load_file() and must return the same type of output.

    Args:
      entries: a list of entry instances
      options_map: a dict of options parsed from the file
    Returns:
      A tuple of entries and errors.
    """

    # Filter out forecast entries from the list of valid entries.
    forecast_entries = []
    filtered_entries = []
    for entry in entries:
        outlist = (
            forecast_entries
            if (isinstance(entry, data.Transaction) and entry.flag == "#")
            else filtered_entries
        )
        outlist.append(entry)

    forecasts = []
    for entry in forecast_entries:
        # Parse the periodicity.
        match = re.search(
            r"(^.*)\[(MONTHLY|YEARLY|WEEKLY|DAILY)"
            r"(\s+SKIP\s+([1-9][0-9]*)\s+TIME.?)"
            r"?(\s+REPEAT\s+([1-9][0-9]*)\s+TIME.?)"
            r"?(\s+UNTIL\s+([0-9\-]+))?\]",
            entry.narration,
        )

        if not match:
            continue

        forecast_narration = match.group(1).strip()
        forecast_interval = (
            rrule.YEARLY
            if match.group(2).strip() == "YEARLY"
            else (
                rrule.WEEKLY
                if match.group(2).strip() == "WEEKLY"
                else rrule.DAILY if match.group(2).strip() == "DAILY" else rrule.MONTHLY
            )
        )
        forecast_periodicity = {"dtstart": entry.date}
        if match.group(6):  # e.g., [MONTHLY REPEAT 3 TIMES]:
            forecast_periodicity["count"] = int(match.group(6))
        elif match.group(8):  # e.g., [MONTHLY UNTIL 2020-01-01]:
            forecast_periodicity["until"] = datetime.datetime.strptime(
                match.group(8), "%Y-%m-%d"
            ).date()
        else:
            # e.g., [MONTHLY]
            forecast_periodicity["until"] = datetime.date(
                datetime.date.today().year, 12, 31
            )

        if match.group(4):
            # SKIP
            forecast_periodicity["interval"] = int(match.group(4)) + 1

        # Generate a new entry for each forecast date.
        forecast_dates = [
            dt.date() for dt in rrule.rrule(forecast_interval, **forecast_periodicity)
        ]

        # 找到为负值的 posting
        for posting in entry.postings:
            if posting.units.number < 0:
                # 构建循环交易的 key，格式为交易日期 + 付款账户
                entry_key = (entry.date, posting.account)
                break

        forecast = Forecast(
            key=entry_key,
            related_entry=entry,
            generated_entries=[],
        )

        for forecast_date in forecast_dates:
            forecast_entry = entry._replace(
                date=forecast_date, narration=forecast_narration, flag="*"
            )
            forecast.generated_entries.append(forecast_entry)

        forecasts.append(forecast)

    return forecasts


def generate_forecast(forecasts: list[Forecast], forecast_root: str):
    for forecast in forecasts:
        forecast_date, account = forecast.key
        # 把 account 中的 : 换成 /
        directory = account.replace(":", "/")
        os.makedirs(f"{forecast_root}/{directory}", exist_ok=True)
        with open(f"{forecast_root}/{directory}/{forecast_date}.bean", "w") as f:
            print_entries(forecast.generated_entries, file=f)


def update_related_entries(forecasts: list[Forecast], forecast_root: str):
    replace_directives: dict[str, dict[int, str]] = dict()

    for forecast in forecasts:
        forecast_date, account = forecast.key
        directory = account.replace(":", "/")
        target_file = f"{forecast_root}/{directory}/{forecast_date}.bean"
        filename = forecast.related_entry.meta["filename"]
        line_number = forecast.related_entry.meta["lineno"]
        if filename not in replace_directives:
            replace_directives[filename] = dict()
        replace_directives[filename][line_number] = target_file

    for filename, directives in replace_directives.items():
        lines = []
        with open(filename) as f:
            lines = f.readlines()
        sorted_directives = dict(sorted(directives.items(), reverse=True))
        for line_number, target_file in sorted_directives.items():
            # 找到 target_file 相对于 filename 的路径
            filename_dir = os.path.dirname(filename)
            if filename_dir:
                target_file = os.path.relpath(target_file, filename_dir)
            begin_index = line_number - 1
            end_index = line_number
            while end_index < len(lines) and lines[end_index][0] == " ":
                end_index += 1
            lines[begin_index:end_index] = [f'include "{target_file}"\n']
        with open(filename, "w") as f:
            f.writelines(lines)


def replace_forecast(ledger_path: str, forecast_root: str):
    entries, _, options_map = load_file(ledger_path)
    forecasts = forecast_plugin(entries, options_map)
    generate_forecast(forecasts, forecast_root)
    update_related_entries(forecasts, forecast_root)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Replace forecast entries")
    parser.add_argument("--ledger-path", help="Ledger path", required=True)
    parser.add_argument(
        "--forecast-root",
        help="Forecast directory relative to ledger path",
        required=True,
    )
    args = parser.parse_args()
    replace_forecast(args.ledger_path, args.forecast_root)
