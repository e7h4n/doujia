import os

from corbado_python_sdk import Config, CorbadoSDK, SessionService
from flask import Flask
from flask_cors import CORS
from logzero import INFO, logger, setup_default_logger

from doujia.server.controller.balance import bp as balance_bp
from doujia.server.controller.importer import bp as importer_bp
from doujia.server.controller.portfolio import bp as portfolio_bp
from doujia.server.task.ledger import reload_ledger
from doujia.server.task.price import update_price_cache

DEFAULT_CORBADO_PROJECT_ID = "pro-8910668211600497001"


def setup_corbado(app: Flask):
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


def setup_app_config(app: Flask, test_config=None):
    logger.debug("Setting up app config")
    app.config.from_mapping(SECRET_KEY="dev")

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_object("doujia.server.config")
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


def setup_logger(app: Flask):
    logger.debug("Setting up logger")
    if not app.config.get("TESTING") and not app.config.get("DEBUG"):
        setup_default_logger(level=INFO)


def setup_cors(app):
    logger.debug("Setting up CORS")
    CORS(
        app,
        origins=[
            "https://xyk.cmbchina.com",
            "https://grandet.vercel.app",
            "http://localhost:5173",
        ],
        max_age=1728000,
    )


def setup_controller(app):
    logger.debug("Setting up controller")
    app.register_blueprint(portfolio_bp)
    app.register_blueprint(importer_bp)
    app.register_blueprint(balance_bp)


def setup_hsbc(app):
    app.hsbc_session = None


def init_data(app):
    logger.debug("Initializing data")
    reload_ledger(app)
    update_price_cache(app)
