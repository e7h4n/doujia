from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import TypeVar

import requests
from beancount.core import data

from doujia.hsbc.cipher import decrypt_response, encrypt_request, generate_key
from doujia.server.logic.ccb import DEFAULT_UFO_POSTING
from doujia.server.logic.utils import get_existed_unique_no_set, import_transactions
from doujia.utils.util import get_last_balance_date

Transaction = TypeVar("Transaction", bound=data.Transaction)


@dataclass
class HSBCSession:
    authorizationguest: str
    authorization: str


def _query_unbilled_transactions(session: HSBCSession):
    sm4_key = generate_key()

    request_data = {
        "billOption": "A",
    }

    request = encrypt_request(request_data, sm4_key)

    url = "https://creditcards.hsbc.com.cn/nwxhf/bill/getPendingBills"
    headers = {
        "authorization": session.authorization,
        "authorizationguest": session.authorizationguest,
    }

    response = requests.post(url, headers=headers, json=request, verify=False)

    # 处理响应
    if response.status_code != 200:
        raise Exception(f"请求失败: {response.status_code}")

    if "authorization" in response.headers:
        session.authorization = response.headers["authorization"]
    if "authorizationguest" in response.headers:
        session.authorizationguest = response.headers["authorizationguest"]

    response_data = response.json()
    decrypted_data = decrypt_response(response_data["rspData"], sm4_key)

    return decrypted_data["rspData"]["transList"]


def _parse_amount(item) -> data.Amount:
    amount_str = item["transAmount"]
    currency = item["currency"]["symbol"]
    amount = Decimal(amount_str)

    return data.Amount(amount, currency)


def _parse_posting(item):
    amount = _parse_amount(item)

    out_posting = data.Posting(
        account="Liabilities:Short:CreditCard:HSBC",
        units=data.Amount(-amount.number, amount.currency),
        cost=None,
        price=None,
        flag=None,
        meta=None,
    )

    return [out_posting, DEFAULT_UFO_POSTING]


def _parse_unique_no(item: dict) -> str:
    txn_date = _parse_txn_date(item)
    trans_no = item["transNo"]

    return f"HSBC_{txn_date.strftime('%Y%m%d')}_{trans_no}"


def _parse_txn_date(item):
    return datetime.strptime(item["newTransDate"], "%Y%m%d").date()


def load_missing_transactions(filename: str, items):
    last_balance_date = get_last_balance_date(filename, "Liabilities:Short:CreditCard:HSBC")
    existed_unique_no_set = get_existed_unique_no_set(filename)

    txns = []
    for item in items:
        """item
        {
            "newTransDate": "20250228",
            "transTime": "21140168",
            "cardEnd": "1234",
            "transNo": "300508",
            "transDescDetail": "WLZF-京东支付-京东商城业务",
            "transAmount": "164.98",
            "transDesc2": "",
            "transType": "1022",
            "transDesc": "WLZF-京东支付-京东商城业务",
            "valDate": "20250301",
            "transDate": "0228",
            "recordDate": "20250301",
            "currency": {"code": "156", "desc": "人民币", "mark": "¥", "sym": "C", "symbol": "CNY"},
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

    return txns


def _convert_transaction(item) -> Transaction:
    description = item["transDescDetail"].strip()
    postings = _parse_posting(item)
    txn_date = _parse_txn_date(item)
    unique_no = _parse_unique_no(item)

    trans_time = item.get("transTime", "")
    formatted_time = ""
    if len(trans_time) >= 6:
        formatted_time = f"{trans_time[0:2]}:{trans_time[2:4]}:{trans_time[4:6]}"

    transaction = data.Transaction(
        data.new_metadata(
            None,
            None,
            {
                "time": formatted_time,
                "card": item["cardEnd"],
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


def import_unbilled_transactions(ledger_file: str, session: HSBCSession, categorize_config: str, import_to: str) -> int:
    trans_list = _query_unbilled_transactions(session)

    txns = load_missing_transactions(ledger_file, trans_list)

    return import_transactions(txns, categorize_config, import_to)
