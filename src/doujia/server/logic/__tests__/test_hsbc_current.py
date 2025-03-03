from datetime import date

from doujia.server.logic.hsbc_current import _convert_transaction


def test_convert_item():
    txn = _convert_transaction(
        [
            "2025年3月3日",
            [
                "转账",
                "ABC123123",
                "系统生成",
            ],
            123.45,
            0,
        ]
    )

    assert txn.payee == "转账#ABC123123#系统生成"
    assert txn.date == date(2025, 3, 3)
    assert txn.postings[0].units.number == 123.45
    assert txn.meta["uniqueNo"] == "HSBC_CURRENT_ABC123123"
