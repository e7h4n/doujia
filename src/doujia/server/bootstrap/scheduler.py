from flask import Flask
from flask_apscheduler import APScheduler
from logzero import logger

from doujia.server.task.hsbc import import_hsbc
from doujia.server.task.ledger import reload_ledger
from doujia.server.task.price import update_price_cache


def setup_scheduler(app: Flask):
    logger.debug("Setting up scheduler")

    scheduler = APScheduler()

    @scheduler.task("interval", id="reload_ledger", seconds=3, max_instances=1, coalesce=True)
    def scheduler_reload_ledger():
        reload_ledger(app)

    @scheduler.task("interval", id="reload_price_cache", minutes=1, max_instances=1, coalesce=True)
    def scheduler_reload_price_cache():
        update_price_cache(app)

    @scheduler.task("interval", id="import_hsbc", minutes=3, max_instances=1, coalesce=True)
    def scheduler_import_hsbc():
        import_hsbc(app)

    if not app.config.get("TESTING"):
        try:
            logger.debug("Starting scheduler")
            scheduler.init_app(app)
            scheduler.start()
            logger.info("Scheduler started successfully")
        except Exception as e:
            logger.error(f"Failed to start scheduler: {e!s}")
            raise
