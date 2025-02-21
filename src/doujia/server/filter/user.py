from flask import request

from doujia.server.app import current_app


def get_current_user():
    auth_header = request.headers.get("Authorization")
    if auth_header is None:
        return None

    if (len(auth_header.split(" ")) != 2) or (auth_header.split(" ")[0] != "Bearer"):
        return None

    session_token = auth_header.split(" ")[1]
    user = current_app.sessions.get_current_user(session_token)
    if not user.authenticated:
        return None

    return user
