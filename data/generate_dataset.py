"""
MyMart dataset generator
========================

Creates the five CSV files that make up the MyMart sample dataset:

    data/categories.csv   - Set 1: product categories
    data/products.csv     - Set 2: product catalogue (inventory + pricing)
    data/customers.csv    - Set 3: registered customers (synthetic people)
    data/orders.csv       - Set 4: order headers (one row per order)
    data/order_items.csv  - Set 5: order lines (one row per product in an order)

The data is SYNTHETIC: every name, phone number, brand and e-mail is invented.
A fixed random seed makes the output identical on every run, so anyone who
clones the repository can regenerate exactly the same files:

    python data/generate_dataset.py

Only the Python standard library is used.
"""

import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

SEED = 42
DATA_DIR = Path(__file__).resolve().parent

START_DATE = datetime(2026, 4, 1, 8, 0, 0)
END_DATE = datetime(2026, 9, 30, 22, 0, 0)
NUM_CUSTOMERS = 60
NUM_ORDERS = 420
FREE_DELIVERY_ABOVE = 499
DELIVERY_FEE = 40

rng = random.Random(SEED)

# --------------------------------------------------------------------------
# SET 1 - CATEGORIES
# --------------------------------------------------------------------------
CATEGORIES = [
    # id, name, slug, emoji, description
    (1, "Fruits", "fruits", "🍎", "Fresh seasonal and imported fruits"),
    (2, "Vegetables", "vegetables", "🥦", "Farm-fresh everyday vegetables and greens"),
    (3, "Dairy & Eggs", "dairy-eggs", "🥛", "Milk, curd, paneer, butter, cheese and eggs"),
    (4, "Rice, Atta & Grains", "rice-atta-grains", "🌾", "Rice, wheat flour, millets and grains"),
    (5, "Pulses & Dals", "pulses-dals", "🫘", "Toor, moong, chana, urad and other lentils"),
    (6, "Oils & Ghee", "oils-ghee", "🫒", "Cooking oils and ghee"),
    (7, "Spices & Masalas", "spices-masalas", "🌶️", "Whole spices, powders and masala blends"),
    (8, "Snacks & Biscuits", "snacks-biscuits", "🍪", "Namkeen, chips, biscuits and cookies"),
    (9, "Beverages", "beverages", "🥤", "Tea, coffee, juices and soft drinks"),
    (10, "Bakery", "bakery", "🍞", "Breads, buns, rusks and cakes"),
    (11, "Personal Care", "personal-care", "🧴", "Soaps, shampoos, toothpaste and skin care"),
    (12, "Household", "household", "🧽", "Detergents, cleaners and kitchen essentials"),
]

# --------------------------------------------------------------------------
# SET 2 - PRODUCTS  (name, unit, mrp, veg?)  brands are fictional
# --------------------------------------------------------------------------
BRANDS = {
    1: ["FreshFarm", "Orchard Valley"],
    2: ["FreshFarm", "GreenLeaf"],
    3: ["DairyDay", "Gokul Fresh"],
    4: ["Annapurna Mills", "MyMart Select"],
    5: ["MyMart Select", "Kisan Gold"],
    6: ["GoldDrop", "Pure Harvest"],
    7: ["Masala Mantra", "SpiceRoute"],
    8: ["Crunchy Bites", "Tea Time"],
    9: ["Chai Point Co.", "Fizzup", "Juicy Farms"],
    10: ["Oven Fresh", "Daily Bake"],
    11: ["Herbal Glow", "CleanCare"],
    12: ["Sparkle", "HomeShine"],
}

