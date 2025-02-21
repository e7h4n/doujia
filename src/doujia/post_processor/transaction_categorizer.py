"""账本的自动分类器"""

import re
import sys

from beancount.core.data import Balance, D, Posting, Transaction
from beancount.core.number import MISSING
from beancount.parser import parser
from beancount.parser.printer import format_entry


def _decimals_almost_equal(lhs, rhs):
    return abs(lhs - rhs) < 0.001


class Rule:
    """匹配规则"""

    def __init__(
        self,
        account: str,
        matcher: dict[str, str | None],
        target: dict[str, str | None],
    ):
        self.account = account
        self.matcher = matcher
        self.target = target

    def __repr__(self):
        return f"Rule(account={self.account}, matcher={self.matcher}, target={self.target})"

    def __eq__(self, other):
        if not isinstance(other, Rule):
            return False

        return self.account == other.account and self.matcher == other.matcher and self.target == other.target


def _is_transaction_matching_rule(transaction: Transaction, rule: Rule) -> bool:
    # 检查摘要是否匹配
    if rule.matcher["summary"] not in transaction.payee and rule.matcher["summary"] not in transaction.narration:
        return False

    # 检查金额是否匹配 (如果需要)
    if rule.matcher["amount"] is not None:
        for posting in transaction.postings:
            if posting.units is not MISSING and _decimals_almost_equal(posting.units.number, rule.matcher["amount"]):
                return True

        return False

    return True


def _apply_rule_to_transaction(transaction: Transaction, rule: Rule) -> Transaction:
    # 修改 postings 中的去向账户
    modified_postings = []
    for posting in transaction.postings:
        if posting.account.startswith("Equity:UFO"):
            modified_postings.append(
                Posting(
                    account=rule.account,
                    units=posting.units,
                    cost=posting.cost,
                    price=posting.price,
                    flag=posting.flag,
                    meta=posting.meta,
                )
            )
        else:
            modified_postings.append(posting)

    # 使用原始 transaction 和 rule.target 的字段创建一个新的 Transaction 对象
    modified_transaction = Transaction(
        date=transaction.date,
        flag=rule.target["flag"] if rule.target["flag"] is not None else "*",
        payee=(rule.target["payee"] if rule.target["payee"] is not None else transaction.payee),
        narration=(rule.target["narration"] if rule.target["narration"] is not None else transaction.narration),
        tags=transaction.tags,
        links=transaction.links,
        postings=modified_postings,
        meta=transaction.meta,
    )
    return modified_transaction


def _process_beancount(input_string, rules, output_file):
    entries, _, _ = parser.parse_string(input_string)

    for entry in entries:
        if isinstance(entry, Transaction):
            for rule in rules:
                if _is_transaction_matching_rule(entry, rule):
                    entry = _apply_rule_to_transaction(entry, rule)
                    break

            output_file.write(format_entry(entry) + "\n")
        elif isinstance(entry, Balance):
            output_file.write(format_entry(entry) + "\n")


def _parse_beancount_converter_dsl(dsl: str) -> list[Rule]:
    rules = []
    current_account = None

    for line in dsl.splitlines():
        if not line:
            continue

        if not line.startswith(" "):  # Account line
            current_account = line
            continue

        if "->" in line:  # Rule line
            matcher = {}
            target = {}
            rules.append(Rule(current_account, matcher, target))

            matcher["summary"] = re.search(r'"(.*?)"', line).group(1)
            if "amount" in line:
                matcher["amount"] = D(float(re.search(r"amount (\S+)", line).group(1)))
            else:
                matcher["amount"] = None

            target["payee"] = re.search(r'payee "(.*?)"', line)
            target["narration"] = re.search(r'narration "(.*?)"', line)
            target["flag"] = re.search(r'flag "(.*?)"', line)

            for key in target:
                if target[key] is not None:
                    target[key] = target[key].group(1)
        else:
            continue

    return rules


def _categorize_transactions(config, input_string, output_io):
    # 读取规则文件
    try:
        with open(config, encoding="utf-8") as file:
            dsl = file.read()

        # 解析规则
        rules = _parse_beancount_converter_dsl(dsl)
    except FileNotFoundError:
        rules = []

    _process_beancount(input_string, rules, output_io)


def main():
    input_string = sys.stdin.read()
    output_io = sys.stdout

    _categorize_transactions("./config/main.bconv", input_string, output_io)


if __name__ == "__main__":
    main()
