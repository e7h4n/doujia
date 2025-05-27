import io
from datetime import datetime, timedelta
from typing import TypeVar

from beancount.core import data
from beancount.loader import load_file
from beancount.parser import printer
from beancount.scripts.format import align_beancount

from doujia.post_processor.merger import _merge_beancount_content
from doujia.post_processor.transaction_categorizer import _categorize_transactions
from doujia.utils.util import get_last_balance_date

Transaction = TypeVar("Transaction", bound=data.Transaction)


DEFAULT_UFO_POSTING = data.Posting(
    "Equity:UFO",
    None,
    None,
    None,
    None,
    None,
)


def get_existed_unique_no_set(main_file_path):
    entries, _, _ = load_file(main_file_path)

    unique_no_set = set()
    for entry in entries:
        if isinstance(entry, data.Transaction) and "uniqueNo" in entry.meta:
            unique_no_set.add(entry.meta["uniqueNo"])

    return unique_no_set


def _compare_transactions(transaction: Transaction):
    if "time" in transaction.meta and transaction.meta["time"] is not None and len(transaction.meta["time"]) > 0:
        return datetime.combine(
            transaction.date,
            datetime.strptime(transaction.meta["time"], "%H:%M:%S").time(),
        )

    return datetime.combine(transaction.date, datetime.min.time())


def sort_transactions(transactions: list[Transaction]) -> list[Transaction]:
    return sorted(transactions, key=_compare_transactions)


def import_transactions(transactions: list[Transaction], categorize_config: str, import_to: str) -> int:
    with io.StringIO() as output:
        for txn in sort_transactions(transactions):
            output.write(printer.format_entry(txn)[:-1] + "\n" + "\n")

        imported_content = output.getvalue()

    with io.StringIO() as output:
        _categorize_transactions(categorize_config, imported_content, output)

        imported_content = output.getvalue()

    with io.StringIO() as output:
        with open(import_to, encoding="utf-8") as file:
            main_content = file.read()
            _merge_beancount_content(main_content, imported_content, output)

        output.write("\n")

        result = align_beancount(output.getvalue())

        with open(import_to, "w", encoding="utf-8") as file:
            file.write(result)

    return len(transactions)


def insert_missing_balance(
    account: str, date: datetime, amount: data.Amount, ledger_file: str, import_to: str | None = None
) -> data.Transaction | None:
    if import_to is None:
        import_to = ledger_file

    last_balance_date = get_last_balance_date(ledger_file, account)
    if last_balance_date is not None and last_balance_date >= date:
        return None

    if datetime.now().date() <= date:
        return None

    txn = data.Balance(
        date=date + timedelta(days=1), account=account, amount=amount, meta=None, tolerance=None, diff_amount=None
    )

    imported_content = printer.format_entry(txn)[:-1] + "\n" + "\n"

    with io.StringIO() as output:
        with open(import_to, encoding="utf-8") as file:
            main_content = file.read()
            _merge_beancount_content(main_content, imported_content, output)

        output.write("\n")

        result = align_beancount(output.getvalue())

        with open(import_to, "w", encoding="utf-8") as file:
            file.write(result)

    return txn
