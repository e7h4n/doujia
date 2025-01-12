import json

from flask.testing import FlaskClient
import pytest


def test_ccb_importer_empty_hello(client: FlaskClient):
    response = client.post("/ccb_wechat", json={})
    assert response.status_code == 400


@pytest.mark.skip
def test_ccb_importer_return_transaction_count(client, doc_fs_ledger_filename: str):
    """
    @@@/main.bean
    1970-01-01 open Assets:Short:Current:CCB
    @@@/config/main.bconv
    """

    response = client.post(
        "/ccb_wechat",
        json={
            "BODY": {
                "NBPAGE_FULLOCSTR": "101004UNK1731477195981141",
                "Crd_Innr_Acc_CgyCd": "0101",
                "DbCrd_CardNo434": "6217***0109",
                "NBPAGE_LOCSTR": "101004UNK1731477195981141+2+1+2+",
                "NBPAGE_FULLIST": "0",
                "CR_TOT_AMT": "15561.54",
                "Prim_Acc_Acg_Dtl": [
                    {
                        "dataList": [
                            {
                                "Dep_Txn_CgyCd": "02",
                                "Cntrprt_Txn_AccNo434": "6231***0808",
                                "Cntrprt_Txn_AccNo_Nm": "张宇辰",
                                "Txn_Rmrk": "电子汇入",
                                "Txn_Lcl_Tm": "072821",
                                "Txn_Lcl_Dt": "20241106",
                                "Smy_Cntnt": "电子汇入",
                                "Txn_CardNo434": "6217***0109",
                                "Smy_Cd": "0312",
                                "Txn_Dt": "20241106",
                                "Dep_AcBa": "15575.66",
                                "Dep_TxnAmt": "15561.54",
                                "CcyCdCN": "人民币",
                            }
                        ],
                        "Txn_Lcl_Dt": "20241106",
                    },
                    {
                        "dataList": [
                            {
                                "Dep_Txn_CgyCd": "02",
                                "Cntrprt_Txn_AccNo434": "1100***2666",
                                "Cntrprt_Txn_AccNo_Nm": "张宇辰",
                                "Txn_Rmrk": "收回贷款11001064360000000000692666本息",
                                "Txn_Lcl_Tm": "011103",
                                "Txn_Lcl_Dt": "20241026",
                                "Smy_Cntnt": "收回贷款本息",
                                "Txn_CardNo434": "6217***0109",
                                "Smy_Cd": "0088",
                                "Txn_Dt": "20241026",
                                "Dep_AcBa": "14.12",
                                "Dep_TxnAmt": "-15561.54",
                                "CcyCdCN": "人民币",
                            }
                        ],
                        "Txn_Lcl_Dt": "20241026",
                    },
                ],
                "NBPAGE_TOTAL": "1",
                "DR_TOT_AMT": "15561.54",
            },
            "HEADER": {"retcode": "000000000000", "retmsg": ""},
        },
    )
    assert response.status_code == 200
    assert response.is_json

    response_data = json.loads(response.get_data(as_text=True))
    assert response_data["transactions"] == 2
