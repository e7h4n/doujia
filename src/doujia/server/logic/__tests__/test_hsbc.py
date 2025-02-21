import os

from doujia.server.logic.hsbc import (
    get_hsbc_items,
    load_hsbc_html_content,
)


def test_hsbc_wechat_importer():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, "hsbc.html")

    with open(file_path, encoding="gbk") as f:
        html = f.read()

    data = load_hsbc_html_content(html)

    assert "bankNum" in data
    assert "cardNum" in data
    assert "orderINFO" in data
    assert len(data["orderINFO"]) > 0


def test_hsbc_wechat_importer_items():
    data = {
        "bankNum": "0321",
        "cardNum": "5000000000000000",
        "tranYM": None,
        "addAllAmt": "￥288.00",
        "rtnMsg": "SUCCESS",
        "orderINFO": [
            {
                "pur_DateTime": "2025-02-11 07:34:25",
                "amount": "￥288.00",
                "cardEND": "0000",
                "descline2": "                         ",
                "descline1": "WLZF-京东支付-京东商城业务                                         ",
                "currNum": "156",
            }
        ],
        "addAllAmtDol": "$0.00",
    }

    items = get_hsbc_items(data)
    assert len(items) == 1
