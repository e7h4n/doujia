import argparse

from beancount.core.data import Directive, Transaction
from beancount.core.interpolate import AUTOMATIC_META
from beancount.loader import load_file
from beancount.parser.printer import EntryPrinter


def _collect_posting_lines(
    entry: Transaction,  # type: ignore
    file_to_lines: dict[str, dict[int, list[str]]],
    printer: EntryPrinter,
) -> None:
    """收集需要填充的 posting 行"""
    if entry.flag == "#" or "filename" not in entry.meta:
        return

    for posting in entry.postings:
        if AUTOMATIC_META not in posting.meta:
            continue

        filename = entry.meta["filename"]
        if filename not in file_to_lines:
            file_to_lines[filename] = dict()

        line_to_replace = posting.meta["lineno"] - 1
        if line_to_replace not in file_to_lines[filename]:
            file_to_lines[filename][line_to_replace] = []

        posting_str = f"{printer.render_posting_strings(posting)[0]} {printer.render_posting_strings(posting)[1]}"
        file_to_lines[filename][line_to_replace].append(posting_str)


def _update_file_lines(filename: str, file_lines: dict[int, list[str]]) -> None:
    """更新文件内容"""
    with open(filename, encoding="utf-8") as f:
        lines = f.readlines()

    for line_no in sorted(file_lines.keys(), reverse=True):
        original_line = lines[line_no]
        indent = len(original_line) - len(original_line.lstrip())
        indent_str = " " * indent

        new_lines = []
        for posting in file_lines[line_no]:
            new_lines.append(indent_str + posting + "\n")

        lines[line_no : line_no + 1] = new_lines

    with open(filename, "w", encoding="utf-8") as f:
        f.writelines(lines)


def interpolate_postings(entries: list[Directive]):  # type: ignore
    file_to_lines: dict[str, dict[int, list[str]]] = dict()
    printer = EntryPrinter()

    # 收集需要填充的 posting 行
    for entry in entries:
        if isinstance(entry, Transaction):
            _collect_posting_lines(entry, file_to_lines, printer)

    # 更新文件内容
    for filename in file_to_lines:
        _update_file_lines(filename, file_to_lines[filename])


def main():
    arg_parser = argparse.ArgumentParser(description="Beancount posting filler.")
    arg_parser.add_argument(
        "--bean-file",
        dest="main_filename",
        type=str,
        required=True,
        help="Path to the main beancount file.",
    )

    args = arg_parser.parse_args()

    entries, _, _ = load_file(args.main_filename)

    interpolate_postings(entries)


if __name__ == "__main__":
    main()
