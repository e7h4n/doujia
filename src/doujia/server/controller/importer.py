import json
import os

from flask import Blueprint, request
from logzero import logger

from doujia.hsbc.hsbc_importer import HSBCSession, import_full_transactions
from doujia.server.app import current_app
from doujia.server.logic.ccb import import_ccb_transactions
from doujia.server.logic.cmb_encrypted import (
    import_cmb_transactions as import_cmb_encrypted_transactions,
)
from doujia.server.logic.hsbc_cn_asset import import_hsbc_cn_asset
from doujia.server.logic.hsbc_current import import_hsbc_current
from doujia.server.logic.hsbc_hk_credit_card import import_hsbc_hk_credit_card, import_hsbc_hk_credit_card_balance

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


@bp.post("/hsbc_session")
def hsbc_session():
    authorization = request.headers.get("authorization")
    authorizationguest = request.headers.get("authorizationguest")
    logger.info(f"HSBC session request with authorization: {authorization}, authorizationguest: {authorizationguest}")

    session = HSBCSession(authorizationguest, authorization)
    current_app.hsbc_session = session

    imported_count = import_full_transactions(
        os.path.join(current_app.ledger_root, "main.bean"),
        session,
        current_app.doujia_config.categorize_config,
        current_app.doujia_config.import_to,
    )

    return {"transactions": imported_count}


@bp.post("/hsbc_current")
def hsbc_current():
    imported_count = import_hsbc_current(request.get_json())
    return {"transactions": imported_count}


@bp.post("/uni_forward")
def uni_forward():
    body = request.get_json()

    url = body["request"]["url"]
    if url == "https://www.services.online-banking.hsbc.com.cn/gpib/channel/proxy/accountDataSvc/rtrvTxnSumm":
        json_body = body["response"]["body"]
        return {"transactions": import_hsbc_cn_asset(json.loads(json_body))}
    elif url.startswith("https://www.hsbc.com.hk/api/mmf-account-transactions--hk-hbap-prod-proxy/v2/transactions"):
        json_body = body["response"]["body"]
        return {"transactions": import_hsbc_hk_credit_card(json.loads(json_body))}
    elif url.startswith(
        "https://www.hsbc.com.hk/api/mmf-cust-accounts-details--hk-hbap-banking-prod-proxy/v1/accounts/credit-cards/CRDTR-"
    ):
        json_body = body["response"]["body"]
        return {"transactions": import_hsbc_hk_credit_card_balance(json.loads(json_body))}

    return {"transactions": 0}
