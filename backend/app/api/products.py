"""Public catalogue API: categories and products (search, filter, sort, paginate)."""

from flask import Blueprint, request

from ..extensions import db
from ..models import Category, OrderItem, Product
from ..utils import ApiError, ok, paginate

bp = Blueprint("products", __name__, url_prefix="/api")

SORTS = {
    "popular": None,  # handled below (rating_count)
    "price_asc": Product.price.asc(),
    "price_desc": Product.price.desc(),
    "rating": Product.rating.desc(),
    "newest": Product.created_at.desc(),
    "name": Product.name.asc(),
}


@bp.get("/categories")
def categories():
    cats = Category.query.order_by(Category.id).all()
    return ok({"categories": [c.to_dict(with_count=True) for c in cats]})


@bp.get("/products")
def list_products():
    """
    Query parameters
      q         text search in name / brand / description
      category  category id or slug
      sort      popular | price_asc | price_desc | rating | newest | name | discount
      veg       1 = vegetarian only
      in_stock  1 = hide out-of-stock items
      min_price / max_price
      page / per_page
    """
    query = Product.query.filter(Product.is_active.is_(True))

    q = (request.args.get("q") or "").strip()
    if q:
        like = f"%{q}%"
        query = query.filter(
            db.or_(Product.name.ilike(like), Product.brand.ilike(like), Product.description.ilike(like))
        )

    category = request.args.get("category")
    if category:
        if category.isdigit():
            query = query.filter(Product.category_id == int(category))
        else:
            query = query.join(Category).filter(Category.slug == category)

    if request.args.get("veg") == "1":
        query = query.filter(Product.is_veg.is_(True))
    if request.args.get("in_stock") == "1":
        query = query.filter(Product.stock > 0)

    for arg, op in (("min_price", "__ge__"), ("max_price", "__le__")):
        value = request.args.get(arg)
        if value:
            try:
                query = query.filter(getattr(Product.price, op)(float(value)))
            except ValueError:
                raise ApiError(f"{arg} must be a number")

    sort = request.args.get("sort", "popular")
    if sort == "discount":
        query = query.order_by(((Product.mrp - Product.price) / Product.mrp).desc())
    elif sort in SORTS and SORTS[sort] is not None:
        query = query.order_by(SORTS[sort], Product.id)
    else:
        query = query.order_by(Product.rating_count.desc(), Product.id)

    return ok(paginate(query, lambda p: p.to_dict(), default_per_page=24))


@bp.get("/products/<int:product_id>")
def product_detail(product_id):
    product = db.session.get(Product, product_id)
    if product is None or not product.is_active:
        raise ApiError("Product not found.", 404)

    related = (
        Product.query.filter(
            Product.category_id == product.category_id,
            Product.id != product.id,
            Product.is_active.is_(True),
        )
        .order_by(Product.rating_count.desc())
        .limit(4)
        .all()
    )
    sold = (
        db.session.query(db.func.coalesce(db.func.sum(OrderItem.quantity), 0))
        .filter(OrderItem.product_id == product.id)
        .scalar()
    )
    return ok({"product": product.to_dict(), "units_sold": int(sold), "related": [p.to_dict() for p in related]})
