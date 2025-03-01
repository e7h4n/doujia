from doujia.hsbc.cipher import (
    decrypt_response,
    encrypt_request,
    generate_key,
)


def test_cipher():
    key = generate_key()

    request = encrypt_request(
        {
            "billOption": "A",
        },
        key,
    )

    assert decrypt_response(request["data"], key) == {
        "billOption": "A",
    }
