from datetime import datetime
import os

from beancount.core import data
from beancount.core.number import D
from flask import current_app

from doujia.server.logic.utils import (
    DEFAULT_UFO_POSTING,
    get_existed_unique_no_set,
    import_transactions,
)
from doujia.utils.util import get_last_balance_date


def convert_cmb_item_to_postings(item):
    if item["currency"] == "156":
        currency = "CNY"
    elif item["currency"] == "840":
        currency = "USD"
    else:
        currency = "CNY"

    amount = D(item["amount"])

    out_posting = data.Posting(
        account="Liabilities:Short:CreditCard:CMB",
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
    last_balance_date = get_last_balance_date(
        filename, "Liabilities:Short:CreditCard:CMB"
    )
    existed_unique_no_set = get_existed_unique_no_set(filename)

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


def import_cmb_transactions(items) -> int:
    txns = load_missing_transactions_from_cmb_items(
        os.path.join(current_app.ledger_root, "main.bean"), items
    )

    return import_transactions(txns)
