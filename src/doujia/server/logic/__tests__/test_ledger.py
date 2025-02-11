from beancount.core import data
from typing import TypeVar

from doujia.server.logic.ledger import load_beancount

Directive = TypeVar("Directive", bound=data.Directive)


def test_options(doc_fs_ledger_filename: str):
    """
    @@@/tmp/ledgers/main.bean
    2025-01-12 custom "doujia-option" "categorize-config" "../config/main.bconv"
    2025-01-12 custom "doujia-option" "investment-config" "../config/investment_distribution.yaml"
    2025-01-12 custom "doujia-option" "beangrow-config" "../config/beangrow.pbtxt"
    2025-01-12 custom "doujia-option" "import-to" "../ledgers/main.bean"
    2025-01-12 custom "doujia-option" "import-account" "Liabilities:Short:CreditCard:CMB"
    """

    _, config, _ = load_beancount(doc_fs_ledger_filename)

    assert config.categorize_config == "/tmp/config/main.bconv"
    assert config.investment_config == "/tmp/config/investment_distribution.yaml"
    assert config.beangrow_config == "/tmp/config/beangrow.pbtxt"
    assert config.import_to == "/tmp/ledgers/main.bean"
