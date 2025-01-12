from corbado_python_sdk import CorbadoSDK, SessionService
from flask import Flask, current_app as _current_app
from beancount.core import data
from typing import Dict, TypeVar

Directive = TypeVar("Directive", bound=data.Directive)  # type: ignore


class FlaskApp(Flask):
    app_root: str
    corbado: CorbadoSDK
    sessions: SessionService
    entries: list[Directive]
    options_map: Dict


current_app: FlaskApp = _current_app
