import os

from flask import Flask

from doujia.server.bootstrap.scheduler import setup_scheduler
from doujia.server.bootstrap.setup_app import (
    init_data,
    setup_app_config,
    setup_controller,
    setup_corbado,
    setup_cors,
    setup_logger,
)


def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    os.makedirs(app.instance_path, exist_ok=True)

    setup_app_config(app, test_config)
    setup_logger(app)
    setup_corbado(app)
    setup_scheduler(app)
    setup_cors(app)
    setup_controller(app)

    init_data(app)

    return app
