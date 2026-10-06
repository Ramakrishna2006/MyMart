"""Admin-only API: dashboard stats, analytics, product management, order management."""

import re
import uuid

from flask import Blueprint, current_app, request

from ..extensions import db
from ..models import ORDER_STATUSES, Category, Order, OrderItem, Product, User
from ..utils import ApiError, admin_required, body, ok, paginate
from .orders import restock

bp = Blueprint("admin", __name__, url_prefix="/api/admin")

func = db.func
NOT_CANCELLED = Order.status != "Cancelled"

# Allowed status moves (current -> next)
TRANSITIONS = {
    "Placed": ["Packed", "Cancelled"],
    "Packed": ["Shipped", "Cancelled"],
    "Shipped": ["Delivered", "Cancelled"],
    "Delivered": [],
    "Cancelled": [],
}


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
@bp.get("/stats")
@admin_required
def stats():
    low = current_app.config["LOW_STOCK_THRESHOLD"]
    revenue = db.session.query(func.coalesce(func.sum(Order.total), 0)).filter(NOT_CANCELLED).scalar()
    orders = Order.query.count()
    valid_orders = Order.query.filter(NOT_CANCELLED).count()
    low_stock = (
        Product.query.filter(Product.is_active.is_(True), Product.stock <= low)
        .order_by(Product.stock)
        .all()
    )
    return ok({
        "revenue": round(float(revenue), 2),
        "orders": orders,
        "avg_order_value": round(float(revenue) / valid_orders, 2) if valid_orders else 0,
        "customers": User.query.filter_by(role="customer").count(),
        "products": Product.query.filter_by(is_active=True).count(),
        "pending_orders": Order.query.filter(Order.status.in_(["Placed", "Packed", "Shipped"])).count(),
        "low_stock_threshold": low,
        "low_stock": [p.to_dict() for p in low_stock],
    })


@bp.get("/analytics")
@admin_required
def analytics():
    month = func.strftime("%Y-%m", Order.created_at)
    by_month = (
        db.session.query(month.label("month"), func.count(Order.id), func.sum(Order.total))
        .filter(NOT_CANCELLED)
        .group_by("month")
        .order_by("month")
        .all()
    )

    by_category = (
        db.session.query(Category.name, Category.emoji, func.sum(OrderItem.line_total), func.sum(OrderItem.quantity))
        .join(Product, Product.category_id == Category.id)
        .join(OrderItem, OrderItem.product_id == Product.id)
        .join(Order, Order.id == OrderItem.order_id)
        .filter(NOT_CANCELLED)
        .group_by(Category.id)
        .order_by(func.sum(OrderItem.line_total).desc())
        .all()
    )

    top_products = (
        db.session.query(OrderItem.product_name, func.sum(OrderItem.quantity), func.sum(OrderItem.line_total))
        .join(Order, Order.id == OrderItem.order_id)
        .filter(NOT_CANCELLED)
        .group_by(OrderItem.product_name)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(10)
        .all()
    )

    by_status = db.session.query(Order.status, func.count(Order.id)).group_by(Order.status).all()
    by_payment = (
        db.session.query(Order.payment_method, func.count(Order.id), func.sum(Order.total))
        .filter(NOT_CANCELLED)
        .group_by(Order.payment_method)
        .all()
    )
    by_city = (
        db.session.query(Order.delivery_city, func.count(Order.id), func.sum(Order.total))
        .filter(NOT_CANCELLED)
        .group_by(Order.delivery_city)
        .order_by(func.sum(Order.total).desc())
        .limit(10)
        .all()
    )
    weekday = func.strftime("%w", Order.created_at)
    by_weekday = (
        db.session.query(weekday.label("wd"), func.count(Order.id))
        .filter(NOT_CANCELLED)
        .group_by("wd")
        .order_by("wd")
        .all()
    )
    days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

    top_customers = (
        db.session.query(User.name, User.city, func.count(Order.id), func.sum(Order.total))
        .join(Order, Order.user_id == User.id)
        .filter(NOT_CANCELLED)
        .group_by(User.id)
        .order_by(func.sum(Order.total).desc())
        .limit(5)
        .all()
    )

    r2 = lambda v: round(float(v or 0), 2)  # noqa: E731
    return ok({
        "sales_by_month": [{"month": m, "orders": c, "revenue": r2(t)} for m, c, t in by_month],
        "sales_by_category": [{"category": n, "emoji": e, "revenue": r2(t), "units": int(u)} for n, e, t, u in by_category],
        "top_products": [{"name": n, "units": int(u), "revenue": r2(t)} for n, u, t in top_products],
        "orders_by_status": {s: c for s, c in by_status},
        "payment_methods": [{"method": m, "orders": c, "revenue": r2(t)} for m, c, t in by_payment],
        "top_cities": [{"city": c or "-", "orders": n, "revenue": r2(t)} for c, n, t in by_city],
        "orders_by_weekday": [{"day": days[int(d)], "orders": c} for d, c in by_weekday],
        "top_customers": [{"name": n, "city": c, "orders": o, "spent": r2(t)} for n, c, o, t in top_customers],
    })


