# ⬆️ Upgrade notes: v1 → v2

The original project was a single Flask app with Jinja templates (`main.py`, `routes/`, `templates/`). Version 2 turns it into a frontend + backend project that's ready for GitHub.

## Bugs fixed from v1

| v1 problem | v2 fix |
|---|---|
| The database path was hard-coded to `C:/Users/ramks/OneDrive/Desktop/my_mart/...`, so the app only ran on one PC | Path is built from the project folder (`backend/instance/mymart.db`) and can be overridden in `.env` |
| `config.py` existed but was never used, and two different secret keys were in the code | One `Config` class that reads `.env` |
| `create_admin.py` passed `phone=` and `role=` to `User`, but the model had neither, so the script crashed | `User` now has `phone`, `role` and `city`. The admin is created automatically. |
| Register form sent `phone`, but the route ignored it | Phone is validated and saved |
| Admin dashboard showed hard-coded `₹0` sales, `0` orders, `0` customers | Real KPIs + 8 analytics charts |
| The checkout page showed "Payment Successful" without any payment step | UPI QR + reference, or Cash on Delivery, with honest Paid/Pending status |
| Cart was stored in the browser session and lost on logout | Cart is stored in the `cart_items` table |
| Deleting a product broke the history of old orders | Soft delete (`is_active`) |
| Orders had no foreign keys and no status workflow | FKs, indexes, check constraints, and a Placed→Delivered state machine with restock on cancel |
| Admin errors were shown as raw HTML with the Python exception | JSON errors with friendly messages |
| No dataset: only 3 products ("ice cream ₹10", "drink ₹10") | 5-set dataset: 12 categories, 111 products, 60 customers, 420 orders, 1,385 lines |
| No README, requirements or tests | README, docs, `requirements.txt`, `.env.example`, `.gitignore`, 19 tests |

## New features
* Separate **frontend/** (HTML/CSS/JS) and **backend/** (REST API)
* Search, category filter, veg/in-stock filter, 7 sort orders, pagination
* Product detail page with related products
* MRP vs selling price, discount badges, ratings, veg/non-veg marks
* Free-delivery progress bar and "you save" amount
* Order history with a tracking timeline and cancel button
* Admin: product add/edit/delete, restock, order status management, customer list
* Dataset Explorer page with explanations, stats, charts, search and CSV downloads
* About page explaining the architecture
* Mobile-friendly layout

## Moving your old data (optional)
v2 uses a new schema, so the old `database/mymart.db` isn't loaded. If you want to keep an old product, add it from **Admin → Products → + Add product**, or add a row to `data/products.csv` and run `python manage.py reset-db`.
