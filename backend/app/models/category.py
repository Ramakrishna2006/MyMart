from ..extensions import db


class Category(db.Model):
    """Set 1 - a group of related products (Fruits, Dairy, ...)."""

    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    slug = db.Column(db.String(80), unique=True, nullable=False)
    emoji = db.Column(db.String(8), default="🛍️")
    description = db.Column(db.String(255))

    products = db.relationship("Product", back_populates="category", lazy="dynamic")

    def to_dict(self, with_count=False):
        data = {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "emoji": self.emoji,
            "description": self.description,
        }
        if with_count:
            data["product_count"] = self.products.filter_by(is_active=True).count()
        return data