# ---------------------------------------------------------------------------
# Products (create / update / soft-delete)
# ---------------------------------------------------------------------------
def _product_from_body(product, data, creating):
    def need(field):
        if creating and data.get(field) in (None, ""):
            raise ApiError(f"'{field}' is required.")

    for f in ("name", "category_id", "price", "stock"):
        need(f)

    if "name" in data:
        name = str(data["name"]).strip()
        if len(name) < 2:
            raise ApiError("Name is too short.")
        product.name = name
    if "category_id" in data:
        cat = db.session.get(Category, int(data["category_id"]))
        if cat is None:
            raise ApiError("Unknown category.")
        product.category_id = cat.id
    try:
        if "price" in data:
            product.price = round(float(data["price"]), 2)
        if "mrp" in data and data["mrp"] not in (None, ""):
            product.mrp = round(float(data["mrp"]), 2)
        if "stock" in data:
            product.stock = int(data["stock"])
        if "rating" in data and data["rating"] not in (None, ""):
            product.rating = float(data["rating"])
    except (TypeError, ValueError):
        raise ApiError("Price, MRP and stock must be numbers.")

    if product.mrp is None or product.mrp < product.price:
        product.mrp = product.price
    if product.price < 0 or product.stock < 0:
        raise ApiError("Price and stock cannot be negative.")

    for f in ("brand", "unit", "description", "image_url"):
        if f in data:
            product.__setattr__(f, (str(data[f]).strip() or None) if data[f] is not None else None)
    if "is_veg" in data:
        product.is_veg = bool(data["is_veg"])
    if "is_active" in data:
        product.is_active = bool(data["is_active"])


@bp.get("/products")
@admin_required
def admin_products():
    query = Product.query
    q = (request.args.get("q") or "").strip()
    if q:
        query = query.filter(db.or_(Product.name.ilike(f"%{q}%"), Product.sku.ilike(f"%{q}%")))
    if request.args.get("category"):
        query = query.filter(Product.category_id == int(request.args["category"]))
    if request.args.get("show_inactive") != "1":
        query = query.filter(Product.is_active.is_(True))
    query = query.order_by(Product.id.desc())
    return ok(paginate(query, lambda p: p.to_dict(), default_per_page=25))


@bp.post("/products")
@admin_required
def create_product():
    data = body()
    sku = (data.get("sku") or "").strip()
    if sku:
        if not re.match(r"^[A-Za-z0-9-]{3,30}$", sku):
            raise ApiError("SKU may contain only letters, digits and '-'.")
        if Product.query.filter_by(sku=sku).first():
            raise ApiError("This SKU is already used by another product.", 409)

    product = Product(rating=0, rating_count=0, sku=sku or f"TMP-{uuid.uuid4().hex[:12]}")
    _product_from_body(product, data, creating=True)
    db.session.add(product)
    db.session.flush()  # gives product.id
    if not sku:
        product.sku = f"MM-{product.category_id:02d}-{product.id:04d}"
    db.session.commit()
    return ok({"product": product.to_dict(), "message": "Product added."}, 201)


@bp.put("/products/<int:product_id>")
@admin_required
def update_product(product_id):
    product = db.session.get(Product, product_id)
    if product is None:
        raise ApiError("Product not found.", 404)
    _product_from_body(product, body(), creating=False)
    db.session.commit()
    return ok({"product": product.to_dict(), "message": "Product updated."})


@bp.delete("/products/<int:product_id>")
@admin_required
def delete_product(product_id):
    """Soft delete: the product disappears from the shop but old orders keep their link."""
    product = db.session.get(Product, product_id)
    if product is None:
        raise ApiError("Product not found.", 404)
    product.is_active = False
    db.session.commit()
    return ok({"message": f"{product.name} removed from the shop."})


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------
@bp.get("/orders")
@admin_required
def admin_orders():
    query = Order.query
    status = request.args.get("status")
    if status:
        query = query.filter(Order.status == status)
    q = (request.args.get("q") or "").strip()
    if q:
        query = query.join(User).filter(
            db.or_(Order.order_number.ilike(f"%{q}%"), User.name.ilike(f"%{q}%"), User.email.ilike(f"%{q}%"))
        )
    query = query.order_by(Order.created_at.desc())
    return ok(paginate(query, lambda o: {**o.to_dict(with_items=True, with_user=True),
                                         "next_statuses": TRANSITIONS.get(o.status, [])},
                       default_per_page=15))


@bp.patch("/orders/<int:order_id>")
@admin_required
def update_order(order_id):
    order = db.session.get(Order, order_id)
    if order is None:
        raise ApiError("Order not found.", 404)
    new_status = body().get("status")
    if new_status not in ORDER_STATUSES:
        raise ApiError("Unknown status.")
    if new_status not in TRANSITIONS[order.status]:
        raise ApiError(f"Cannot change an order from {order.status} to {new_status}.")

    order.status = new_status
    if new_status == "Cancelled":
        order.payment_status = "Refunded" if order.payment_status == "Paid" else "Cancelled"
        restock(order)
    elif new_status == "Delivered" and order.payment_method == "COD":
        order.payment_status = "Paid"
    db.session.commit()
    return ok({"order": {**order.to_dict(with_items=True, with_user=True),
                         "next_statuses": TRANSITIONS[order.status]},
               "message": f"Order {order.order_number} marked {new_status}."})


# ---------------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------------
@bp.get("/customers")
@admin_required
def customers():
    spent = func.coalesce(func.sum(db.case((NOT_CANCELLED, Order.total), else_=0)), 0)
    query = (
        db.session.query(User, func.count(Order.id), spent)
        .outerjoin(Order, Order.user_id == User.id)
        .filter(User.role == "customer")
        .group_by(User.id)
        .order_by(spent.desc())
    )
    q = (request.args.get("q") or "").strip()
    if q:
        query = query.filter(db.or_(User.name.ilike(f"%{q}%"), User.email.ilike(f"%{q}%"), User.city.ilike(f"%{q}%")))
    rows = query.all()
    return ok({"customers": [{**u.to_dict(), "orders": c, "spent": round(float(s), 2)} for u, c, s in rows]})
