import hashlib
import os
from datetime import date, datetime
from decimal import Decimal

from beancount.core import data

from doujia.server.app import current_app
from doujia.server.logic.utils import (
    DEFAULT_UFO_POSTING,
    get_existed_unique_no_set,
    import_transactions,
    insert_missing_balance,
)
from doujia.utils.util import get_last_balance_date, get_last_transaction_date

ACCOUNT = "Liabilities:Short:CreditCard:HK:HSBC"


def _parse_txn_date(item):
    # "transactionDate": "2025-05-25",
    date_str = item["transactionDate"]

    # Extract year, month, and day from the string
    year = int(date_str.split("-")[0])
    month = int(date_str.split("-")[1])
    day = int(date_str.split("-")[2])

    txn_date = datetime(year, month, day).date()
    return txn_date


def _parse_unique_no(item):
    # 将 txnDetail 列表 join 后计算 MD5
    detail_str = item["uniqueTransactionIdentifier"]
    md5_hash = hashlib.md5(detail_str.encode("utf-8")).hexdigest()
    return "HSBC_HK_CREDIT_" + md5_hash


def _parse_amount(item):
    amt_number = item["transactionAmount"]["amount"]

    # 转换为 Decimal 并保留两位小数
    decimal_amount = Decimal(str(amt_number)).quantize(Decimal("0.01"))

    if item["transactionCreditDebitCode"] == "DEBIT_TRANSACTION":
        decimal_amount = -decimal_amount

    return data.Amount(decimal_amount, item["transactionAmount"]["currencyCode"])


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


def _parse_time(item):
    time_str = item["realTimeTransactionDetails"]["transactionTime"]
    if time_str:
        return datetime.strptime(time_str, "%H%M%S").time().strftime("%H:%M:%S")
    return ""


def _convert_transaction(item):
    description = "#".join(item["transactionDescriptions"])
    postings = _parse_posting(item)
    txn_date = _parse_txn_date(item)
    unique_no = _parse_unique_no(item)
    time = _parse_time(item)

    transaction = data.Transaction(
        data.new_metadata(
            None,
            None,
            {
                "uniqueNo": unique_no,
                "card": item["cardNumber"][-4:],
                "time": time,
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

{
    "transactionDate": "2025-05-26",
    "transactionType": "UNBILLED",
    "transactionAmount": {
        "amount": 10.00,
        "currencyCode": "CNY"
    },
    "transactionDescriptions": [
        "..."
    ],
    "cardNumber": "12345678901234567",
    "cardNumberDisplay": "12345678901234567",
    "cardNumberIdentifier": "...",
    "cardholderName": "NAME",
    "merchantCategoryCode": "1234",
    "transactionCreditDebitCode": "DEBIT_TRANSACTION",
    "realTimeTransactionDetails": {
        "transactionTime": "172359",
        "merchantName": "MERCHANT NAME",
        "merchantCity": "CITY",
        "merchantLocation": "CN",
        "merchantCountryCode": "CN"
    },
    "authorizationCode": "123456",
    "uniqueTransactionIdentifier": "...",
    "transactionEnrichmentIndicator": true,
    "secondaryCardTransactionIndicator": true,
    "transactionStatus": "PENDING"
},
{
    "transactionDate": "2025-05-25",
    "transactionPostingDate": "2025-05-26",
    "transactionType": "UNBILLED",
    "transactionAmount": {
        "amount": 100.00,
        "currencyCode": "CNY"
    },
    "transactionDescriptions": [
        "..."
    ],
    "cardNumber": "12345678901234567",
    "cardNumberDisplay": "12345678901234567",
    "cardNumberIdentifier": "...",
    "cardholderName": "NAME",
    "merchantCategoryCode": "1234",
    "transactionCreditDebitCode": "DEBIT_TRANSACTION",
    "realTimeTransactionDetails": {
        "transactionTime": "120721",
        "merchantName": "MERCHANT NAME",
        "merchantCity": "CITY",
        "merchantLocation": "CN",
        "authorizationType": "INTERNATIONAL",
        "merchantCountryCode": "CN"
    },
    "authorizationCode": "123456",
    "acquirerReferenceNumber": "00000000000000000000000",
    "uniqueTransactionIdentifier": "...",
    "transactionEnrichmentIndicator": true,
    "transactionDisputeIndicator": true,
    "secondaryCardTransactionIndicator": false,
    "transactionStatus": "HISTORIC",
    "transactionEnrichmentTypes": [
        "MERCHANT"
    ],
    "foreignCurrencyTransactionCreditDebitCode": "DEBIT_TRANSACTION"
},
        """
        if item["transactionStatus"] == "PENDING":
            continue

        txn_date = _parse_txn_date(item)
        if last_balance_date is not None and txn_date < last_balance_date:
            continue

        unique_no = _parse_unique_no(item)
        if unique_no in existed_unique_no_set:
            continue

        txn = _convert_transaction(item)
        txns.append(txn)

    return txns


def import_hsbc_hk_credit_card(items) -> int:
    txns = load_missing_transactions(os.path.join(current_app.ledger_root, "main.bean"), items["transactions"])

    return import_transactions(txns, current_app.doujia_config.categorize_config, current_app.doujia_config.import_to)


def import_hsbc_hk_credit_card_balance(resp) -> int:
    ledger_file = os.path.join(current_app.ledger_root, "main.bean")
    last_date = get_last_transaction_date(ledger_file, ACCOUNT)
    if last_date is None:
        return 0

    """
    ledgerBalance: {
        "amount": -123.45
        "currencyCode": "CNY",
    }
    """
    ledger_balance = resp["creditCardAccountDetail"]["ledgerBalance"]
    amount = data.Amount(
        Decimal(str(ledger_balance["amount"])).quantize(Decimal("0.01")), ledger_balance["currencyCode"]
    )
    balance_txn = insert_missing_balance(
        account=ACCOUNT,
        date=last_date + date.timedelta(days=1),
        amount=amount,
        ledger_file=ledger_file,
        import_to=current_app.doujia_config.import_to,
    )
    if balance_txn is None:
        return 0

    return 1
