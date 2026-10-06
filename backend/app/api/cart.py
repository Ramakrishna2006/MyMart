"""Shopping cart API (one cart per logged-in user, stored in the cart_items table)."""

from flask import Blueprint, current_app
from flask_login import current_user, login_required

from ..extensions import db
from ..models import CartItem, Product
from ..utils import ApiError, body, ok

bp = Blueprint("cart", __name__, url_prefix="/api/cart")


def cart_summary(user_id):
    """Build the cart response: lines, totals and delivery fee."""
    cfg = current_app.config
    lines = (
        CartItem.query.filter_by(user_id=user_id)
        .join(Product)
        .order_by(CartItem.added_at, CartItem.id)
        .all()
    )
    items, subtotal, savings, count = [], 0.0, 0.0, 0
    for line in lines:
        p = line.product
        line_total = round(p.price * line.quantity, 2)
        subtotal += line_total
        savings += (p.mrp - p.price) * line.quantity
        count += line.quantity
        items.append({
            "product": p.to_dict(),
            "quantity": line.quantity,
            "line_total": line_total,
            "available": p.is_active and p.stock >= line.quantity,
        })
    subtotal = round(subtotal, 2)
    delivery = 0 if subtotal == 0 or subtotal >= cfg["FREE_DELIVERY_ABOVE"] else cfg["DELIVERY_FEE"]
    return {
        "items": items,
        "items_count": count,
        "subtotal": subtotal,
        "savings": round(savings, 2),
        "delivery_fee": delivery,
        "total": round(subtotal + delivery, 2),
        "free_delivery_above": cfg["FREE_DELIVERY_ABOVE"],
        "amount_for_free_delivery": max(0, round(cfg["FREE_DELIVERY_ABOVE"] - subtotal, 2)) if subtotal else 0,
    }


def _get_product(product_id):
    product = db.session.get(Product, product_id)
    if product is None or not product.is_active:
        raise ApiError("Product not found.", 404)
    return product


def _validate_qty(product, qty):
    max_qty = current_app.config["MAX_QTY_PER_ITEM"]
    if qty < 1:
        raise ApiError("Quantity must be at least 1.")
    if qty > max_qty:
        raise ApiError(f"You can buy at most {max_qty} of an item per order.")
    if qty > product.stock:
        if product.stock == 0:
            raise ApiError(f"{product.name} is out of stock.")
        raise ApiError(f"Only {product.stock} units of {product.name} are available.")


@bp.get("")
@login_required
def get_cart():
    return ok(cart_summary(current_user.id))


@bp.post("")
@login_required
def add_item():
    """Body: {"product_id": 5, "quantity": 1}  - adds to the existing quantity."""
    data = body()
    try:
        product_id = int(data.get("product_id"))
        qty = int(data.get("quantity", 1))
    except (TypeError, ValueError):
        raise ApiError("product_id and quantity must be numbers.")

    product = _get_product(product_id)
    line = CartItem.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    new_qty = (line.quantity if line else 0) + qty
    _validate_qty(product, new_qty)

    if line:
        line.quantity = new_qty
    else:
        db.session.add(CartItem(user_id=current_user.id, product_id=product_id, quantity=new_qty))
    db.session.commit()
    return ok({**cart_summary(current_user.id), "message": f"{product.name} added to cart"})


@bp.patch("/<int:product_id>")
@login_required
def update_item(product_id):
    """Body: {"quantity": 3}  - sets the quantity (0 removes the line)."""
    try:
        qty = int(body().get("quantity"))
    except (TypeError, ValueError):
        raise ApiError("quantity must be a number.")

    line = CartItem.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    if line is None:
        raise ApiError("This product is not in your cart.", 404)
    if qty <= 0:
        db.session.delete(line)
    else:
        _validate_qty(_get_product(product_id), qty)
        line.quantity = qty
    db.session.commit()
    return ok(cart_summary(current_user.id))


@bp.delete("/<int:product_id>")
@login_required
def remove_item(product_id):
    CartItem.query.filter_by(user_id=current_user.id, product_id=product_id).delete()
    db.session.commit()
    return ok(cart_summary(current_user.id))


@bp.delete("")
@login_required
def clear_cart():
    CartItem.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    return ok(cart_summary(current_user.id))
