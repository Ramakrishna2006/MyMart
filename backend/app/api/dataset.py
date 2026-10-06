"""
Dataset Explorer API - lets anyone browse the five data sets that power MyMart.

GET /api/dataset                    -> list of sets with explanation + live stats
GET /api/dataset/<key>              -> one page of rows (supports ?q= & ?page= & ?per_page=)
GET /api/dataset/<key>/download     -> CSV export of the live table
GET /api/dataset/<key>/original     -> the original CSV file from data/
"""

import csv
import io

from flask import Blueprint, Response, request, send_file

from ..config import DATA_DIR
from ..extensions import db
from ..models import Category, Order, OrderItem, Product, User
from ..utils import ApiError, ok, paginate

bp = Blueprint("dataset", __name__, url_prefix="/api/dataset")
func = db.func


def _mask_email(email):
    if not email or "@" not in email:
        return email
    user, domain = email.split("@", 1)
    return f"{user[:2]}***@{domain}"


# Every set: what it is, why it exists, how the app uses it, and every column.
DATASETS = {
    "categories": {
        "number": 1,
        "title": "Categories",
        "emoji": "🗂️",
        "file": "categories.csv",
        "model": Category,
        "summary": "The 12 aisles of the store. Every product belongs to exactly one category.",
        "purpose": "Groups products so customers can browse by aisle (Fruits, Dairy, ...) and so the "
                   "admin can see which aisle earns the most money.",
        "used_in": ["Shop page category chips", "Admin > Sales by category chart", "Product form dropdown"],
        "relations": ["categories.id  1 ──< many  products.category_id"],
        "columns": [
            ("id", "integer", "Primary key - unique number of the category", "3"),
            ("name", "text", "Display name shown in the shop", "Dairy & Eggs"),
            ("slug", "text", "URL-friendly name used in links / filters", "dairy-eggs"),
            ("emoji", "text", "Icon used as the product picture placeholder", "🥛"),
            ("description", "text", "One-line description of the aisle", "Milk, curd, paneer..."),
        ],
        "questions": ["How many products are in each category?", "Which category sells the most?"],
    },
    "products": {
        "number": 2,
        "title": "Products",
        "emoji": "📦",
        "file": "products.csv",
        "model": Product,
        "summary": "The product catalogue: 111 Indian grocery items with price, MRP, discount, stock and rating.",
        "purpose": "This is what customers search, filter and add to their cart. Stock is reduced on every "
                   "order and restored when an order is cancelled. A few items are deliberately low / out of "
                   "stock so the admin's low-stock alert has something to show.",
        "used_in": ["Shop page grid, search, filters and sorting", "Cart & checkout", "Admin > Products table",
                    "Admin > Low-stock alert"],
        "relations": ["products.category_id >── categories.id", "products.id 1 ──< many order_items.product_id"],
        "columns": [
            ("id", "integer", "Primary key", "24"),
            ("sku", "text", "Stock Keeping Unit - unique product code (MM-<category>-<id>)", "MM-03-0024"),
            ("name", "text", "Product name", "Malai Paneer"),
            ("brand", "text", "Brand name (fictional brands)", "DairyDay"),
            ("category_id", "integer", "Foreign key → categories.id", "3"),
            ("unit", "text", "Pack size", "200 g"),
            ("mrp", "decimal ₹", "Maximum Retail Price printed on the pack", "90.00"),
            ("price", "decimal ₹", "Selling price on MyMart (≤ MRP)", "85.50"),
            ("discount_pct", "integer %", "(mrp − price) / mrp × 100 - calculated", "5"),
            ("stock", "integer", "Units currently available in the store", "64"),
            ("rating", "decimal 1-5", "Average customer rating", "4.3"),
            ("rating_count", "integer", "Number of ratings - used for 'Popular' sorting", "812"),
            ("is_veg", "boolean", "1 = vegetarian (green dot), 0 = non-veg (red dot)", "1"),
            ("description", "text", "Short marketing description", "Malai Paneer from DairyDay..."),
            ("created_at", "datetime", "When the product was added to the catalogue", "2026-02-11 10:22:05"),
        ],
        "questions": ["Which items are low on stock?", "What is the average discount?",
                      "Which products have the best rating?"],
    },
    "customers": {
        "number": 3,
        "title": "Customers",
        "emoji": "👥",
        "file": "customers.csv",
        "model": User,
        "summary": "60 synthetic customer accounts spread across 10 Indian cities (plus anyone who registers).",
        "purpose": "Customers own carts and orders. Their city lets the admin see where sales come from. "
                   "All demo customers can log in with password Customer@123.",
        "used_in": ["Login / register", "Admin > Customers table", "Admin > Top cities & top customers"],
        "relations": ["users.id 1 ──< many orders.user_id"],
        "privacy": "All people in this set are invented (emails use example.com). Even so, the live explorer "
                   "masks emails and never shows phone numbers or password hashes - a good habit for real data. "
                   "Passwords are stored as salted hashes, never as plain text.",
        "columns": [
            ("id", "integer", "Primary key", "11"),
            ("name", "text", "Full name (synthetic)", "Rohan Iyer"),
            ("email", "text", "Login email - masked in the explorer", "ro***@example.com"),
            ("city", "text", "Home city", "Bengaluru"),
            ("state", "text", "State", "Karnataka"),
            ("joined_at", "datetime", "Registration date", "2026-03-04 18:20:11"),
        ],
        "questions": ["Which city has the most customers?", "Who are the top spenders?"],
    },
    "orders": {
        "number": 4,
        "title": "Orders",
        "emoji": "🧾",
        "file": "orders.csv",
        "model": Order,
        "summary": "420 orders placed between April and September 2026 - one row per checkout.",
        "purpose": "The order 'header' / receipt: who ordered, when, how they paid, the status of delivery and "
                   "the money totals. It drives every revenue number on the admin dashboard.",
        "used_in": ["My Orders page", "Admin > Orders (status updates)", "Admin > Revenue, monthly sales, "
                    "payment split, top cities"],
        "relations": ["orders.user_id >── users.id", "orders.id 1 ──< many order_items.order_id"],
        "rules": [
            "subtotal = sum of its order_items.line_total",
            "delivery_fee = ₹0 when subtotal ≥ ₹499, otherwise ₹40",
            "total = subtotal + delivery_fee",
            "status flow: Placed → Packed → Shipped → Delivered (or Cancelled before delivery)",
            "Cancelled orders are excluded from revenue; UPI payments become Refunded",
        ],
        "columns": [
            ("id", "integer", "Primary key", "57"),
            ("order_number", "text", "Human-readable order number MM<yymm>-<id>", "MM2605-00057"),
            ("user_id", "integer", "Foreign key → users.id (the customer)", "29"),
            ("created_at", "datetime", "When the order was placed", "2026-05-14 19:41:07"),
            ("status", "text", "Placed / Packed / Shipped / Delivered / Cancelled", "Delivered"),
            ("payment_method", "text", "UPI or COD (cash on delivery)", "UPI"),
            ("payment_status", "text", "Paid / Pending / Refunded / Cancelled", "Paid"),
            ("items_count", "integer", "Total units in the order", "6"),
            ("subtotal", "decimal ₹", "Sum of line totals", "512.40"),
            ("delivery_fee", "decimal ₹", "0 or 40", "0.00"),
            ("total", "decimal ₹", "Amount the customer pays", "512.40"),
            ("delivery_city", "text", "City the order was delivered to", "Chennai"),
        ],
        "questions": ["What is the monthly revenue trend?", "UPI vs Cash on Delivery - which is more popular?",
                      "What percentage of orders are cancelled?"],
    },
    "order_items": {
        "number": 5,
        "title": "Order Items",
        "emoji": "🛒",
        "file": "order_items.csv",
        "model": OrderItem,
        "summary": "1,385 order lines - one row for each product inside an order.",
        "purpose": "Links orders to products (a many-to-many relationship). The product name and price are "
                   "copied at the moment of purchase so old receipts never change when a price changes.",
        "used_in": ["Order details on My Orders", "Admin > Top products", "Admin > Sales by category"],
        "relations": ["order_items.order_id >── orders.id", "order_items.product_id >── products.id"],
        "rules": ["line_total = unit_price × quantity"],
        "columns": [
            ("id", "integer", "Primary key", "201"),
            ("order_id", "integer", "Foreign key → orders.id", "57"),
            ("product_id", "integer", "Foreign key → products.id", "24"),
            ("product_name", "text", "Product name at the time of purchase (snapshot)", "Malai Paneer"),
            ("unit_price", "decimal ₹", "Price per unit at the time of purchase (snapshot)", "85.50"),
            ("quantity", "integer", "Units bought", "2"),
            ("line_total", "decimal ₹", "unit_price × quantity", "171.00"),
        ],
        "questions": ["What are the 10 best-selling products?", "How many items does an average order contain?"],
    },
}


