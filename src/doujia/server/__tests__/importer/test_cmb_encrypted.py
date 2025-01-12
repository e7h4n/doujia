from datetime import date

from beancount.core.data import D

from doujia.server.logic.cmb_encrypted import (
    convert_cmb_item_to_postings,
    convert_cmb_item_to_transaction,
    load_missing_transactions_from_cmb_items,
)


def test_convert_cmb_encrypted_item_to_postings():
    item = {
        "id": "WLXTAN11040X7020000XXXXX",
        "iconNo": "002",
        "tranSummary": "支付宝-中贡华联超市",
        "tranType": "购物百货",
        "tranDate": "11-05",
        "tranTime": "",
        "tranCard": "尾号****",
        "tranDateTime": "20241105135030",
        "currency": "156",
        "amount": "16.70",
        "amountPositive": "Y",
        "modifyCategoryFlag": "Y",
        "subTranSummary": "支付宝-中贡华联超市",
        "showNote": "Y",
        "showQuestionTrans": "N",
        "tranDetailJumpFlag": "N",
    }

    posting = convert_cmb_item_to_postings(item)[0]

    assert abs(posting.units.number - D(-16.70)) < 0.01
    assert posting.units.currency == "CNY"
    assert posting.price is None


def test_convert_cmb_encrypted_item_to_transaction():
    item = {
        "id": "WLXTAN11030X7020000XXXXX",
        "iconNo": "013",
        "tranSummary": "财付通-MESCAPE蜜逃",
        "tranType": "其他",
        "tranDate": "11-05",
        "tranTime": "",
        "tranCard": "尾号****",
        "tranDateTime": "20241105125732",
        "currency": "156",
        "amount": "49.80",
        "amountPositive": "Y",
        "inBill": "0",
        "modifyCategoryFlag": "Y",
        "subTranSummary": "财付通-MESCAPE蜜逃",
        "showNote": "Y",
        "showQuestionTrans": "N",
        "originData": "...",
        "extInfo": "...",
        "tranDetailJumpFlag": "N",
    }

    txn = convert_cmb_item_to_transaction(item)
    assert txn.flag == "!"
    assert txn.payee == "财付通-MESCAPE蜜逃"
    assert txn.narration is None
    assert txn.tags == frozenset()
    assert txn.links == frozenset()
    assert txn.date == date(2024, 11, 5)
    assert txn.meta["time"] == "12:57:32"
    assert txn.meta["card"] == "****"
    assert txn.meta["uniqueNo"] == "CMB_WLXTAN11030X7020000XXXXX"


def test_convert_cmb_encrypted_item_to_transaction_2():
    item = {
        "id": "3956555.002024XXXXXXXXXX",
        "iconNo": "013",
        "tranSummary": "Paypal",
        "tranType": "其他",
        "tranDate": "11-10",
        "tranTime": "",
        "tranCard": "尾号****",
        "tranDateTime": "20241110190455",
        "currency": "840",
        "amount": "5.00",
        "amountPositive": "Y",
        "inBill": "0",
        "modifyCategoryFlag": "Y",
        "subTranSummary": "Paypal",
        "showNote": "Y",
        "showQuestionTrans": "N",
        "tranDetailJumpFlag": "N",
    }

    txn = convert_cmb_item_to_transaction(item)
    assert txn.flag == "!"
    assert txn.payee == "Paypal"
    assert txn.narration is None
    assert txn.tags == frozenset()
    assert txn.links == frozenset()
    assert txn.date == date(2024, 11, 10)
    assert txn.meta["time"] == "19:04:55"
    assert txn.meta["card"] == "****"
    assert txn.meta["uniqueNo"] == "CMB_3956555.002024XXXXXXXXXX"
    assert txn.postings[0].units.number == D(-5.00)
    assert txn.postings[0].units.currency == "USD"


def test_convert_cmb_encrypted_item_to_transaction_nz(fs):
    item = {
        "id": "8357881718.002024XXXXXXXXXX",
        "iconNo": "013",
        "tranSummary": "Wanaka River Journeys Haast           NZ",
        "tranType": "其他",
        "tranDate": "11-22",
        "tranTime": "",
        "tranCard": "尾号****",
        "tranDateTime": "20241122162155",
        "currency": "840",
        "amount": "1011.56",
        "amountPositive": "Y",
        "inBill": "0",
        "modifyCategoryFlag": "Y",
        "subTranSummary": "Wanaka River Journeys Haast           NZ",
        "showNote": "Y",
        "showQuestionTrans": "N",
        "tranDetailJumpFlag": "N",
    }

    txn = convert_cmb_item_to_transaction(item)
    assert txn.flag == "!"
    assert txn.payee == "Wanaka River Journeys Haast           NZ"
    assert txn.narration is None
    assert abs(txn.postings[0].units.number - D(-1011.56)) < 0.01
    assert txn.postings[0].units.currency == "USD"


def test_load_missing_transactions_balance_date(fs):
    fs.create_file(
        "main.bean",
        contents="""
1970-01-01 open Liabilities:CreditCard:CMB

2024-11-05 balance Liabilities:CreditCard:CMB -72935.49 CNY

2024-01-25 *
    uniqueNo: "CMB_foo"
    Liabilities:CreditCard:CMB  -18.00 CNY
    Equity:UFO
""",
    )

    txns = load_missing_transactions_from_cmb_items(
        "main.bean",
        [
            {
                "id": "foo",
                "iconNo": "002",
                "tranSummary": "支付宝-北京友宝昂莱科技有限公司",
                "tranType": "购物百货",
                "tranDate": "11-05",
                "tranTime": "",
                "tranCard": "尾号xxxx",
                "tranDateTime": "20241105121714",
                "currency": "156",
                "amount": "8.70",
                "amountPositive": "Y",
                "inBill": "0",
                "modifyCategoryFlag": "Y",
                "subTranSummary": "支付宝-北京友宝昂莱科技有限公司",
                "showNote": "Y",
                "showQuestionTrans": "N",
                "originData": "...",
                "extInfo": "...",
                "tranDetailJumpFlag": "N",
            }
        ],
    )

    assert len(txns) == 0
