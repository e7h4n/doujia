import os

from flask import app as default_app
from doujia.server.app import FlaskApp
from doujia.server.logic.ledger import load_beancount
from logzero import logger

from doujia.server.task.scheduler import scheduler


def reload_ledger(app: FlaskApp) -> bool:
    """
    重新加载 beancount 文件
    返回是否加载成功
    """
    ledger_path = os.path.join(app.ledger_root, "main.bean")
    entries, doujia_config, options_map = load_beancount(ledger_path)

    app.entries = entries
    app.options_map = options_map
    app.doujia_config = doujia_config

    logger.info("Successfully reloaded beancount file")
    return True


@scheduler.task("interval", id="reload_beancount", minutes=10)
def schedule_reload_ledger():
    reload_ledger(default_app)
