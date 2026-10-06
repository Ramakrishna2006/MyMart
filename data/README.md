# 📊 MyMart Dataset: Data Card

This folder holds the sample data that powers My Mart. It has **5 CSV files** that link to each other like database tables. On first start, `backend/app/seed.py` loads them into SQLite.

> **Synthetic data.** Every customer, e-mail (`@example.com`), phone number and brand name here is invented. Prices are realistic for Indian groceries in 2026, but they are not real offers.

| # | File | Rows | Columns | Primary key | Foreign keys |
|---|---|---:|---:|---|---|
| 1 | `categories.csv` | 12 | 5 | `id` | – |
| 2 | `products.csv` | 111 | 15 | `id` (also unique `sku`) | `category_id → categories.id` |
| 3 | `customers.csv` | 60 | 7 | `id` (also unique `email`) | – |
| 4 | `orders.csv` | 420 | 12 | `id` (also unique `order_number`) | `user_id → customers.id` |
| 5 | `order_items.csv` | 1,385 | 7 | `id` | `order_id → orders.id`, `product_id → products.id` |

```
categories 1 ──< products 1 ──< order_items >── 1 orders >── 1 customers
```

---

## How the data was made

`generate_dataset.py` uses only the Python standard library and `random.Random(42)`, so every run produces **exactly the same files**:

```bash
python data/generate_dataset.py
```

| Step | Logic |
|---|---|
| Products | Hand-written list of 111 common Indian grocery items with a realistic MRP. The discount is picked from {0, 5, 8, 10, 12, 15, 20}%. Stock is a random 15–200, but about 8 % of items get 0, 3 or 7 so the low-stock alert has something to show. |
| Customers | Random first + last name (no duplicates). The city is weighted (Hyderabad and Bengaluru are the most common). Join date is between Jan and Jun 2026. |
| Orders | 420 orders between 1 Apr and 30 Sep 2026, never before the customer joined. Some customers shop up to 6× more often than others, and about 35 % of orders are pushed to evening hours. |
| Order lines | 1–6 different products per order (3 is the most common), each with quantity 1–4. Fresh items (fruit, veg, dairy, bakery) and cheap items are picked more often. |
| Money | `line_total = unit_price × quantity`, `subtotal = Σ line_total`, `delivery_fee = 0 if subtotal ≥ 499 else 40`, `total = subtotal + delivery_fee` |
| Status | Orders older than 3 days: 94 % Delivered, 6 % Cancelled. The last few days are still Placed, Packed or Shipped. |
| Payment | 65 % UPI and 35 % COD. UPI → Paid. COD → Paid only once Delivered. Cancelled → Refunded (UPI) or Cancelled (COD). |

---

## Set 1: `categories.csv` 🗂️

The aisles of the store.

| Column | Type | Description | Example |
|---|---|---|---|
| `id` | int | Primary key | `3` |
| `name` | text | Display name | `Dairy & Eggs` |
| `slug` | text | URL-friendly name (`/?category=dairy-eggs`) | `dairy-eggs` |
| `emoji` | text | Icon used as the product image placeholder | `🥛` |
| `description` | text | One-line description | `Milk, curd, paneer, butter, cheese and eggs` |

## Set 2: `products.csv` 📦

The product catalogue.

| Column | Type | Description | Example |
|---|---|---|---|
| `id` | int | Primary key | `24` |
| `sku` | text | Stock Keeping Unit, `MM-<category>-<id>` | `MM-03-0024` |
| `name` | text | Product name | `Malai Paneer` |
| `brand` | text | Fictional brand | `DairyDay` |
| `category_id` | int | FK → `categories.id` | `3` |
| `unit` | text | Pack size | `200 g` |
| `mrp` | decimal ₹ | Maximum Retail Price | `90.00` |
| `price` | decimal ₹ | Selling price (≤ MRP) | `85.50` |
| `discount_pct` | int % | `round((mrp − price) / mrp × 100)` | `5` |
| `stock` | int | Units available | `64` |
| `rating` | decimal | Average rating, 3.4–4.9 | `4.3` |
| `rating_count` | int | Number of ratings (drives "Popular" sort) | `812` |
| `is_veg` | 0/1 | 1 = vegetarian, 0 = non-veg (eggs, plum cake, chicken masala) | `1` |
| `description` | text | Short description | `Malai Paneer from DairyDay - chilled and delivered fresh.` |
| `created_at` | datetime | Added to catalogue (Jan–Mar 2026) | `2026-02-11 10:22:05` |

