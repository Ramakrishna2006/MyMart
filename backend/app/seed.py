"""
Load the sample dataset (data/*.csv) into the database.

Called automatically on first start (AUTO_SEED=true) and from `manage.py`.
"""

import csv
from datetime import datetime

from flask import current_app
from werkzeug.security import generate_password_hash

from .config import DATA_DIR
from .extensions import db
from .models import CartItem, Category, Order, OrderItem, Product, User


def _read(name):
    with (DATA_DIR / name).open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _dt(value):
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")


def ensure_admin():
    """Create the admin account from ADMIN_EMAIL / ADMIN_PASSWORD if missing."""
    cfg = current_app.config
    admin = User.query.filter_by(email=cfg["ADMIN_EMAIL"]).first()
    if admin is None:
        admin = User(name="Admin", email=cfg["ADMIN_EMAIL"], phone="9999999999", role="admin")
        admin.set_password(cfg["ADMIN_PASSWORD"])
        db.session.add(admin)
        db.session.commit()
    return admin


def seed_database(verbose=True):
    """Insert every CSV row. Assumes empty tables (call reset first if needed)."""
    log = print if verbose else (lambda *a, **k: None)
    cfg = current_app.config

    # Set 1 - categories
    for r in _read("categories.csv"):
        db.session.add(Category(id=int(r["id"]), name=r["name"], slug=r["slug"],
                                emoji=r["emoji"], description=r["description"]))

    # Set 2 - products
    for r in _read("products.csv"):
        db.session.add(Product(
            id=int(r["id"]), sku=r["sku"], name=r["name"], brand=r["brand"],
            category_id=int(r["category_id"]), unit=r["unit"], mrp=float(r["mrp"]),
            price=float(r["price"]), stock=int(r["stock"]), rating=float(r["rating"]),
            rating_count=int(r["rating_count"]), is_veg=r["is_veg"] == "1",
            description=r["description"], created_at=_dt(r["created_at"]),
        ))

    # Set 3 - customers (all demo customers share one password; hashing once is faster)
    shared_hash = generate_password_hash(cfg["DEMO_CUSTOMER_PASSWORD"])
    for r in _read("customers.csv"):
        db.session.add(User(
            id=int(r["id"]), name=r["name"], email=r["email"], phone=r["phone"],
            password_hash=shared_hash, role="customer", city=r["city"], state=r["state"],
            created_at=_dt(r["joined_at"]),
        ))
    db.session.flush()

    # Set 4 - orders
    customers = {u.id: u for u in User.query.all()}
    for r in _read("orders.csv"):
        cust = customers[int(r["user_id"])]
        db.session.add(Order(
            id=int(r["id"]), order_number=r["order_number"], user_id=cust.id,
            created_at=_dt(r["created_at"]), status=r["status"],
            payment_method=r["payment_method"], payment_status=r["payment_status"],
            items_count=int(r["items_count"]), subtotal=float(r["subtotal"]),
            delivery_fee=float(r["delivery_fee"]), total=float(r["total"]),
            delivery_name=cust.name, delivery_phone=cust.phone,
            delivery_address="Demo address", delivery_city=r["delivery_city"],
        ))

    # Set 5 - order items
    for r in _read("order_items.csv"):
        db.session.add(OrderItem(
            id=int(r["id"]), order_id=int(r["order_id"]), product_id=int(r["product_id"]),
            product_name=r["product_name"], unit_price=float(r["unit_price"]),
            quantity=int(r["quantity"]), line_total=float(r["line_total"]),
        ))

    db.session.commit()
    ensure_admin()  # admin gets the next free id after the customers

    log(f"Seeded: {Category.query.count()} categories, {Product.query.count()} products, "
        f"{User.query.count()} users, {Order.query.count()} orders, {OrderItem.query.count()} order items")


def is_empty():
    return db.session.query(Category.id).first() is None


def reset_database(verbose=True):
    """Drop every table, recreate them and load the dataset again."""
    db.drop_all()
    db.create_all()
    seed_database(verbose=verbose)


__all__ = ["seed_database", "reset_database", "ensure_admin", "is_empty", "CartItem"]
