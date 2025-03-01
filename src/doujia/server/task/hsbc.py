import os

from logzero import logger

from doujia.hsbc.hsbc_importer import import_unbilled_transactions
from doujia.server.app import FlaskApp


def import_hsbc(app: FlaskApp) -> bool:
    session = app.hsbc_session
    if session is None:
        logger.info("HSBC session not found, skipping import")
        return

    ledger_file = os.path.join(app.ledger_root, "main.bean")
    imported_count = import_unbilled_transactions(
        ledger_file, session, app.doujia_config.categorize_config, app.doujia_config.import_to
    )
    if imported_count > 0:
        logger.info(f"Imported {imported_count} unbilled transactions from HSBC")