# ---------------------------------------------------------------------------
# Row builders (live DB -> dict with exactly the documented columns)
# ---------------------------------------------------------------------------
def _fmt(v):
    if hasattr(v, "strftime"):
        return v.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(v, bool):
        return int(v)
    return v


def _row(key, obj):
    columns = DATASETS[key]["columns"]
    cols = [c[0] for c in columns]
    money = {c[0] for c in columns if "₹" in c[1]}
    if key == "customers":
        values = {"id": obj.id, "name": obj.name, "email": _mask_email(obj.email), "city": obj.city,
                  "state": obj.state, "joined_at": obj.created_at}
    else:
        values = {c: getattr(obj, c, None) for c in cols}
    out = {c: _fmt(values.get(c)) for c in cols}
    for c in money:
        if out[c] is not None:
            out[c] = f"{float(out[c]):.2f}"
    return out


def _query(key):
    meta = DATASETS[key]
    model = meta["model"]
    query = model.query
    if key == "customers":
        query = query.filter(User.role == "customer")

    q = (request.args.get("q") or "").strip()
    if q:
        text_cols = {"categories": [Category.name, Category.description],
                     "products": [Product.name, Product.brand, Product.sku, Product.unit],
                     "customers": [User.name, User.city, User.state],
                     "orders": [Order.order_number, Order.status, Order.payment_method, Order.delivery_city],
                     "order_items": [OrderItem.product_name]}[key]
        conds = [c.ilike(f"%{q}%") for c in text_cols]
        if q.isdigit():
            conds.append(model.id == int(q))
            if key == "order_items":
                conds.append(OrderItem.order_id == int(q))
        query = query.filter(db.or_(*conds))
    return query.order_by(model.id)


