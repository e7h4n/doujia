"""处理招行导入的一些工具类"""

from beancount.core.data import Balance, Transaction
from beancount.loader import load_file


def get_last_balance_date(main_file_path, account_name):
    """获取文档中对应账户最后一次对账的时间"""

    entries, _, _ = load_file(main_file_path)
    last_balance_date = None

    for entry in reversed(entries):
        if isinstance(entry, Balance) and entry.account == account_name:
            last_balance_date = entry.date
            break

    return last_balance_date


def get_last_transaction_date(main_file_path, account_name):
    """获取文档中对应账户最后一次交易的时间"""

    entries, _, _ = load_file(main_file_path)
    last_transaction_date = None

    for entry in reversed(entries):
        if isinstance(entry, Transaction):
            found = False
            for posting in entry.postings:
                if posting.account == account_name:
                    found = True
                    break
            if found:
                last_transaction_date = entry.date
                break

    return last_transaction_date
