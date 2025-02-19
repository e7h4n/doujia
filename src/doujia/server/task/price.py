from beancount.core.getters import get_commodity_directives
from flask import app as default_app
from doujia.price.yahoo import update_price_cache as update_price_cache_from_yahoo
from logzero import logger

from doujia.server.app import FlaskApp
from doujia.server.task.scheduler import scheduler


@scheduler.task("interval", id="update_price_cache", minutes=1)
def schedule_update_price_cache():
    update_price_cache(default_app)


def update_price_cache(app: FlaskApp) -> None:
    try:
        commodity_map = get_commodity_directives(app.entries)
        symbols = dict()
        for currency, commodity in commodity_map.items():
            if "price" in commodity.meta and "yahoo/" in commodity.meta["price"]:
                symbols[currency] = commodity.meta["price"].split("/")[-1]

        if symbols:
            update_price_cache_from_yahoo(list(symbols.values()))
            logger.info("Successfully updated price cache")
    except Exception as e:
        logger.error(f"Failed to update price cache: {e}")
