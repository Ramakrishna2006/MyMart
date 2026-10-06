from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from ..extensions import db


class User(UserMixin, db.Model):
    """Set 3 - a customer or an admin account."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(15))
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="customer")  # customer | admin
    city = db.Column(db.String(80))
    state = db.Column(db.String(80))
    created_at = db.Column(db.DateTime, default=datetime.now)

    orders = db.relationship("Order", back_populates="user", lazy="dynamic")

    # ---- password helpers -------------------------------------------------
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password or "")

    @property
    def is_admin(self):
        return self.role == "admin"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "role": self.role,
            "is_admin": self.is_admin,
            "city": self.city,
            "state": self.state,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