PRODUCTS = {
    1: [("Banana Robusta", "1 dozen", 60, 1), ("Apple Shimla", "1 kg", 180, 1),
        ("Pomegranate", "1 kg", 220, 1), ("Papaya", "1 pc (~1 kg)", 55, 1),
        ("Alphonso Mango", "1 kg", 450, 1), ("Watermelon", "1 pc (~3 kg)", 90, 1),
        ("Orange Nagpur", "1 kg", 120, 1), ("Green Grapes", "500 g", 80, 1),
        ("Guava", "1 kg", 70, 1), ("Kiwi", "3 pcs", 99, 1)],
    2: [("Onion", "1 kg", 40, 1), ("Tomato", "1 kg", 35, 1), ("Potato", "1 kg", 30, 1),
        ("Green Chilli", "100 g", 12, 1), ("Coriander Leaves", "1 bunch", 15, 1),
        ("Carrot", "500 g", 30, 1), ("Cauliflower", "1 pc", 40, 1),
        ("Spinach (Palak)", "1 bunch", 20, 1), ("Ladies Finger (Bhindi)", "500 g", 35, 1),
        ("Ginger", "250 g", 30, 1)],
    3: [("Toned Milk", "1 L", 56, 1), ("Full Cream Milk", "1 L", 68, 1),
        ("Fresh Curd", "500 g", 40, 1), ("Malai Paneer", "200 g", 90, 1),
        ("Salted Butter", "100 g", 58, 1), ("Cheese Slices", "200 g", 140, 1),
        ("Farm Eggs", "6 pcs", 54, 0), ("Brown Eggs", "6 pcs", 72, 0),
        ("Buttermilk", "500 ml", 25, 1), ("Fresh Cream", "200 ml", 65, 1)],
    4: [("Basmati Rice", "1 kg", 140, 1), ("Sona Masoori Rice", "5 kg", 380, 1),
        ("Whole Wheat Atta", "5 kg", 285, 1), ("Maida", "1 kg", 52, 1),
        ("Rava (Sooji)", "1 kg", 60, 1), ("Poha", "500 g", 45, 1),
        ("Ragi Flour", "1 kg", 75, 1), ("Brown Rice", "1 kg", 160, 1),
        ("Besan", "500 g", 70, 1), ("Idli Rice", "5 kg", 320, 1)],
    5: [("Toor Dal", "1 kg", 165, 1), ("Moong Dal", "1 kg", 140, 1),
        ("Chana Dal", "1 kg", 110, 1), ("Urad Dal", "1 kg", 150, 1),
        ("Masoor Dal", "1 kg", 115, 1), ("Rajma", "500 g", 95, 1),
        ("Kabuli Chana", "500 g", 90, 1), ("Green Moong Whole", "500 g", 75, 1)],
    6: [("Sunflower Oil", "1 L", 165, 1), ("Groundnut Oil", "1 L", 210, 1),
        ("Mustard Oil", "1 L", 180, 1), ("Cow Ghee", "500 ml", 340, 1),
        ("Coconut Oil", "500 ml", 140, 1), ("Rice Bran Oil", "1 L", 175, 1),
        ("Olive Oil (Pomace)", "500 ml", 450, 1)],
    7: [("Turmeric Powder", "200 g", 52, 1), ("Red Chilli Powder", "200 g", 75, 1),
        ("Coriander Powder", "200 g", 48, 1), ("Garam Masala", "100 g", 70, 1),
        ("Cumin Seeds (Jeera)", "100 g", 65, 1), ("Mustard Seeds", "100 g", 25, 1),
        ("Sambar Powder", "100 g", 55, 1), ("Chicken Masala", "100 g", 68, 0),
        ("Black Pepper Whole", "100 g", 110, 1), ("Iodised Salt", "1 kg", 28, 1)],
    8: [("Aloo Bhujia", "400 g", 110, 1), ("Salted Potato Chips", "90 g", 30, 1),
        ("Marie Biscuits", "250 g", 40, 1), ("Chocolate Cream Biscuits", "150 g", 35, 1),
        ("Roasted Peanuts", "200 g", 60, 1), ("Khakhra Methi", "200 g", 75, 1),
        ("Instant Noodles", "4-pack", 56, 1), ("Butter Cookies", "200 g", 95, 1),
        ("Mixture Namkeen", "400 g", 100, 1), ("Dark Chocolate Bar", "100 g", 120, 1)],
    9: [("Assam Tea", "500 g", 260, 1), ("Filter Coffee Powder", "500 g", 320, 1),
        ("Instant Coffee", "100 g", 290, 1), ("Green Tea Bags", "25 bags", 165, 1),
        ("Orange Juice", "1 L", 120, 1), ("Mango Drink", "1.2 L", 75, 1),
        ("Cola", "750 ml", 40, 1), ("Packaged Drinking Water", "1 L", 20, 1),
        ("Lemon Soda", "600 ml", 30, 1), ("Tender Coconut Water", "200 ml", 45, 1)],
    10: [("White Bread", "400 g", 40, 1), ("Brown Bread", "400 g", 50, 1),
         ("Pav Buns", "6 pcs", 30, 1), ("Milk Rusk", "300 g", 55, 1),
         ("Multigrain Bread", "400 g", 65, 1), ("Plum Cake", "300 g", 150, 0),
         ("Burger Buns", "4 pcs", 40, 1), ("Garlic Bread", "200 g", 70, 1)],
    11: [("Neem Soap", "4 x 100 g", 140, 1), ("Herbal Shampoo", "340 ml", 210, 1),
         ("Toothpaste", "150 g", 95, 1), ("Toothbrush Soft", "pack of 3", 85, 1),
         ("Coconut Hair Oil", "300 ml", 135, 1), ("Aloe Vera Gel", "150 g", 160, 1),
         ("Hand Wash Refill", "750 ml", 99, 1), ("Body Lotion", "250 ml", 245, 1),
         ("Face Wash", "100 g", 175, 1)],
    12: [("Detergent Powder", "1 kg", 125, 1), ("Dishwash Liquid", "750 ml", 155, 1),
         ("Floor Cleaner", "1 L", 189, 1), ("Toilet Cleaner", "500 ml", 98, 1),
         ("Scrub Pads", "pack of 3", 45, 1), ("Garbage Bags", "30 pcs", 110, 1),
         ("Aluminium Foil", "9 m", 95, 1), ("Matchbox", "pack of 10", 20, 1),
         ("Liquid Detergent", "1 L", 210, 1)],
}

