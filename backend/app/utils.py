"""Small helpers shared by the API blueprints."""

from functools import wraps

from flask import jsonify, request
from flask_login import current_user


class ApiError(Exception):
    """Raise anywhere in a view to return {"error": message} with a status code."""

    def __init__(self, message, status=400):
        super().__init__(message)
        self.message = message
        self.status = status


def admin_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            raise ApiError("Please log in first.", 401)
        if not current_user.is_admin:
            raise ApiError("Admin access only.", 403)
        return view(*args, **kwargs)

    return wrapper


def body():
    """Return the JSON body of the request (or an empty dict)."""
    return request.get_json(silent=True) or {}


def int_arg(name, default, minimum=None, maximum=None):
    try:
        value = int(request.args.get(name, default))
    except (TypeError, ValueError):
        value = default
    if minimum is not None:
        value = max(minimum, value)
    if maximum is not None:
        value = min(maximum, value)
    return value


def paginate(query, serializer, default_per_page=20, max_per_page=100):
    page = int_arg("page", 1, minimum=1)
    per_page = int_arg("per_page", default_per_page, minimum=1, maximum=max_per_page)
    result = query.paginate(page=page, per_page=per_page, error_out=False)
    return {
        "items": [serializer(x) for x in result.items],
        "page": result.page,
        "per_page": per_page,
        "pages": result.pages,
        "total": result.total,
    }


def ok(data=None, status=200, **extra):
    payload = data if data is not None else {}
    if extra:
        payload = {**payload, **extra}
    return jsonify(payload), status
