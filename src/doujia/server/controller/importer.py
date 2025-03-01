from flask import Blueprint, request

from doujia.hsbc.hsbc_importer import HSBCSession
from doujia.server.app import current_app
from doujia.server.logic.ccb import import_ccb_transactions
from doujia.server.logic.cmb_encrypted import (
    import_cmb_transactions as import_cmb_encrypted_transactions,
)
from doujia.server.logic.hsbc import import_hsbc_transactions

bp = Blueprint("importer", __name__)


@bp.post("/ccb_wechat")
def ccb_wechat_importer():
    body = request.get_json()

    if "BODY" not in body or "Prim_Acc_Acg_Dtl" not in body["BODY"]:
        return "请求缺少账单信息", 400

    imported_count = import_ccb_transactions(body)

    return {"transactions": imported_count}


@bp.post("/cmb_wechat_encrypted")
def cmb_wechat_encrypted_importer():
    body = request.get_json()

    imported_count = import_cmb_encrypted_transactions(body)

    return {"transactions": imported_count}


@bp.post("/hsbc_wechat")
def hsbc_wechat_importer():
    url = request.data

    imported_count = import_hsbc_transactions(url)

    return {"transactions": imported_count}


@bp.post("/hsbc_session")
def hsbc_session():
    authorization = request.headers.get("authorization")
    authorizationguest = request.headers.get("authorizationguest")

    session = HSBCSession(authorizationguest, authorization)
    current_app.hsbc_session = session

    return {"status": "ok"}