DESCRIPTIONS = {
    1: "Hand-picked {name}, sorted and washed. Best stored in a cool place.",
    2: "Fresh {name} sourced daily from local farms.",
    3: "{name} from {brand} - chilled and delivered fresh.",
    4: "Premium quality {name}, cleaned and packed hygienically.",
    5: "Unpolished {name}, rich in protein. Cleaned and sorted.",
    6: "{brand} {name} for healthy everyday cooking.",
    7: "Aromatic {name} - no added colour or preservatives.",
    8: "Crunchy and tasty {name}, perfect for tea time.",
    9: "Refreshing {name} from {brand}.",
    10: "Freshly baked {name} from {brand}.",
    11: "{brand} {name} for daily personal care.",
    12: "{brand} {name} for a sparkling clean home.",
}

# --------------------------------------------------------------------------
# SET 3 - CUSTOMERS (synthetic names / cities)
# --------------------------------------------------------------------------
FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditya", "Arjun", "Sai", "Rohan", "Karthik", "Rahul", "Vikram", "Nikhil",
    "Ananya", "Diya", "Priya", "Sneha", "Kavya", "Meera", "Isha", "Pooja", "Lakshmi", "Divya",
    "Harsha", "Manoj", "Suresh", "Ramesh", "Deepak", "Neha", "Swathi", "Keerthi", "Bhavana", "Anjali",
]
LAST_NAMES = [
    "Sharma", "Reddy", "Iyer", "Nair", "Patel", "Gupta", "Rao", "Kumar", "Singh", "Menon",
    "Das", "Joshi", "Pillai", "Verma", "Naidu", "Mehta", "Chowdary", "Krishnan", "Bose", "Shetty",
]
CITIES = [
    # city, state, weight
    ("Hyderabad", "Telangana", 18), ("Bengaluru", "Karnataka", 16), ("Chennai", "Tamil Nadu", 14),
    ("Mumbai", "Maharashtra", 12), ("Pune", "Maharashtra", 8), ("Delhi", "Delhi", 10),
    ("Kolkata", "West Bengal", 6), ("Visakhapatnam", "Andhra Pradesh", 6),
    ("Kochi", "Kerala", 5), ("Ahmedabad", "Gujarat", 5),
]


def money(x):
    return f"{x:.2f}"


def random_datetime(start, end):
    seconds = int((end - start).total_seconds())
    return start + timedelta(seconds=rng.randint(0, seconds))


def build_products():
    rows = []
    pid = 1
    for cat_id, items in PRODUCTS.items():
        for name, unit, mrp, veg in items:
            brand = rng.choice(BRANDS[cat_id])
            discount = rng.choice([0, 0, 5, 5, 8, 10, 10, 12, 15, 20])
            price = round(mrp * (100 - discount) / 100, 2)
            # a few products deliberately low / out of stock so the admin
            # "low stock" alert has something to show
            stock = rng.choice([0, 3, 7]) if rng.random() < 0.08 else rng.randint(15, 200)
            rows.append({
                "id": pid,
                "sku": f"MM-{cat_id:02d}-{pid:04d}",
                "name": name,
                "brand": brand,
                "category_id": cat_id,
                "unit": unit,
                "mrp": money(mrp),
                "price": money(price),
                "discount_pct": discount,
                "stock": stock,
                "rating": f"{rng.uniform(3.4, 4.9):.1f}",
                "rating_count": rng.randint(12, 2400),
                "is_veg": veg,
                "description": DESCRIPTIONS[cat_id].format(name=name, brand=brand),
                "created_at": random_datetime(datetime(2026, 1, 1), datetime(2026, 3, 31)).strftime("%Y-%m-%d %H:%M:%S"),
            })
            pid += 1
    return rows


