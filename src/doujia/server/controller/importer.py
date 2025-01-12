from flask import Blueprint, request

from doujia.server.logic.ccb import import_ccb_transactions
from doujia.server.logic.cmb_encrypted import (
    import_cmb_transactions as import_cmb_encrypted_transactions,
)


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