## Set 3: `customers.csv` 👥

Registered shoppers. In the database they live in the `users` table with `role = 'customer'`. The admin account is not part of the CSV; it is created from `.env`.

| Column | Type | Description | Example |
|---|---|---|---|
| `id` | int | Primary key | `11` |
| `name` | text | Full name | `Rohan Iyer` |
| `email` | text | Login e-mail (unique, `@example.com`) | `rohan.iyer11@example.com` |
| `phone` | text | 10-digit mobile starting with 9 | `9530256336` |
| `city` / `state` | text | Location | `Bengaluru` / `Karnataka` |
| `joined_at` | datetime | Registration date | `2026-03-04 18:20:11` |

Password: all demo customers use **`Customer@123`**. Only a salted hash is stored, never the password itself.

## Set 4: `orders.csv` 🧾

One row per checkout.

| Column | Type | Description | Example |
|---|---|---|---|
| `id` | int | Primary key | `57` |
| `order_number` | text | `MM<yymm>-<id>` | `MM2605-00057` |
| `user_id` | int | FK → `customers.id` | `29` |
| `created_at` | datetime | Order time | `2026-05-14 19:41:07` |
| `status` | text | Placed / Packed / Shipped / Delivered / Cancelled | `Delivered` |
| `payment_method` | text | `UPI` or `COD` | `UPI` |
| `payment_status` | text | Paid / Pending / Refunded / Cancelled | `Paid` |
| `items_count` | int | Total units | `6` |
| `subtotal` | decimal ₹ | Σ line totals | `512.40` |
| `delivery_fee` | decimal ₹ | 0 or 40 | `0.00` |
| `total` | decimal ₹ | subtotal + delivery_fee | `512.40` |
| `delivery_city` | text | Delivery city | `Chennai` |

## Set 5: `order_items.csv` 🛒

One row per product inside an order. This is the bridge table between orders and products.

| Column | Type | Description | Example |
|---|---|---|---|
| `id` | int | Primary key | `201` |
| `order_id` | int | FK → `orders.id` | `57` |
| `product_id` | int | FK → `products.id` | `24` |
| `product_name` | text | Name **at purchase time** (snapshot) | `Malai Paneer` |
| `unit_price` | decimal ₹ | Price **at purchase time** (snapshot) | `85.50` |
| `quantity` | int | Units, 1–4 | `2` |
| `line_total` | decimal ₹ | unit_price × quantity | `171.00` |

---

## Summary statistics

| Metric | Value |
|---|---|
| Date range | 2 Apr 2026 – 30 Sep 2026 |
| Orders (all / non-cancelled) | 420 / 396 |
| Revenue (non-cancelled) | ₹1,64,336 |
| Average order value | ₹415 |
| Cancelled | 24 orders (5.7 %) |
| Payment split | UPI 65 % · COD 35 % |
| Units sold | 2,211 across 1,385 lines (3.3 lines per order) |
| Products sold at least once | 111 / 111 |
| Average product price / rating | ₹100 / 4.1 ★ |

## Example questions to explore

* Which category earns the most revenue? (Fruits)
* What's the monthly revenue trend? (It rises from April and peaks in August.)
* Do customers prefer UPI or Cash on Delivery?
* Which products should be restocked first?
* Which city has the highest average order value?

Load the files in pandas for your own analysis:

```python
import pandas as pd
orders = pd.read_csv("data/orders.csv", parse_dates=["created_at"])
items  = pd.read_csv("data/order_items.csv")
orders[orders.status != "Cancelled"].groupby(orders.created_at.dt.to_period("M"))["total"].sum()
```

## Known limitations

* The data is synthetic, so the patterns are simplified (no seasonality per product, no returns or partial refunds).
* Customer addresses are not included; seeded orders use `"Demo address"`.
* `rating` and `rating_count` are generated values, not computed from reviews.
