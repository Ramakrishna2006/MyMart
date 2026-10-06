"""
Application configuration.

Values are read from environment variables (or a `.env` file in the project
root, see `.env.example`). Every setting has a safe default so the project runs
out of the box on localhost.
"""

import os
from pathlib import Path

try:  # python-dotenv is optional
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

# Project root = the folder that contains run.py
ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT_DIR / "backend"
FRONTEND_DIR = ROOT_DIR / "frontend"
DATA_DIR = ROOT_DIR / "data"
INSTANCE_DIR = BACKEND_DIR / "instance"

if load_dotenv:
    load_dotenv(ROOT_DIR / ".env")


def _bool(name, default=False):
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


class Config:
    # Flask
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me-in-production")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    # Database - SQLite file inside backend/instance/ (path works on every OS)
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", "sqlite:///" + (INSTANCE_DIR / "mymart.db").as_posix()
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Shop rules
    FREE_DELIVERY_ABOVE = float(os.getenv("FREE_DELIVERY_ABOVE", 499))
    DELIVERY_FEE = float(os.getenv("DELIVERY_FEE", 40))
    LOW_STOCK_THRESHOLD = int(os.getenv("LOW_STOCK_THRESHOLD", 10))
    MAX_QTY_PER_ITEM = int(os.getenv("MAX_QTY_PER_ITEM", 10))

    # UPI (demo payment) - put your own UPI ID in .env
    MERCHANT_UPI_ID = os.getenv("MERCHANT_UPI_ID", "mymart@upi")
    MERCHANT_NAME = os.getenv("MERCHANT_NAME", "My Mart")

    # Default admin created by the seeder
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@mymart.com")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Admin@123")

    # Load the sample dataset automatically when the database is empty
    AUTO_SEED = _bool("AUTO_SEED", True)
    DEMO_CUSTOMER_PASSWORD = os.getenv("DEMO_CUSTOMER_PASSWORD", "Customer@123")


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SECRET_KEY = "test"
