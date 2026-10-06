# 🔌 MyMart REST API reference

Base URL: `http://localhost:5000/api`

* Requests and responses are JSON (`Content-Type: application/json`).
* Authentication uses a **session cookie** set by `/api/auth/login`. The frontend sends it automatically.
* Errors always look like `{"error": "message"}`, with status `400` (bad input), `401` (not logged in), `403` (not admin), `404` (not found) or `409` (conflict).
* Lists are paginated: `?page=1&per_page=20` → `{"items": [...], "page", "per_page", "pages", "total"}`.

---

## Auth

### `POST /auth/register`
```json
{ "name": "Ravi Kumar", "email": "ravi@example.com", "password": "secret1", "phone": "9876543210", "city": "Hyderabad" }
```
→ `201 {"user": {...}, "message": "Account created!"}`. The new user is logged in right away.

### `POST /auth/login`
```json
{ "email": "admin@mymart.com", "password": "Admin@123", "remember": true }
```
→ `200 {"user": {"id": 61, "name": "Admin", "role": "admin", "is_admin": true, ...}}`

### `POST /auth/logout` · `GET /auth/me`
`/auth/me` returns `{"user": null}` when nobody is logged in.

---

## Catalogue (public)

### `GET /categories`
```json
{ "categories": [ { "id": 1, "name": "Fruits", "slug": "fruits", "emoji": "🍎", "description": "...", "product_count": 10 } ] }
```

### `GET /products`
| Param | Example | Meaning |
|---|---|---|
| `q` | `milk` | Search name, brand and description |
| `category` | `3` or `dairy-eggs` | Category id or slug |
| `sort` | `popular` · `price_asc` · `price_desc` · `discount` · `rating` · `newest` · `name` | Sort order |
| `veg` | `1` | Vegetarian only |
| `in_stock` | `1` | Hide out-of-stock items |
| `min_price` / `max_price` | `50` / `200` | Price range |

```bash
curl "http://localhost:5000/api/products?category=fruits&sort=price_asc&per_page=3"
```

Each product looks like this:
```json
{ "id": 24, "sku": "MM-03-0024", "name": "Malai Paneer", "brand": "DairyDay", "category_id": 3,
  "category": "Dairy & Eggs", "emoji": "🥛", "unit": "200 g", "mrp": 90.0, "price": 85.5,
  "discount_pct": 5, "stock": 64, "in_stock": true, "rating": 4.3, "rating_count": 812,
  "is_veg": true, "description": "...", "image_url": null, "is_active": true, "created_at": "..." }
```

### `GET /products/<id>`
→ `{"product": {...}, "units_sold": 37, "related": [ up to 4 products ]}`

---

## Cart (login required)

| Method | Endpoint | Body | Effect |
|---|---|---|---|
| GET | `/cart` | – | Current cart |
| POST | `/cart` | `{"product_id": 5, "quantity": 1}` | Add (adds to the existing quantity) |
| PATCH | `/cart/<product_id>` | `{"quantity": 3}` | Set quantity (0 removes the line) |
| DELETE | `/cart/<product_id>` | – | Remove one line |
| DELETE | `/cart` | – | Empty the cart |

Every cart call returns the full summary:
```json
{ "items": [ { "product": {...}, "quantity": 2, "line_total": 171.0, "available": true } ],
  "items_count": 2, "subtotal": 171.0, "savings": 9.0, "delivery_fee": 40, "total": 211.0,
  "free_delivery_above": 499, "amount_for_free_delivery": 328.0 }
```
Rules: you can't add more than the available stock or more than 10 of one item.

---

## Checkout & orders (login required)

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/checkout/upi` | `{upi_id, payee, amount, upi_link}` for the cart total |
| GET | `/checkout/upi-qr.png` | PNG QR code for the `upi://pay?...` link |
| POST | `/orders` | Place an order from the cart |
| GET | `/orders` | My orders (newest first, with items) |
| GET | `/orders/<id>` | One order |
| POST | `/orders/<id>/cancel` | Cancel when status is Placed or Packed (items are restocked) |

`POST /orders` body:
```json
{ "payment_method": "UPI", "upi_ref": "ravi@okbank",
  "delivery_name": "Ravi", "delivery_phone": "9876543210",
  "delivery_address": "12 MG Road", "delivery_city": "Hyderabad" }
```
→ `201 {"order": {"order_number": "MM2610-00421", "status": "Placed", "payment_status": "Paid", "items": [...], ...}}`
`COD` orders start with `payment_status: "Pending"`, which becomes `Paid` when the order is delivered.

---

## Admin (admin login required)

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/admin/stats` | revenue, orders, avg order value, customers, products, pending orders, low-stock list |
| GET | `/admin/analytics` | sales by month / category / city / weekday, top products, payment split, status counts, top customers |
| GET | `/admin/products?q=&category=&show_inactive=1` | Product table |
| POST | `/admin/products` | Create: `{name, category_id, price, stock, mrp?, brand?, unit?, description?, image_url?, is_veg?, sku?}` |
| PUT | `/admin/products/<id>` | Update any of the fields above |
| DELETE | `/admin/products/<id>` | Soft delete (hidden from the shop) |
| GET | `/admin/orders?status=&q=` | Orders with customer, items and `next_statuses` |
| PATCH | `/admin/orders/<id>` | `{"status": "Packed"}`. Only allowed moves are accepted. |
| GET | `/admin/customers?q=` | Customers with order count and total spent |

Allowed status moves:
```
Placed  → Packed | Cancelled
Packed  → Shipped | Cancelled
Shipped → Delivered | Cancelled
Delivered, Cancelled → (final)
```

---

## Dataset explorer (public)

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/dataset` | All 5 sets: summary, purpose, used_in, relations, rules, columns, live stats + chart data |
| GET | `/dataset/<key>?q=&page=&per_page=` | Rows of one set (`categories`, `products`, `customers`, `orders`, `order_items`) |
| GET | `/dataset/<key>/download` | Live table as CSV |
| GET | `/dataset/<key>/original` | The original file from `data/` |

## Health
`GET /health` → `{"status": "ok", "app": "MyMart"}`
