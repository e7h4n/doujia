import os
from datetime import datetime
from decimal import Decimal

from beancount.core import data

from doujia.server.app import current_app
from doujia.server.logic.utils import DEFAULT_UFO_POSTING, get_existed_unique_no_set, import_transactions
from doujia.utils.util import get_last_balance_date

ACCOUNT = "Assets:Short:Current:HSBC"


def _parse_txn_date(item):
    # Convert date string like "2025年3月3日" to datetime.date
    date_str = item[0]

    # Extract year, month, and day from the string
    year = int(date_str.split("年")[0])
    month = int(date_str.split("年")[1].split("月")[0])
    day = int(date_str.split("月")[1].split("日")[0])

    txn_date = datetime(year, month, day).date()
    return txn_date


def _parse_unique_no(item):
    return "HSBC_CURRENT_" + item[1][-2]


def _parse_amount(item):
    return data.Amount(Decimal(item[2]), "CNY")


def _parse_posting(item):
    amount = _parse_amount(item)

    out_posting = data.Posting(
        account=ACCOUNT,
        units=amount,
        cost=None,
        price=None,
        flag=None,
        meta=None,
    )

    return [out_posting, DEFAULT_UFO_POSTING]


def _convert_transaction(item):
    description = "#".join(item[1])
    postings = _parse_posting(item)
    txn_date = _parse_txn_date(item)
    unique_no = _parse_unique_no(item)

    transaction = data.Transaction(
        data.new_metadata(
            None,
            None,
            {
                "uniqueNo": unique_no,
            },
        ),
        txn_date,
        "!",
        description,
        None,
        data.EMPTY_SET,
        data.EMPTY_SET,
        postings,
    )

    return transaction


def load_missing_transactions(filename: str, items):
    last_balance_date = get_last_balance_date(filename, ACCOUNT)
    existed_unique_no_set = get_existed_unique_no_set(filename)

    txns = []
    for item in items:
        """item

  [
    '2025年3月3日',
    [
      '转账',
      '/AA/BB',
      '/CC/DD',
      'Submitted on: 02MAR25 10:24:08',
      'YPI123123',
      'COMMENT'
    ],
    74,254.32,
    74,254.32
  ]

        """
        txn_date = _parse_txn_date(item)
        if last_balance_date is not None and txn_date < last_balance_date:
            continue

        unique_no = _parse_unique_no(item)
        if unique_no in existed_unique_no_set:
            continue

        txn = _convert_transaction(item)
        txns.append(txn)

    return txns


def import_hsbc_current(items) -> int:
    txns = load_missing_transactions(os.path.join(current_app.ledger_root, "main.bean"), items)

    return import_transactions(txns, current_app.doujia_config.categorize_config, current_app.doujia_config.import_to)
