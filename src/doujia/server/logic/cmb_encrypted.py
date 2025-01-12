import io
import json
from datetime import datetime
import os

from beancount.core import data
from beancount.core.number import D
from beancount.loader import load_file
from beancount.parser import printer
from beancount.scripts.format import align_beancount
from flask import current_app

from doujia.post_processor.merger import _merge_beancount_content
from doujia.post_processor.transaction_categorizer import _categorize_transactions
from doujia.utils.util import get_last_balance_date

DEFAULT_UFO_POSTING = data.Posting(
    "Equity:UFO",
    None,
    None,
    None,
    None,
    None,
)


def convert_cmb_item_to_postings(item):
    if item["currency"] == "156":
        currency = "CNY"
    elif item["currency"] == "840":
        currency = "USD"
    else:
        currency = "CNY"

    amount = D(item["amount"])

    out_posting = data.Posting(
        account="Liabilities:CreditCard:CMB",
        units=data.Amount(-amount, currency),
        cost=None,
        price=None,
        flag=None,
        meta=None,
    )

    out_posting = data.Posting(
        account=out_posting.account,
        units=data.Amount(-amount, currency),
        cost=out_posting.cost,
        price=out_posting.price,
        flag=out_posting.flag,
        meta=out_posting.meta,
    )

    postings = [out_posting, DEFAULT_UFO_POSTING]

    return postings


def load_missing_transactions_from_cmb_items(filename, items):
    last_balance_date = get_last_balance_date(filename, "Liabilities:CreditCard:CMB")
    existed_unique_no_set = get_existed_unique_no_set(
        filename, "Liabilities:CreditCard:CMB"
    )

    txns = []
    for item in items:
        txn_date = datetime.strptime(item["tranDateTime"], "%Y%m%d%H%M%S").date()
        if last_balance_date is not None and txn_date < last_balance_date:
            continue

        if "id" in item and "CMB_" + item["id"] in existed_unique_no_set:
            continue

        txn = convert_cmb_item_to_transaction(item)
        txns.append(txn)
    return txns


def convert_cmb_item_to_transaction(item):
    date_time = datetime.strptime(item["tranDateTime"], "%Y%m%d%H%M%S")
    date = date_time.date()

    description = item["tranSummary"]
    postings = convert_cmb_item_to_postings(item)

    transaction = data.Transaction(
        data.new_metadata(
            None,
            None,
            {
                "time": date_time.strftime("%H:%M:%S"),
                "card": item["tranCard"].replace("尾号", ""),
                "uniqueNo": "CMB_" + item["id"],
            },
        ),
        date,
        "!",
        description,
        None,
        data.EMPTY_SET,
        data.EMPTY_SET,
        postings,
    )

    return transaction


def get_existed_unique_no_set(main_file_path, account_name):
    entries, _, _ = load_file(main_file_path)

    unique_no_set = set()
    for entry in entries:
        if isinstance(entry, data.Transaction) and "uniqueNo" in entry.meta:
            unique_no_set.add(entry.meta["uniqueNo"])

    return unique_no_set


def import_cmb_transactions(items) -> int:
    print(json.dumps(items, indent=4, ensure_ascii=False))
    txns = load_missing_transactions_from_cmb_items(
        os.path.join(current_app.ledger_root, "main.bean"), items
    )

    with io.StringIO() as output:
        for txn in txns:
            output.write(printer.format_entry(txn)[:-1] + "\n" + "\n")

        imported_content = output.getvalue()

    with io.StringIO() as output:
        _categorize_transactions(imported_content, output)

        imported_content = output.getvalue()

    with io.StringIO() as output:
        with open(
            os.path.join(current_app.ledger_root, "main.bean"), "r", encoding="utf-8"
        ) as file:
            main_content = file.read()
            _merge_beancount_content(main_content, imported_content, output)

        output.write("\n")

        result = align_beancount(output.getvalue())

        with open(
            os.path.join(current_app.ledger_root, "main.bean"), "w", encoding="utf-8"
        ) as file:
            file.write(result)

    return len(txns)