# ---------------------------------------------------------------------------
# Live statistics per set
# ---------------------------------------------------------------------------
def _stats(key):
    r2 = lambda v: round(float(v or 0), 2)  # noqa: E731
    if key == "categories":
        rows = (db.session.query(Category.name, Category.emoji, func.count(Product.id))
                .outerjoin(Product, db.and_(Product.category_id == Category.id, Product.is_active.is_(True)))
                .group_by(Category.id).order_by(Category.id).all())
        return {"cards": [("Categories", len(rows)), ("Largest aisle", max(rows, key=lambda r: r[2])[0] if rows else "-")],
                "chart": {"title": "Products per category", "data": [{"label": f"{e} {n}", "value": c} for n, e, c in rows]}}
    if key == "products":
        active = Product.query.filter(Product.is_active.is_(True))
        n = active.count()
        avg_price, min_p, max_p, avg_rating = db.session.query(
            func.avg(Product.price), func.min(Product.price), func.max(Product.price), func.avg(Product.rating)
        ).filter(Product.is_active.is_(True)).one()
        veg = active.filter(Product.is_veg.is_(True)).count()
        oos = active.filter(Product.stock == 0).count()
        buckets = [("< ₹50", 0, 50), ("₹50-99", 50, 100), ("₹100-199", 100, 200), ("₹200-299", 200, 300), ("₹300+", 300, 10**9)]
        chart = [{"label": label, "value": active.filter(Product.price >= lo, Product.price < hi).count()}
                 for label, lo, hi in buckets]
        return {"cards": [("Products", n), ("Average price", f"₹{r2(avg_price)}"),
                          ("Price range", f"₹{r2(min_p):g} - ₹{r2(max_p):g}"), ("Average rating", f"{r2(avg_rating)} ★"),
                          ("Vegetarian", f"{round(veg * 100 / n) if n else 0}%"), ("Out of stock", oos)],
                "chart": {"title": "Products by price range", "data": chart}}
    if key == "customers":
        base = User.query.filter(User.role == "customer")
        rows = (db.session.query(User.city, func.count(User.id)).filter(User.role == "customer")
                .group_by(User.city).order_by(func.count(User.id).desc()).all())
        return {"cards": [("Customers", base.count()), ("Cities", len([r for r in rows if r[0]])),
                          ("Top city", rows[0][0] if rows else "-")],
                "chart": {"title": "Customers per city", "data": [{"label": c or "Unknown", "value": n} for c, n in rows]}}
    if key == "orders":
        total = Order.query.count()
        valid = Order.query.filter(Order.status != "Cancelled")
        revenue = db.session.query(func.sum(Order.total)).filter(Order.status != "Cancelled").scalar()
        first, last = db.session.query(func.min(Order.created_at), func.max(Order.created_at)).one()
        cancelled = Order.query.filter(Order.status == "Cancelled").count()
        month = func.strftime("%Y-%m", Order.created_at)
        rows = (db.session.query(month.label("m"), func.sum(Order.total)).filter(Order.status != "Cancelled")
                .group_by("m").order_by("m").all())
        return {"cards": [("Orders", total), ("Revenue", f"₹{r2(revenue):,.0f}"),
                          ("Avg order value", f"₹{r2(revenue) / valid.count():,.0f}" if valid.count() else "-"),
                          ("Cancelled", f"{round(cancelled * 100 / total, 1) if total else 0}%"),
                          ("From", first.strftime("%d %b %Y") if first else "-"),
                          ("To", last.strftime("%d %b %Y") if last else "-")],
                "chart": {"title": "Revenue per month (₹)", "data": [{"label": m, "value": r2(v)} for m, v in rows]}}
    if key == "order_items":
        rows = OrderItem.query.count()
        units = db.session.query(func.sum(OrderItem.quantity)).scalar() or 0
        orders = db.session.query(func.count(func.distinct(OrderItem.order_id))).scalar() or 0
        distinct = db.session.query(func.count(func.distinct(OrderItem.product_id))).scalar() or 0
        qty = (db.session.query(OrderItem.quantity, func.count(OrderItem.id))
               .group_by(OrderItem.quantity).order_by(OrderItem.quantity).all())
        return {"cards": [("Order lines", rows), ("Units sold", int(units)),
                          ("Lines per order", round(rows / orders, 2) if orders else 0),
                          ("Different products sold", distinct)],
                "chart": {"title": "How many units per line", "data": [{"label": f"qty {q}", "value": c} for q, c in qty]}}
    return {}


