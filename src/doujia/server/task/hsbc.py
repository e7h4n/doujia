from logzero import logger

from doujia.hsbc.hsbc_importer import import_unbilled_transactions
from doujia.server.app import FlaskApp


def import_hsbc(app: FlaskApp) -> bool:
    session = app.hsbc_session
    if session is None:
        return

    imported_count = import_unbilled_transactions(session)
    if imported_count > 0:
        logger.info(f"Imported {imported_count} unbilled transactions from HSBC")
