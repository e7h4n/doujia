from collections import namedtuple

from beancount.core.convert import convert_amount
from beancount.core.data import Transaction
from beancount.loader import load_file

from doujia.price.price_map import get_last_and_realtime_price_map

Cashflow = namedtuple("Cashflow", ["date", "amount"])


def main():  # noqa: C901
    entries, errors, options_map = load_file("./main.bean")
    _, price_map = get_last_and_realtime_price_map(entries)

    investment_entries = []
    for entry in entries:
        if isinstance(entry, Transaction):
            is_investment = False
            for posting in entry.postings:
                # 如果账号中包含 stock 或者 investment，则加入到投资交易列表中
                if (
                    "Stock" in posting.account
                    or "Investment" in posting.account
                    or "Saving" in posting.account
                ):
                    is_investment = True
                    break
            if is_investment:
                investment_entries.append(entry)

    cash_flows = []
    last_date = None
    amount = 0
    posting_amount = 0
    for entry in investment_entries:
        if last_date is None:
            last_date = entry.date
        elif last_date != entry.date:
            cash_flows.append(Cashflow(last_date, amount))
            last_date = entry.date
            amount = 0

        for posting in entry.postings:
            if (
                "Stock" in posting.account
                or "Investment" in posting.account
                or "Saving" in posting.account
            ):
                converted_amount = convert_amount(
                    posting.units,
                    "CNY",
                    price_map,
                    date=entry.date,
                    via=["USD", "HKD", "CNY"],
                )
                assert converted_amount.currency == "CNY"
                posting_amount += converted_amount.number

            elif (
                "Fee" not in posting.account
                and "PnL" not in posting.account
                and "PrepaidExpenses" not in posting.account
            ):
                if posting.units.currency == "CNY":
                    amount += posting.units.number
                else:
                    amount += convert_amount(
                        posting.units,
                        "CNY",
                        price_map,
                        date=entry.date,
                    ).number

    cash_flows.append(Cashflow(last_date, amount))


if __name__ == "__main__":
    main()
