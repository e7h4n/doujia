import hashlib
import os
from datetime import datetime
from decimal import Decimal

from beancount.core import data

from doujia.server.app import current_app
from doujia.server.logic.utils import (
    DEFAULT_UFO_POSTING,
    get_existed_unique_no_set,
    import_transactions,
    insert_missing_balance,
)
from doujia.utils.util import get_last_balance_date

ACCOUNT = "Assets:Short:Current:HSBC"


def _parse_txn_date(item):
    # txnDate: "2025-05-26 00:00:00"
    date_str = item["txnDate"]

    # Extract year, month, and day from the string
    year = int(date_str.split("-")[0])
    month = int(date_str.split("-")[1])
    day = int(date_str.split("-")[2].split(" ")[0])

    txn_date = datetime(year, month, day).date()
    return txn_date


def _parse_unique_no(item):
    # 将 txnDetail 列表 join 后计算 MD5
    detail_str = "#".join(item["txnDetail"])
    md5_hash = hashlib.md5(detail_str.encode("utf-8")).hexdigest()
    return "HSBC_CURRENT_" + md5_hash


def _parse_amount(item):
    amt_number = item["txnAmt"]["amt"]

    # 转换为 Decimal 并保留两位小数
    decimal_amount = Decimal(str(amt_number)).quantize(Decimal("0.01"))

    return data.Amount(decimal_amount, "CNY")


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
    description = "#".join(item["txnDetail"])
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


def _parse_balance_amount(item):
    # 解析最后一条交易的余额金额
    bal_run_amt = item["balRunAmt"]["amt"]
    return data.Amount(Decimal(str(bal_run_amt)).quantize(Decimal("0.01")), item["balRunAmt"]["ccy"])


def load_missing_transactions(filename: str, items):
    last_balance_date = get_last_balance_date(filename, ACCOUNT)
    existed_unique_no_set = get_existed_unique_no_set(filename)

    txns = []
    for item in items:
        """item

{
      "txnIndex": 0,
      "txnAmt": { "amt": -100.0, "ccy": "CNY" },
      "txnTypeCde": "D",
      "txnCatCde": "",
      "balRunAmt": { "amt": 200.0, "ccy": "CNY" },
      "txnDate": "2025-05-26 00:00:00",
      "txnRefNum": "",
      "txnDetail": [],
      "txnPostDate": "2025-05-26 00:00:00",
      "termStrtDt": "2025-05-26 00:00:00",
      "mturIntAmt": { "amt": 0, "ccy": "" },
      "extension": {}
}


        """
        txn_date = _parse_txn_date(item)
        if last_balance_date is not None and txn_date < last_balance_date:
            continue

        unique_no = _parse_unique_no(item)
        if unique_no in existed_unique_no_set:
            continue

        txn = _convert_transaction(item)
        txns.append(txn)

    if len(items) > 0:
        last_balance_item = items[-1]
        last_balance_date = _parse_txn_date(last_balance_item)
        balance_txn = insert_missing_balance(
            account=ACCOUNT,
            date=last_balance_date,
            amount=_parse_balance_amount(last_balance_item),
            ledger_file=filename,
            import_to=current_app.doujia_config.import_to,
        )

        if balance_txn:
            txns.append(balance_txn)

    return txns


def import_hsbc_cn_asset(items) -> int:
    txns = load_missing_transactions(os.path.join(current_app.ledger_root, "main.bean"), items["txnSumm"])

    return import_transactions(txns, current_app.doujia_config.categorize_config, current_app.doujia_config.import_to)
