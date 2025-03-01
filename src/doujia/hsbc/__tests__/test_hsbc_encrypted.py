from datetime import date
from decimal import Decimal

import pytest

from doujia.hsbc.hsbc_importer import (
    HSBCSession,
    _convert_transaction,
    _parse_txn_date,
    _parse_unique_no,
    _query_unbilled_transactions,
)


def test_parse_txn_date():
    item = {
        "newTransDate": "20250228",
        "transTime": "21140168",
        "cardEnd": "7326",
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

    txn_date = _parse_txn_date(item)

    assert txn_date == date(2025, 2, 28)


def test_generate_unique_no():
    item = {
        "newTransDate": "20250228",
        "transTime": "21140168",
        "cardEnd": "7326",
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

    unique_no = _parse_unique_no(item)

    assert unique_no == "HSBC_20250228_300508"


def test_convert_hsbc_item_to_transaction():
    item = {
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

    txn = _convert_transaction(item)

    assert txn.meta["time"] == "21:14:01"
    assert txn.meta["card"] == "1234"
    assert txn.meta["uniqueNo"] == "HSBC_20250228_300508"
    assert txn.payee == "WLZF-京东支付-京东商城业务"
    assert len(txn.postings) == 2
    assert txn.postings[0].units.number == Decimal("-164.98")
    assert txn.postings[0].units.currency == "CNY"


@pytest.mark.skip
def test_query_hsbc():
    session = HSBCSession(
        authorization="",
        authorizationguest="",
    )
    trans = _query_unbilled_transactions(session)

    assert len(trans) > 0
