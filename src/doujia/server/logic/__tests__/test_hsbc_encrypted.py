import pytest

from doujia.server.logic.hsbc_encrypted import query_unbilled_transactions


@pytest.mark.skip(reason="Not implemented")
def test_hsbc_encrypted_request():
    query = query_unbilled_transactions()
    print(query)

    assert query is None
