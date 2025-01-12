import io
from datetime import datetime

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


def get_existed_unique_no_set(main_file_path, account_name):
    entries, _, _ = load_file(main_file_path)

    unique_no_set = set()
    for entry in entries:
        if isinstance(entry, data.Transaction) and "uniqueNo" in entry.meta:
            unique_no_set.add(entry.meta["uniqueNo"])

    return unique_no_set


def import_ccb_transactions(items) -> int:
    txns = load_missing_transactions_from_ccb_items("main.bean", items)

    with io.StringIO() as output:
        for txn in txns:
            del txn.meta["billType"]
            output.write(printer.format_entry(txn)[:-1] + "\n" + "\n")

        imported_content = output.getvalue()

    with io.StringIO() as output:
        _categorize_transactions(
            current_app.doujia_config.categorize_config, imported_content, output
        )

        imported_content = output.getvalue()

    with io.StringIO() as output:
        with open(current_app.doujia_config.import_to, "r", encoding="utf-8") as file:
            main_content = file.read()
            _merge_beancount_content(main_content, imported_content, output)

        output.write("\n")

        result = align_beancount(output.getvalue())

        with open(current_app.doujia_config.import_to, "w", encoding="utf-8") as file:
            file.write(result)

    return len(txns)
