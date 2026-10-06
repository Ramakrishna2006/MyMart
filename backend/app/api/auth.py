"""Authentication API: register, login, logout, current user."""

import re

from flask import Blueprint
from flask_login import current_user, login_required, login_user, logout_user

from ..extensions import db
from ..models import User
from ..utils import ApiError, body, ok

bp = Blueprint("auth", __name__, url_prefix="/api/auth")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^[6-9]\d{9}$")


@bp.post("/register")
def register():
    data = body()
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    phone = (data.get("phone") or "").strip()
    password = data.get("password") or ""
    city = (data.get("city") or "").strip() or None

    if len(name) < 2:
        raise ApiError("Please enter your full name.")
    if not EMAIL_RE.match(email):
        raise ApiError("Please enter a valid email address.")
    if phone and not PHONE_RE.match(phone):
        raise ApiError("Phone must be a 10-digit Indian mobile number.")
    if len(password) < 6:
        raise ApiError("Password must be at least 6 characters.")
    if User.query.filter_by(email=email).first():
        raise ApiError("This email is already registered.", 409)

    user = User(name=name, email=email, phone=phone or None, city=city, role="customer")
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    login_user(user)
    return ok({"user": user.to_dict(), "message": "Account created!"}, 201)


@bp.post("/login")
def login():
    data = body()
    email = (data.get("email") or "").strip().lower()
    user = User.query.filter_by(email=email).first()
    if user is None or not user.check_password(data.get("password")):
        raise ApiError("Invalid email or password.", 401)
    login_user(user, remember=bool(data.get("remember")))
    return ok({"user": user.to_dict(), "message": f"Welcome back, {user.name.split()[0]}!"})


@bp.post("/logout")
@login_required
def logout():
    logout_user()
    return ok({"message": "Logged out."})


@bp.get("/me")
def me():
    if not current_user.is_authenticated:
        return ok({"user": None})
    return ok({"user": current_user.to_dict()})
