import os

from flask_cors import CORS
from flask import Flask
from flask_apscheduler import APScheduler
from doujia.server.app import FlaskApp
from doujia.server.controller.portfolio import bp as portfolio_bp
from doujia.server.controller.importer import bp as importer_bp
from doujia.server.controller.balance import bp as balance_bp
from corbado_python_sdk import (
    Config,
    CorbadoSDK,
    SessionService,
)
from logzero import setup_default_logger, INFO, logger
from beancount.core.getters import get_commodity_directives
from doujia.price.yahoo import update_price_cache
from doujia.server.logic.ledger import load_beancount

DEFAULT_CORBADO_PROJECT_ID = "pro-8910668211600497001"

scheduler = APScheduler()


def init_corbado(app: FlaskApp):
    if "CORBADO_API_SECRET" not in app.config:
        app.corbado = None
        app.sessions = None
        return

    if app.config["CORBADO_API_SECRET"] == "test-secret":
        return

    config = Config(
        project_id=app.config["CORBADO_PROJECT_ID"],
        api_secret=app.config["CORBADO_API_SECRET"],
    )
    sdk: CorbadoSDK = CorbadoSDK(config=config)
    sessions: SessionService = sdk.sessions

    app.corbado = sdk
    app.sessions = sessions


def reload_beancount(app: FlaskApp) -> bool:
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


def init_beancount(app: FlaskApp):
    """初始化时加载 beancount 文件"""
    if not reload_beancount(app):
        raise ValueError("Failed to load beancount file during initialization")


def create_app(test_config=None):  # noqa: C901
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(SECRET_KEY="dev")

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_object("doujia.server.config")
        setup_default_logger(level=INFO)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    if "CORBADO_PROJECT_ID" not in app.config:
        app.config["CORBADO_PROJECT_ID"] = DEFAULT_CORBADO_PROJECT_ID

    if "CORBADO_API_SECRET" in os.environ:
        app.config["CORBADO_API_SECRET"] = os.environ["CORBADO_API_SECRET"]
    if "LEDGER_ROOT" in os.environ:
        app.ledger_root = os.path.abspath(os.environ["LEDGER_ROOT"])
    elif "LEDGER_ROOT" in app.config:
        app.ledger_root = os.path.abspath(app.config["LEDGER_ROOT"])
    else:
        app.ledger_root = os.path.abspath(os.getcwd())

    init_corbado(app)

    # 添加调度器配置
    app.config["SCHEDULER_API_ENABLED"] = True

    # 初始化调度器
    scheduler.init_app(app)
    if not app.config.get("TESTING"):
        scheduler.start()

    # 添加定时任务
    @scheduler.task("interval", id="reload_beancount", minutes=10)
    def scheduled_reload():
        reload_beancount(app)

    # 添加价格更新的定时任务
    @scheduler.task("interval", id="update_price_cache", minutes=1)
    def scheduled_update_price_cache():
        try:
            commodity_map = get_commodity_directives(app.entries)
            symbols = dict()
            for currency, commodity in commodity_map.items():
                if "price" in commodity.meta and "yahoo/" in commodity.meta["price"]:
                    symbols[currency] = commodity.meta["price"].split("/")[-1]

            if symbols:
                update_price_cache(list(symbols.values()))
                logger.info("Successfully updated price cache")
        except Exception as e:
            logger.error(f"Failed to update price cache: {e}")

    scheduled_reload()
    scheduled_update_price_cache()

    CORS(
        app,
        origins=[
            "https://xyk.cmbchina.com",
            "https://grandet.vercel.app",
            "http://localhost:5173",
        ],
        max_age=1728000,
    )

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    app.register_blueprint(portfolio_bp)
    app.register_blueprint(importer_bp)
    app.register_blueprint(balance_bp)
    return app
