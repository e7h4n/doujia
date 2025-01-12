from functools import wraps

from flask import abort, request
from doujia.server.filter.user import get_current_user
from doujia.server.app import current_app


def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_app.config.get("TESTING") or (
            current_app.sessions is None
            and request.args.get("__debug__user__") is not None
            and request.headers.get("X-Debug-User") is not None
        ):
            return f(*args, **kwargs)

        current_user = get_current_user()

        if current_user is None:
            abort(401, description="Unauthorized")

        if (
            current_user.user_id != "usr-6722965184682784673"
            and current_user.user_id != "usr-8326674140331757550"
        ):
            abort(403, description="Forbidden")

        return f(*args, **kwargs)

    return decorated_function
