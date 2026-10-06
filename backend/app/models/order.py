from datetime import datetime

from ..extensions import db
from .product import Money

# Allowed order life-cycle:  Placed -> Packed -> Shipped -> Delivered
#                            (Placed/Packed/Shipped) -> Cancelled
ORDER_STATUSES = ["Placed", "Packed", "Shipped", "Delivered", "Cancelled"]
PAYMENT_METHODS = ["UPI", "COD"]


class Order(db.Model):
    """Set 4 - one checkout = one order (the 'header' / receipt)."""

    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(20), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.now, index=True)
    status = db.Column(db.String(20), nullable=False, default="Placed")
    payment_method = db.Column(db.String(10), nullable=False, default="UPI")
    payment_status = db.Column(db.String(20), nullable=False, default="Pending")
    upi_ref = db.Column(db.String(150))
    items_count = db.Column(db.Integer, nullable=False, default=0)
    subtotal = db.Column(Money, nullable=False, default=0)
    delivery_fee = db.Column(Money, nullable=False, default=0)
    total = db.Column(Money, nullable=False, default=0)
    delivery_name = db.Column(db.String(120))
    delivery_phone = db.Column(db.String(15))
    delivery_address = db.Column(db.String(255))
    delivery_city = db.Column(db.String(80))

    user = db.relationship("User", back_populates="orders")
    items = db.relationship(
        "OrderItem", back_populates="order", cascade="all, delete-orphan", lazy="selectin"
    )

    def to_dict(self, with_items=False, with_user=False):
        data = {
            "id": self.id,
            "order_number": self.order_number,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "status": self.status,
            "payment_method": self.payment_method,
            "payment_status": self.payment_status,
            "items_count": self.items_count,
            "subtotal": self.subtotal,
            "delivery_fee": self.delivery_fee,
            "total": self.total,
            "delivery_name": self.delivery_name,
            "delivery_phone": self.delivery_phone,
            "delivery_address": self.delivery_address,
            "delivery_city": self.delivery_city,
            "can_cancel": self.status in ("Placed", "Packed"),
        }
        if with_items:
            data["items"] = [i.to_dict() for i in self.items]
        if with_user and self.user:
            data["customer"] = {"id": self.user.id, "name": self.user.name, "email": self.user.email}
        return data


class OrderItem(db.Model):
    """Set 5 - one product line inside an order.

    product_name and unit_price are copied at purchase time, so the receipt
    stays correct even if the product is later renamed, re-priced or removed.
    """

    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), index=True)
    product_name = db.Column(db.String(150), nullable=False)
    unit_price = db.Column(Money, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    line_total = db.Column(Money, nullable=False)

    order = db.relationship("Order", back_populates="items")
    product = db.relationship("Product")

    def to_dict(self):
        return {
            "id": self.id,
            "order_id": self.order_id,
            "product_id": self.product_id,
            "product_name": self.product_name,
            "unit_price": self.unit_price,
            "quantity": self.quantity,
            "line_total": self.line_total,
            "emoji": self.product.category.emoji if self.product and self.product.category else "🛍️",
        }
