import hashlib
import os
import re
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
    # txnDetail: ["...", "2025052796400392", "..."]
    # or
    # txnDetail: ["...", "Submitted on: 23MAY25", "10:32:07", "..."]

    # 尝试从 txnDetail 中解析日期
    txn_detail = item.get("txnDetail", [])

    for detail in txn_detail:
        # 尝试解析 "2025052796400392" 格式 (前8位是日期)
        if re.match(r"^\d{14}$", detail):
            date_part = detail[:8]  # 前8位
            try:
                year = int(date_part[:4])
                month = int(date_part[4:6])
                day = int(date_part[6:8])
                return datetime(year, month, day).date()
            except ValueError:
                continue

        # 尝试解析 "Submitted on: 23MAY25" 格式
        submitted_match = re.search(r"Submitted on:\s*(\d{2})([A-Z]{3})(\d{2})", detail)
        if submitted_match:
            day = int(submitted_match.group(1))
            month_str = submitted_match.group(2)
            year = int("20" + submitted_match.group(3))  # 假设是21世纪

            # 月份缩写映射
            month_map = {
                "JAN": 1,
                "FEB": 2,
                "MAR": 3,
                "APR": 4,
                "MAY": 5,
                "JUN": 6,
                "JUL": 7,
                "AUG": 8,
                "SEP": 9,
                "OCT": 10,
                "NOV": 11,
                "DEC": 12,
            }

            if month_str in month_map:
                try:
                    month = month_map[month_str]
                    return datetime(year, month, day).date()
                except ValueError:
                    continue

    # 如果从 txnDetail 中找不到日期, 使用 txnDate
    date_str = item["txnDate"]
    year = int(date_str.split("-")[0])
    month = int(date_str.split("-")[1])
    day = int(date_str.split("-")[2].split(" ")[0])

    return datetime(year, month, day).date()


def _parse_time(item):
    # 尝试从 txnDetail 中解析时间
    txn_detail = item.get("txnDetail", [])

    for detail in txn_detail:
        # 尝试解析 "10:32:07" 格式
        time_match = re.match(r"^(\d{2}):(\d{2}):(\d{2})$", detail)
        if time_match:
            return detail

    return None


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
                "time": _parse_time(item) or "",
                "card": "",
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
        # 从前往后找到第一条 txn_date < 当天日期的交易
        today = datetime.now().date()
        last_balance_item = None
        for item in items:
            txn_date = _parse_txn_date(item)
            if txn_date < today:
                last_balance_item = item
                break

        # 如果没有找到合适的项目, 使用第一个项目
        if last_balance_item is not None:
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
