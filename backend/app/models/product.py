from datetime import datetime

from ..extensions import db

Money = db.Numeric(10, 2, asdecimal=False)


class Product(db.Model):
    """Set 2 - an item that can be bought."""

    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(30), unique=True, nullable=False)
    name = db.Column(db.String(150), nullable=False, index=True)
    brand = db.Column(db.String(80))
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False, index=True)
    unit = db.Column(db.String(40))                  # "1 kg", "500 ml", "6 pcs"
    mrp = db.Column(Money, nullable=False)           # maximum retail price
    price = db.Column(Money, nullable=False)         # selling price
    stock = db.Column(db.Integer, nullable=False, default=0)
    rating = db.Column(db.Float, default=0)
    rating_count = db.Column(db.Integer, default=0)
    is_veg = db.Column(db.Boolean, default=True)
    description = db.Column(db.Text)
    image_url = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True, nullable=False)  # soft delete
    created_at = db.Column(db.DateTime, default=datetime.now)

    category = db.relationship("Category", back_populates="products")

    __table_args__ = (
        db.CheckConstraint("stock >= 0", name="ck_product_stock_positive"),
        db.CheckConstraint("price >= 0", name="ck_product_price_positive"),
    )

    @property
    def discount_pct(self):
        if not self.mrp or self.mrp <= self.price:
            return 0
        return round((self.mrp - self.price) * 100 / self.mrp)

    def to_dict(self):
        return {
            "id": self.id,
            "sku": self.sku,
            "name": self.name,
            "brand": self.brand,
            "category_id": self.category_id,
            "category": self.category.name if self.category else None,
            "emoji": self.category.emoji if self.category else "🛍️",
            "unit": self.unit,
            "mrp": self.mrp,
            "price": self.price,
            "discount_pct": self.discount_pct,
            "stock": self.stock,
            "in_stock": self.stock > 0,
            "rating": self.rating,
            "rating_count": self.rating_count,
            "is_veg": self.is_veg,
            "description": self.description,
            "image_url": self.image_url,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