def _meta(key, with_stats=True):
    m = DATASETS[key]
    data = {k: v for k, v in m.items() if k not in ("model", "columns")}
    data["key"] = key
    data["columns"] = [{"name": n, "type": t, "description": d, "example": e} for n, t, d, e in m["columns"]]
    data["rows"] = _query(key).count() if not request.args.get("q") else None
    if with_stats:
        st = _stats(key)
        data["stats"] = {"cards": [{"label": a, "value": b} for a, b in st.get("cards", [])], "chart": st.get("chart")}
    return data


def _get(key):
    if key not in DATASETS:
        raise ApiError("Unknown dataset.", 404)
    return DATASETS[key]


@bp.get("")
def list_sets():
    return ok({"datasets": [_meta(k) for k in DATASETS]})


@bp.get("/<key>")
def rows(key):
    _get(key)
    page = paginate(_query(key), lambda o: _row(key, o), default_per_page=25)
    page["columns"] = [c[0] for c in DATASETS[key]["columns"]]
    return ok(page)


@bp.get("/<key>/download")
def download(key):
    meta = _get(key)
    cols = [c[0] for c in meta["columns"]]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=cols)
    writer.writeheader()
    for obj in _query(key).all():
        writer.writerow(_row(key, obj))
    return Response(
        "﻿" + buf.getvalue(),  # BOM so Excel shows ₹ and emoji correctly
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=mymart_{key}_live.csv"},
    )


@bp.get("/<key>/original")
def original(key):
    meta = _get(key)
    return send_file(DATA_DIR / meta["file"], mimetype="text/csv", as_attachment=True, download_name=meta["file"])