def build_customers():
    rows = []
    used = set()
    city_pool = [c for c in CITIES for _ in range(c[2])]
    for cid in range(1, NUM_CUSTOMERS + 1):
        while True:
            first, last = rng.choice(FIRST_NAMES), rng.choice(LAST_NAMES)
            if (first, last) not in used:
                used.add((first, last))
                break
        city, state, _ = rng.choice(city_pool)
        rows.append({
            "id": cid,
            "name": f"{first} {last}",
            "email": f"{first.lower()}.{last.lower()}{cid}@example.com",
            "phone": f"9{rng.randint(100000000, 999999999)}",
            "city": city,
            "state": state,
            "joined_at": random_datetime(datetime(2026, 1, 1), datetime(2026, 6, 30)).strftime("%Y-%m-%d %H:%M:%S"),
        })
    return rows


def build_orders(customers, products):
    # popularity weights: cheap everyday items are bought more often
    weights = []
    for p in products:
        w = 1.0
        if p["category_id"] in (2, 3, 1, 10):
            w *= 3.0
        if float(p["price"]) < 80:
            w *= 1.8
        w *= rng.uniform(0.5, 1.5)
        weights.append(w)

    # some customers shop much more than others
    cust_weights = [rng.choice([1, 1, 1, 2, 3, 6]) for _ in customers]

    orders, items = [], []
    item_id = 1
    raw = []
    for _ in range(NUM_ORDERS):
        cust = rng.choices(customers, weights=cust_weights, k=1)[0]
        joined = datetime.strptime(cust["joined_at"], "%Y-%m-%d %H:%M:%S")
        start = max(START_DATE, joined)
        # weekends and evenings are busier: bias the timestamp a little
        created = random_datetime(start, END_DATE)
        if rng.random() < 0.35:
            created = created.replace(hour=rng.choice([18, 19, 20, 21]))
        raw.append((created, cust))
    raw.sort(key=lambda r: r[0])

    for oid, (created, cust) in enumerate(raw, start=1):
        n_lines = rng.choices([1, 2, 3, 4, 5, 6], weights=[10, 20, 25, 20, 15, 10])[0]
        chosen = set()
        while len(chosen) < n_lines:
            chosen.add(rng.choices(range(len(products)), weights=weights)[0])

        subtotal = 0.0
        count = 0
        for idx in sorted(chosen):
            p = products[idx]
            qty = rng.choices([1, 2, 3, 4], weights=[60, 25, 10, 5])[0]
            unit_price = float(p["price"])
            line = round(unit_price * qty, 2)
            subtotal += line
            count += qty
            items.append({
                "id": item_id,
                "order_id": oid,
                "product_id": p["id"],
                "product_name": p["name"],
                "unit_price": money(unit_price),
                "quantity": qty,
                "line_total": money(line),
            })
            item_id += 1

        delivery = 0 if subtotal >= FREE_DELIVERY_ABOVE else DELIVERY_FEE
        method = rng.choices(["UPI", "COD"], weights=[65, 35])[0]

        days_old = (END_DATE - created).days
        if days_old <= 1:
            status = rng.choice(["Placed", "Packed"])
        elif days_old <= 3:
            status = rng.choice(["Packed", "Shipped", "Delivered"])
        else:
            status = "Cancelled" if rng.random() < 0.06 else "Delivered"

        if status == "Cancelled":
            pay_status = "Refunded" if method == "UPI" else "Cancelled"
        elif method == "UPI":
            pay_status = "Paid"
        else:
            pay_status = "Paid" if status == "Delivered" else "Pending"

        orders.append({
            "id": oid,
            "order_number": f"MM{created:%y%m}-{oid:05d}",
            "user_id": cust["id"],
            "created_at": created.strftime("%Y-%m-%d %H:%M:%S"),
            "status": status,
            "payment_method": method,
            "payment_status": pay_status,
            "items_count": count,
            "subtotal": money(subtotal),
            "delivery_fee": money(delivery),
            "total": money(subtotal + delivery),
            "delivery_city": cust["city"],
        })
    return orders, items


def write_csv(filename, rows):
    path = DATA_DIR / filename
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"  wrote {filename:<18} {len(rows):>5} rows")


def main():
    categories = [
        {"id": c[0], "name": c[1], "slug": c[2], "emoji": c[3], "description": c[4]}
        for c in CATEGORIES
    ]
    products = build_products()
    customers = build_customers()
    orders, order_items = build_orders(customers, products)

    print("Generating MyMart dataset (seed=%d)" % SEED)
    write_csv("categories.csv", categories)
    write_csv("products.csv", products)
    write_csv("customers.csv", customers)
    write_csv("orders.csv", orders)
    write_csv("order_items.csv", order_items)
    print("Done.")


if __name__ == "__main__":
    main()
