def test_portfolio_cors(client, mocker):
    mock_user = mocker.Mock()
    mock_user.user_id = "usr-6722965184682784673"
    mock_user.authenticated = True
    mocker.patch("doujia.server.filter.user.get_current_user", return_value=mock_user)

    response = client.get(
        "/portfolio/irr_summary",
        headers={
            "Origin": "https://xyk.cmbchina.com",
            "Authorization": "Bearer 1234567890",
        },
    )
    assert response.headers["Access-Control-Allow-Origin"] == "https://xyk.cmbchina.com"

    response = client.get(
        "/portfolio/irr_summary",
        headers={
            "Origin": "https://grandet.vercel.app",
            "Authorization": "Bearer 1234567890",
        },
    )
    assert response.headers["Access-Control-Allow-Origin"] == "https://grandet.vercel.app"

    response = client.get(
        "/portfolio/irr_summary",
        headers={
            "Origin": "http://localhost:5173",
            "Authorization": "Bearer 1234567890",
        },
    )
    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:5173"


def test_portfolio_cors_invalid_origin(client, mocker):
    mock_user = mocker.Mock()
    mock_user.user_id = "usr-6722965184682784673"
    mock_user.authenticated = True
    mocker.patch("doujia.server.filter.user.get_current_user", return_value=mock_user)

    response = client.get(
        "/portfolio/irr_summary",
        headers={
            "Origin": "https://localhost:3000",
            "Authorization": "Bearer 1234567890",
        },
    )
    assert "Access-Control-Allow-Origin" not in response.headers
