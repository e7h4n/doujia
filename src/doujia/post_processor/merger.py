"""beancount 记录合成器"""

import argparse
import io
import sys
from collections import defaultdict
from datetime import datetime

from beancount.core.data import Balance, Transaction
from beancount.parser import parser, printer


def _merge_beancount_content(main_content: str, imported_content: str, output: io.StringIO):
    main_lines = main_content.splitlines()

    imported_entries = _parse_beancount_file(imported_content)
    sorted_entries = _sort_imported_entries(imported_entries)

    merged_lines = _merge_entries(main_lines, sorted_entries)
    output.write("\n".join(merged_lines))


def _merge_beancount_file(main_filename: str, imported_filename: str, output: io.StringIO):
    main_content = _read_file(main_filename)
    imported_content = _load_content(imported_filename)

    _merge_beancount_content(main_content, imported_content, output)


def _read_file(file_path: str) -> str:
    with open(file_path, encoding="utf-8") as f:
        content = f.read()
    return content


def _load_content(file_path: str):
    if file_path == "-":
        file_content = sys.stdin.read()
    else:
        with open(file_path, encoding="utf-8") as opened_file:
            file_content = opened_file.read()

    return file_content


def _parse_beancount_file(file_content: str):
    entries, _, _ = parser.parse_string(file_content)

    return entries


def _sort_imported_entries(entries):
    entries_by_date = defaultdict(list)

    for entry in entries:
        if isinstance(entry, Transaction | Balance):
            entries_by_date[entry.date].append(entry)

    for _, date_entries in entries_by_date.items():
        date_entries.sort(
            key=lambda x: (
                x.date,
                isinstance(x, Balance),
            )
        )

    return entries_by_date


def _find_balance_insert_position(main_lines: list[str], start_index: int, target_date) -> int:
    """找到 balance 记录的位置, 并在这个位置之后找到同日期交易的最后一笔记录后的位置"""

    first_balance_position = None
    start_index = min(start_index, len(main_lines) - 1)

    for index in range(start_index, -1, -1):
        line = main_lines[index]
        balance_date = _get_balance_date_from_line(line)
        line_date = _get_date_from_line(line)

        if balance_date and balance_date == target_date:
            first_balance_position = index + 1
            break
        elif balance_date and balance_date < target_date and first_balance_position is None:
            first_balance_position = index + 1
            break
        elif balance_date is None and line_date and line_date < target_date:
            # 从 index 开始查找到第一个空行或者下一个包含日期的行
            next_line = index + 1
            while next_line < len(main_lines):
                if main_lines[next_line] == "":
                    break

                next_line_date = _get_date_from_line(main_lines[next_line])
                if next_line_date:
                    break

                next_line += 1

            first_balance_position = next_line
            break

    return first_balance_position or 0


def _find_transaction_insert_position(main_lines, insert_position, target_date) -> int:
    # 从 insert_position 开始往下查找, 找到第一个包含日期但不等于 target_date 的记录位置
    for index in range(insert_position, len(main_lines)):
        line = main_lines[index]
        current_date = _get_date_from_line(line)

        if current_date and current_date != target_date:
            return index

    return len(main_lines)


def _find_insert_position(main_lines: list[str], start_index: int, target_date) -> int:
    """找到 balance 记录的位置, 并在这个位置之后找到同日期交易的最后一笔记录后的位置"""

    balance_insert_position = _find_balance_insert_position(main_lines, start_index, target_date)

    return _find_transaction_insert_position(main_lines, balance_insert_position, target_date)


def _insert_entries(main_lines, entries, insert_position):
    last_insert_balance = False
    for entry in entries:
        last_insert_balance = isinstance(entry, Balance)
        main_lines.insert(insert_position, "")
        main_lines.insert(insert_position, printer.format_entry(entry)[:-1])

    if not last_insert_balance:
        main_lines.insert(insert_position, "")


def _merge_entries(main_lines: list[str], sorted_entries) -> list[str]:
    main_line_index = len(main_lines) - 1
    sorted_entries_items = sorted(sorted_entries.items(), reverse=True)

    for import_date, date_entries in sorted_entries_items:
        balances = []
        transactions = []

        for entry in date_entries:
            if isinstance(entry, Balance):
                balances.append(entry)
            else:
                transactions.append(entry)

        balance_insert_position = _find_balance_insert_position(main_lines, main_line_index, import_date)

        if len(balances) > 0:
            _insert_entries(main_lines, balances, balance_insert_position)

        transaction_insert_position = _find_transaction_insert_position(
            main_lines, balance_insert_position, import_date
        )

        if len(transactions) > 0:
            _insert_entries(main_lines, transactions, transaction_insert_position)

    cleaned_line_index = len(main_lines) - 1
    while cleaned_line_index > 0:
        if len(main_lines[cleaned_line_index - 1]) == 0 and len(main_lines[cleaned_line_index]) == 0:
            del main_lines[cleaned_line_index]

        cleaned_line_index -= 1

    return main_lines


def _get_date_from_line(line: str) -> datetime.date:
    # 尝试在 line 中查找 \d{4}-\d{2}-\d{2} 格式的日期
    # 如果找到, 返回 datetime.date 对象
    # 如果找不到, 返回 None

    parts = line.split()
    if parts and parts[0].count("-") == 2:
        try:
            return datetime.strptime(parts[0], "%Y-%m-%d").date()
        except ValueError:
            pass
    return None


def _get_balance_date_from_line(line: str):
    if line.find(" balance ") == -1:
        return None

    return _get_date_from_line(line)


def main():
    """
    Main function of the Beancount entries merger script.
    Parses command-line arguments and invokes _merge_beancount_file function
    to merge the main Beancount file with the entries read from standard input.
    Outputs the merged content to standard output.
    """

    arg_parser = argparse.ArgumentParser(description="Beancount entries merger.")
    arg_parser.add_argument(
        "--bean-file",
        dest="main_filename",
        type=str,
        required=True,
        help="Path to the main beancount file.",
    )

    args = arg_parser.parse_args()

    _merge_beancount_file(args.main_filename, "-", sys.stdout)


if __name__ == "__main__":
    main()
