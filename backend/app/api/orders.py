"""Checkout + customer order history."""

from io import BytesIO
from urllib.parse import quote

from flask import Blueprint, Response, current_app
from flask_login import current_user, login_required

from ..extensions import db
from ..models import CartItem, Order, OrderItem, Product
from ..models.order import PAYMENT_METHODS
from ..utils import ApiError, body, ok, paginate
from .cart import cart_summary

bp = Blueprint("orders", __name__, url_prefix="/api")


def _upi_link(amount):
    cfg = current_app.config
    return (
        "upi://pay?"
        f"pa={quote(cfg['MERCHANT_UPI_ID'])}"
        f"&pn={quote(cfg['MERCHANT_NAME'])}"
        f"&am={amount:.2f}&cu=INR"
        f"&tn={quote('MyMart order')}"
    )


@bp.get("/checkout/upi")
@login_required
def upi_details():
    summary = cart_summary(current_user.id)
    if not summary["items"]:
        raise ApiError("Your cart is empty.")
    return ok({
        "upi_id": current_app.config["MERCHANT_UPI_ID"],
        "payee": current_app.config["MERCHANT_NAME"],
        "amount": summary["total"],
        "upi_link": _upi_link(summary["total"]),
    })


@bp.get("/checkout/upi-qr.png")
@login_required
def upi_qr():
    """PNG QR code that any UPI app (GPay, PhonePe, Paytm...) can scan."""
    import qrcode  # imported lazily so the rest of the app works without it

    summary = cart_summary(current_user.id)
    if not summary["items"]:
        raise ApiError("Your cart is empty.")
    img = qrcode.make(_upi_link(summary["total"]), box_size=8, border=2)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return Response(buf.getvalue(), mimetype="image/png", headers={"Cache-Control": "no-store"})


def _next_order_number(order_id):
    from datetime import datetime

    return f"MM{datetime.now():%y%m}-{order_id:05d}"


@bp.post("/orders")
@login_required
def place_order():
    """
    Body:
      {
        "payment_method": "UPI" | "COD",
        "upi_ref": "name@okbank or UPI transaction id"   (required for UPI),
        "delivery_name": "...", "delivery_phone": "...",
        "delivery_address": "...", "delivery_city": "..."
      }
    """
    data = body()
    method = (data.get("payment_method") or "UPI").upper()
    if method not in PAYMENT_METHODS:
        raise ApiError("payment_method must be UPI or COD.")
    upi_ref = (data.get("upi_ref") or "").strip()
    if method == "UPI" and not upi_ref:
        raise ApiError("Please enter your UPI ID / transaction reference.")

    name = (data.get("delivery_name") or current_user.name or "").strip()
    phone = (data.get("delivery_phone") or current_user.phone or "").strip()
    address = (data.get("delivery_address") or "").strip()
    city = (data.get("delivery_city") or current_user.city or "").strip()
    if not address or not city:
        raise ApiError("Please enter your delivery address and city.")

    lines = CartItem.query.filter_by(user_id=current_user.id).all()
    if not lines:
        raise ApiError("Your cart is empty.")

    # Re-check stock inside the same transaction that reduces it
    for line in lines:
        p = db.session.get(Product, line.product_id)
        if p is None or not p.is_active:
            raise ApiError("A product in your cart is no longer available. Please review your cart.", 409)
        if line.quantity > p.stock:
            raise ApiError(f"Only {p.stock} units of {p.name} left. Please update your cart.", 409)

    summary = cart_summary(current_user.id)
    order = Order(
        order_number="TEMP",
        user_id=current_user.id,
        status="Placed",
        payment_method=method,
        # NOTE: demo project - UPI payments are trusted, not verified with a bank/gateway
        payment_status="Paid" if method == "UPI" else "Pending",
        upi_ref=upi_ref or None,
        items_count=summary["items_count"],
        subtotal=summary["subtotal"],
        delivery_fee=summary["delivery_fee"],
        total=summary["total"],
        delivery_name=name,
        delivery_phone=phone,
        delivery_address=address,
        delivery_city=city,
    )
    db.session.add(order)
    db.session.flush()  # gives order.id
    order.order_number = _next_order_number(order.id)

    for line in lines:
        p = line.product
        db.session.add(OrderItem(
            order_id=order.id, product_id=p.id, product_name=p.name,
            unit_price=p.price, quantity=line.quantity,
            line_total=round(p.price * line.quantity, 2),
        ))
        p.stock -= line.quantity
        db.session.delete(line)

    db.session.commit()
    return ok({"order": order.to_dict(with_items=True), "message": "Order placed successfully!"}, 201)


@bp.get("/orders")
@login_required
def my_orders():
    query = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc())
    return ok(paginate(query, lambda o: o.to_dict(with_items=True), default_per_page=10))


def _own_order(order_id):
    order = db.session.get(Order, order_id)
    if order is None or (order.user_id != current_user.id and not current_user.is_admin):
        raise ApiError("Order not found.", 404)
    return order


@bp.get("/orders/<int:order_id>")
@login_required
def order_detail(order_id):
    return ok({"order": _own_order(order_id).to_dict(with_items=True)})


def restock(order):
    for item in order.items:
        if item.product:
            item.product.stock += item.quantity


@bp.post("/orders/<int:order_id>/cancel")
@login_required
def cancel_order(order_id):
    order = _own_order(order_id)
    if order.status not in ("Placed", "Packed"):
        raise ApiError(f"An order that is {order.status} cannot be cancelled.")
    order.status = "Cancelled"
    order.payment_status = "Refunded" if order.payment_status == "Paid" else "Cancelled"
    restock(order)
    db.session.commit()
    return ok({"order": order.to_dict(with_items=True), "message": "Order cancelled."})
