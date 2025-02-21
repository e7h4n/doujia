import os
from dataclasses import dataclass
from typing import TypeVar

from beancount.core import data
from beancount.loader import load_file

Directive = TypeVar("Directive", bound=data.Directive)


@dataclass
class DoujiaConfig:
    categorize_config: str
    investment_config: str
    beangrow_config: str
    import_to: str
    import_account: str


def load_beancount(ledger_path: str) -> tuple[list[Directive], DoujiaConfig, dict]:
    entries, errors, options_map = load_file(ledger_path)
    if errors:
        raise ValueError(f"Beancount load errors: {errors}")

    config = DoujiaConfig(
        categorize_config="",
        investment_config="",
        beangrow_config="",
        import_to="",
        import_account="",
    )

    ledger_root = os.path.dirname(ledger_path)

    for entry in entries:
        if not isinstance(entry, data.Custom):
            continue
        if entry.type == "doujia-option":
            opt_key, opt_value = entry.values
            if opt_key.value == "categorize-config":
                config.categorize_config = os.path.abspath(
                    os.path.join(ledger_root, opt_value.value)
                )
            elif opt_key.value == "investment-config":
                config.investment_config = os.path.abspath(
                    os.path.join(ledger_root, opt_value.value)
                )
            elif opt_key.value == "beangrow-config":
                config.beangrow_config = os.path.abspath(
                    os.path.join(ledger_root, opt_value.value)
                )
            elif opt_key.value == "import-to":
                config.import_to = os.path.abspath(
                    os.path.join(ledger_root, opt_value.value)
                )

    return entries, config, options_map
