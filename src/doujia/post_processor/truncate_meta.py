import argparse
from beancount.core.data import Balance, Directive, Transaction
from beancount.loader import load_file


def truncate_meta(entries: list[Directive], account: str = "Liabilities:Short:CreditCard:CMB"):  # type: ignore
    last_balance_date = None

    for entry in reversed(entries):
        if isinstance(entry, Balance) and entry.account == account:
            last_balance_date = entry.date
            break

    files_to_truncate: dict[str, list[int]] = dict()

    for entry in entries:
        if isinstance(entry, Transaction) and entry.date < last_balance_date:
            if "uniqueNo" not in entry.meta:
                continue

            lineno = entry.meta["lineno"]
            filename = entry.meta["filename"]
            files_to_truncate.setdefault(filename, []).append(lineno)

    for filename, linenos in files_to_truncate.items():
        with open(filename, "r", encoding="utf-8") as f:
            lines = f.readlines()

        for lineno in reversed(linenos):
            for idx in range(3):
                remove_lineno = lineno + 2 - idx
                lines.pop(remove_lineno)

        with open(filename, "w", encoding="utf-8") as f:
            f.writelines(lines)


def main():
    arg_parser = argparse.ArgumentParser(description="Beancount posting filler.")

    arg_parser.add_argument(
        "--bean-file",
        dest="main_filename",
        type=str,
        required=True,
        help="Path to the main beancount file.",
    )
    arg_parser.add_argument(
        "--account",
        dest="account",
        type=str,
        required=True,
        help="Account to truncate meta.",
    )

    args = arg_parser.parse_args()

    entries, _, _ = load_file(args.main_filename)

    truncate_meta(entries, args.account)


if __name__ == "__main__":
    main()
