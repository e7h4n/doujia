import os
from datetime import datetime

from beancount.core import data
from beancount.core.number import D
from flask import current_app

from doujia.server.logic.cmb_encrypted import DEFAULT_UFO_POSTING
from doujia.server.logic.utils import import_transactions
from doujia.utils.util import get_last_balance_date


def convert_ccb_item_to_postings(item):
    currency = "CNY"

    amount = D(item["amount"])

    out_posting = data.Posting(
        account="Assets:Short:Current:CCB",
        units=data.Amount(-amount, currency),
        cost=None,
        price=None,
        flag=None,
        meta=None,
    )

    return [out_posting, DEFAULT_UFO_POSTING]


def load_missing_transactions_from_ccb_items(filename, items):
    last_balance_date = get_last_balance_date(filename, "Assets:Short:Current:CCB")

    txns = []
    for item in items:
        """item
        {
                        "dataList": [
                            {
                                "Dep_Txn_CgyCd": "02",
                                "Cntrprt_Txn_AccNo434": "6231***0808",
                                "Cntrprt_Txn_AccNo_Nm": "张宇辰",
                                "Txn_Rmrk": "电子汇入",
                                "Txn_Lcl_Tm": "072821",
                                "Txn_Lcl_Dt": "20241106",
                                "Smy_Cntnt": "电子汇入",
                                "Txn_CardNo434": "6217***0109",
                                "Smy_Cd": "0312",
                                "Txn_Dt": "20241106",
                                "Dep_AcBa": "15575.66",
                                "Dep_TxnAmt": "15561.54",
                                "CcyCdCN": "人民币",
                            }
                        ],
                        "Txn_Lcl_Dt": "20241106",
                    },
        """
        txn_date = datetime.strptime(item["Txn_Lcl_Dt"], "%Y%m%d").date()
        if last_balance_date is not None and txn_date < last_balance_date:
            continue

        txn = convert_ccb_item_to_transaction(item)
        txns.append(txn)
    return txns


def convert_ccb_item_to_transaction(item):
    description = item["dataList"][0]["Smy_Cntnt"]
    postings = convert_ccb_item_to_postings(item)

    item_data = item["dataList"][0]
    txn_date = datetime.strptime(item_data["Txn_Lcl_Dt"], "%Y%m%d")
    txn_time = datetime.strptime(item_data["Txn_Lcl_Tm"], "%H%M%S")
    transaction = data.Transaction(
        data.new_metadata(
            None,
            None,
            {
                "time": txn_time.strftime("%H:%M:%S"),
                "card": item_data["Txn_CardNo434"],
                "uniqueNo": "CCB_" + item_data["Txn_CardNo434"],
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


def import_ccb_transactions(items) -> int:
    txns = load_missing_transactions_from_ccb_items(
        os.path.join(current_app.ledger_root, "main.bean"), items
    )

    return import_transactions(txns)
