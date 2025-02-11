from dataclasses import dataclass
import os
from beancount.core import data
from typing import TypeVar, Tuple
from beancount.loader import load_file

Directive = TypeVar("Directive", bound=data.Directive)


@dataclass
class DoujiaConfig:
    categorize_config: str
    investment_config: str
    beangrow_config: str
    import_to: str
    import_account: str


def load_beancount(ledger_path: str) -> Tuple[list[Directive], DoujiaConfig, dict]:
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
            optKey, optValue = entry.values
            if optKey.value == "categorize-config":
                config.categorize_config = os.path.abspath(
                    os.path.join(ledger_root, optValue.value)
                )
            elif optKey.value == "investment-config":
                config.investment_config = os.path.abspath(
                    os.path.join(ledger_root, optValue.value)
                )
            elif optKey.value == "beangrow-config":
                config.beangrow_config = os.path.abspath(
                    os.path.join(ledger_root, optValue.value)
                )
            elif optKey.value == "import-to":
                config.import_to = os.path.abspath(
                    os.path.join(ledger_root, optValue.value)
                )

    return entries, config, options_map
