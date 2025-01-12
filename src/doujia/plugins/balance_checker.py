from collections import namedtuple

from beancount.core.data import Transaction
from beancount.core.number import ZERO

__plugins__ = ["balance_checker"]

BalanceError = namedtuple("BalanceError", "source message entry")


def _compute_balances(entries, account_name, tag):
    balances = {}
    tag_balances = {}
    currency_set = set()

    for entry in entries:
        if isinstance(entry, Transaction):
            for posting in entry.postings:
                if posting.account == account_name:
                    currency = posting.units.currency
                    currency_set.add(currency)

                    balances[currency] = (
                        balances.get(currency, ZERO) + posting.units.number
                    )

                    if tag in entry.tags:
                        tag_balances[currency] = (
                            tag_balances.get(currency, ZERO) + posting.units.number
                        )

    return balances, tag_balances, currency_set


def _find_first_unbalanced_entry(entries, account_name, currency, tag):  # noqa: C901
    balance = ZERO
    tag_balance = ZERO
    curr_entries = []
    for entry in entries:
        if isinstance(entry, Transaction):
            for posting in entry.postings:
                if (
                    posting.account == account_name
                    and posting.units.currency == currency
                ):
                    balance += posting.units.number
                    if tag in entry.tags:
                        tag_balance += posting.units.number
                    curr_entries.append(entry)

    while not _is_equal(balance, tag_balance) and len(curr_entries) > 0:
        curr_date = curr_entries[-1].date
        curr_date_entries = []
        for entry in reversed(curr_entries):
            if entry.date == curr_date:
                curr_date_entries.append(entry)
            else:
                break

        curr_entries = curr_entries[: -len(curr_date_entries)]
        for entry in curr_date_entries:
            for posting in entry.postings:
                if (
                    posting.account == account_name
                    and posting.units.currency == currency
                ):
                    last_balance = balance
                    last_tag_balance = tag_balance

                    balance -= posting.units.number
                    if tag in entry.tags:
                        tag_balance -= posting.units.number

                    if _is_equal(balance, tag_balance):
                        return entry, last_balance, last_tag_balance

    return None, None, None


def _is_equal(left, right):
    return abs(left - right) < 0.01


def balance_checker(entries, options_map, config=None):
    # 将 config 字符串转换为字典
    config_dict = eval(config)
    errors = []

    # 遍历字典
    for account_name, tag in config_dict.items():
        balance, tag_balance, currency_set = _compute_balances(
            entries, account_name, tag
        )

        for currency in currency_set:
            left = balance.get(currency, ZERO)
            right = tag_balance.get(currency, ZERO)
            if _is_equal(left, right):
                continue

            (
                last_transaction,
                last_balance,
                last_tag_balance,
            ) = _find_first_unbalanced_entry(entries, account_name, currency, tag)

            if last_transaction:
                message = "Balance failed for '{}': expected {} {} != accumulated {} {} ({} {} {})".format(
                    account_name,
                    last_tag_balance,
                    currency,
                    last_balance,
                    currency,
                    abs(last_balance - last_tag_balance),
                    currency,
                    "too much" if last_balance > last_tag_balance else "too little",
                )
                source = last_transaction.meta
                entry = last_transaction
            else:
                message = "Balance failed for '{}': expected {} {} != accumulated {} {} ({} {} {})".format(
                    account_name,
                    right,
                    currency,
                    left,
                    currency,
                    abs(left - right),
                    currency,
                    "too much" if left > right else "too little",
                )
                source = entries[-1].meta
                entry = entries[-1]

            errors.append(BalanceError(source=source, message=message, entry=entry))

    return entries, errors
