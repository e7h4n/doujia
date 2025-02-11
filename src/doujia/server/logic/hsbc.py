import io
from datetime import datetime
import json

from beancount.core import data
from beancount.core.number import D
from beancount.loader import load_file
from beancount.parser import printer
from beancount.scripts.format import align_beancount
from flask import current_app
import requests

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


def parse_amount_from_hsbc_item(amount_str: str) -> data.Amount:
    if amount_str.startswith("￥"):
        currency = "CNY"
        amount = D(amount_str[1:].replace(",", ""))
    elif amount_str.startswith("$"):
        currency = "USD"
        amount = D(amount_str[1:].replace(",", ""))
    else:
        currency = "CNY"
        amount = D(amount_str.replace(",", ""))

    return data.Amount(amount, currency)


def convert_hsbc_item_to_postings(item):
    amount = parse_amount_from_hsbc_item(item["amount"])

    out_posting = data.Posting(
        account="Liabilities:Short:CreditCard:HSBC",
        units=data.Amount(-amount.number, amount.currency),
        cost=None,
        price=None,
        flag=None,
        meta=None,
    )

    return [out_posting, DEFAULT_UFO_POSTING]


def load_missing_transactions_from_hsbc_items(filename, items):
    last_balance_date = get_last_balance_date(
        filename, "Liabilities:Short:CreditCard:HSBC"
    )
    existed_unique_no_set = get_existed_unique_no_set(filename)

    txns = []
    for item in items:
        """item
        {
            "pur_DateTime": "2025-02-11 07:34:25",
            "amount": "￥288.00",
            "cardEND": "0000",
            "descline2": "                         ",
            "descline1": "WLZF-京东支付-京东商城业务                                         ",
            "currNum": "156",
        }
        """
        txn_date = datetime.strptime(item["pur_DateTime"], "%Y-%m-%d %H:%M:%S").date()
        if last_balance_date is not None and txn_date < last_balance_date:
            continue

        # 生成唯一标识进行检查
        datetime_obj = datetime.strptime(item["pur_DateTime"], "%Y-%m-%d %H:%M:%S")
        amount = parse_amount_from_hsbc_item(item["amount"])
        unique_no = (
            f"HSBC_{int(datetime_obj.timestamp())}_{amount.number}_{amount.currency}"
        )

        if unique_no in existed_unique_no_set:
            continue

        txn = convert_hsbc_item_to_transaction(item)
        txns.append(txn)
    return txns


def convert_hsbc_item_to_transaction(item):
    description = item["descline1"].strip() + " " + item["descline2"].strip()
    postings = convert_hsbc_item_to_postings(item)

    # 解析日期时间
    datetime_obj = datetime.strptime(item["pur_DateTime"], "%Y-%m-%d %H:%M:%S")
    txn_date = datetime_obj.date()

    # 生成新的唯一标识
    amount = parse_amount_from_hsbc_item(item["amount"])
    unique_no = (
        f"HSBC_{int(datetime_obj.timestamp())}_{amount.number}_{amount.currency}"
    )

    transaction = data.Transaction(
        data.new_metadata(
            None,
            None,
            {
                "time": datetime_obj.strftime("%H:%M:%S"),
                "card": item["cardEND"],
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


def get_existed_unique_no_set(main_file_path):
    entries, _, _ = load_file(main_file_path)

    unique_no_set = set()
    for entry in entries:
        if isinstance(entry, data.Transaction) and "uniqueNo" in entry.meta:
            unique_no_set.add(entry.meta["uniqueNo"])

    return unique_no_set


def load_hsbc_html_content(html: str):
    # 查找包含 var unBillDetail = 的行
    for line in html.splitlines():
        if "var unBillDetail = " in line:
            # 从 = 后面开始截取，去掉末尾的分号
            json_str = line.split("=", 1)[1].strip().rstrip(";")
            data = json.loads(json_str)
            break

    return data


def get_hsbc_items(data: dict) -> list[dict]:
    return data["orderINFO"]


def fetch_hsbc_html_content(url: str) -> dict:
    with requests.get(url) as response:
        html = response.text

    return load_hsbc_html_content(html)


def import_hsbc_transactions(url: str) -> int:
    html = fetch_hsbc_html_content(url)
    items = get_hsbc_items(html)
    txns = load_missing_transactions_from_hsbc_items("main.bean", items)

    with io.StringIO() as output:
        for txn in txns:
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
