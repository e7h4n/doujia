from typing import TypeVar

from beancount.core import data
from corbado_python_sdk import CorbadoSDK, SessionService
from flask import Flask
from flask import current_app as _current_app

from doujia.hsbc.hsbc_importer import HSBCSession

Directive = TypeVar("Directive", bound=data.Directive)  # type: ignore


class FlaskApp(Flask):
    app_root: str
    ledger_root: str
    corbado: CorbadoSDK
    sessions: SessionService
    entries: list[Directive]
    options_map: dict
    hsbc_session: HSBCSession


current_app: FlaskApp = _current_app
