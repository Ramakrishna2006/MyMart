"""
API tests. Run from the project root with either:

    python -m unittest discover backend/tests -v
    pytest            (if you have pytest installed)

Each test gets a fresh in-memory database loaded with the sample dataset.
"""

import unittest

from backend.app import create_app
from backend.app.config import TestConfig
from backend.app.extensions import db
from backend.app.models import Order, Product


class MyMartTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        db.engine.dispose()
        self.ctx.pop()

    # helpers ---------------------------------------------------------------
    def login(self, email="ananya.gupta1@example.com", password="Customer@123"):
        return self.client.post("/api/auth/login", json={"email": email, "password": password})

    def login_admin(self):
        return self.login("admin@mymart.com", "Admin@123")

    def in_stock_product(self, minimum=5):
        return Product.query.filter(Product.stock >= minimum, Product.is_active.is_(True)).first()


class TestCatalogue(MyMartTestCase):
    def test_dataset_loaded(self):
        r = self.client.get("/api/categories")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json["categories"]), 12)
        self.assertEqual(self.client.get("/api/products").json["total"], 111)

    def test_search_and_filter(self):
        r = self.client.get("/api/products?q=milk")
        self.assertTrue(all("milk" in (p["name"] + p["description"] + p["brand"]).lower() for p in r.json["items"]))
        r = self.client.get("/api/products?category=dairy-eggs&veg=1")
        self.assertTrue(all(p["category"] == "Dairy & Eggs" and p["is_veg"] for p in r.json["items"]))

    def test_sort_by_price(self):
        prices = [p["price"] for p in self.client.get("/api/products?sort=price_asc&per_page=50").json["items"]]
        self.assertEqual(prices, sorted(prices))

    def test_unknown_product_404(self):
        r = self.client.get("/api/products/99999")
        self.assertEqual(r.status_code, 404)
        self.assertIn("error", r.json)


class TestAuth(MyMartTestCase):
    def test_register_login_logout(self):
        r = self.client.post("/api/auth/register", json={
            "name": "Test User", "email": "test@example.com", "password": "secret1", "phone": "9876543210"})
        self.assertEqual(r.status_code, 201)
        self.assertEqual(self.client.get("/api/auth/me").json["user"]["email"], "test@example.com")
        self.client.post("/api/auth/logout")
        self.assertIsNone(self.client.get("/api/auth/me").json["user"])
        self.assertEqual(self.login("test@example.com", "secret1").status_code, 200)

    def test_duplicate_email(self):
        r = self.client.post("/api/auth/register", json={
            "name": "Again", "email": "ananya.gupta1@example.com", "password": "secret1"})
        self.assertEqual(r.status_code, 409)

    def test_wrong_password(self):
        self.assertEqual(self.login(password="nope").status_code, 401)

    def test_cart_requires_login(self):
        self.assertEqual(self.client.get("/api/cart").status_code, 401)


class TestCartAndCheckout(MyMartTestCase):
    def test_full_purchase_reduces_stock(self):
        self.login()
        product = self.in_stock_product()
        stock_before = product.stock

        r = self.client.post("/api/cart", json={"product_id": product.id, "quantity": 2})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json["items_count"], 2)

        r = self.client.post("/api/orders", json={
            "payment_method": "COD", "delivery_address": "12 MG Road", "delivery_city": "Hyderabad"})
        self.assertEqual(r.status_code, 201, r.json)
        order = r.json["order"]
        self.assertEqual(order["status"], "Placed")
        self.assertEqual(order["payment_status"], "Pending")
        self.assertAlmostEqual(order["subtotal"], round(product.price * 2, 2))

        db.session.refresh(product)
        self.assertEqual(product.stock, stock_before - 2)
        self.assertEqual(self.client.get("/api/cart").json["items_count"], 0)

        # cancelling puts the stock back
        r = self.client.post(f"/api/orders/{order['id']}/cancel")
        self.assertEqual(r.json["order"]["status"], "Cancelled")
        db.session.refresh(product)
        self.assertEqual(product.stock, stock_before)

    def test_cannot_exceed_stock(self):
        self.login()
        product = Product.query.filter(Product.stock > 0, Product.stock < 10).first()
        r = self.client.post("/api/cart", json={"product_id": product.id, "quantity": product.stock + 1})
        self.assertEqual(r.status_code, 400)

    def test_upi_needs_reference(self):
        self.login()
        self.client.post("/api/cart", json={"product_id": self.in_stock_product().id})
        r = self.client.post("/api/orders", json={
            "payment_method": "UPI", "delivery_address": "x", "delivery_city": "y"})
        self.assertEqual(r.status_code, 400)

    def test_delivery_fee_rule(self):
        self.login()
        cheap = Product.query.filter(Product.price < 100, Product.stock > 0).first()
        cart = self.client.post("/api/cart", json={"product_id": cheap.id}).json
        self.assertEqual(cart["delivery_fee"], 40)

    def test_upi_qr_png(self):
        self.login()
        self.client.post("/api/cart", json={"product_id": self.in_stock_product().id})
        r = self.client.get("/api/checkout/upi-qr.png")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.mimetype, "image/png")


class TestAdmin(MyMartTestCase):
    def test_customer_is_blocked(self):
        self.login()
        self.assertEqual(self.client.get("/api/admin/stats").status_code, 403)

    def test_stats_and_analytics(self):
        self.login_admin()
        stats = self.client.get("/api/admin/stats").json
        self.assertEqual(stats["orders"], 420)
        self.assertGreater(stats["revenue"], 0)
        analytics = self.client.get("/api/admin/analytics").json
        self.assertEqual(len(analytics["sales_by_month"]), 6)
        self.assertEqual(len(analytics["top_products"]), 10)

    def test_product_crud(self):
        self.login_admin()
        r = self.client.post("/api/admin/products", json={
            "name": "Test Honey", "category_id": 9, "price": 199, "mrp": 249, "stock": 20, "unit": "250 g"})
        self.assertEqual(r.status_code, 201, r.json)
        pid = r.json["product"]["id"]
        self.assertEqual(r.json["product"]["discount_pct"], 20)

        r = self.client.put(f"/api/admin/products/{pid}", json={"price": 179})
        self.assertEqual(r.json["product"]["price"], 179)

        self.client.delete(f"/api/admin/products/{pid}")
        self.assertEqual(self.client.get(f"/api/products/{pid}").status_code, 404)

    def test_order_status_flow(self):
        self.login_admin()
        order = Order.query.filter_by(status="Delivered").first()
        r = self.client.patch(f"/api/admin/orders/{order.id}", json={"status": "Placed"})
        self.assertEqual(r.status_code, 400)  # cannot go backwards


class TestDataset(MyMartTestCase):
    def test_list_and_rows(self):
        sets = self.client.get("/api/dataset").json["datasets"]
        self.assertEqual([s["key"] for s in sets], ["categories", "products", "customers", "orders", "order_items"])
        rows = self.client.get("/api/dataset/customers").json
        self.assertNotIn("phone", rows["columns"])
        self.assertIn("***", rows["items"][0]["email"])

    def test_download_csv(self):
        r = self.client.get("/api/dataset/products/download")
        self.assertEqual(r.mimetype, "text/csv")
        self.assertIn("sku", r.get_data(as_text=True).splitlines()[0])


if __name__ == "__main__":
    unittest.main()
