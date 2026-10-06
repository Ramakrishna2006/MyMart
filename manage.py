"""
Database management commands.

    python manage.py reset-db        drop all tables and reload data/*.csv
    python manage.py seed            load data/*.csv into an EMPTY database (only needed when AUTO_SEED=false)
    python manage.py create-admin    create/update the admin from .env (ADMIN_EMAIL / ADMIN_PASSWORD)
    python manage.py export          write the live tables to exports/*.csv
    python manage.py stats           print row counts for every table
"""

import argparse

from backend.app import create_app
from backend.app.extensions import db


def main():
    parser = argparse.ArgumentParser(description="MyMart database tools")
    parser.add_argument("command", choices=["reset-db", "seed", "create-admin", "export", "stats"])
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        from backend.app.models import Category, Order, OrderItem, Product, User
        from backend.app.seed import ensure_admin, is_empty, reset_database, seed_database

        if args.command == "reset-db":
            answer = input("This deletes ALL data (including new orders/users). Continue? [y/N] ")
            if answer.lower() == "y":
                reset_database()
                print("Database reset complete.")
        elif args.command == "seed":
            if not is_empty():
                print("Database already has data. Use 'reset-db' to start fresh.")
            else:
                seed_database()
        elif args.command == "create-admin":
            admin = ensure_admin()
            admin.role = "admin"
            admin.set_password(app.config["ADMIN_PASSWORD"])
            db.session.commit()
            print(f"Admin ready: {admin.email}")
        elif args.command == "export":
            import csv
            from pathlib import Path

            from backend.app.api.dataset import DATASETS, _row

            out = Path("exports")
            out.mkdir(exist_ok=True)
            with app.test_request_context():
                from backend.app.api.dataset import _query

                for key, meta in DATASETS.items():
                    cols = [c[0] for c in meta["columns"]]
                    path = out / f"{key}.csv"
                    with path.open("w", newline="", encoding="utf-8") as f:
                        w = csv.DictWriter(f, fieldnames=cols)
                        w.writeheader()
                        for obj in _query(key).all():
                            w.writerow(_row(key, obj))
                    print(f"  wrote {path}")
        elif args.command == "stats":
            for model in (Category, Product, User, Order, OrderItem):
                print(f"  {model.__tablename__:<12} {model.query.count():>6} rows")


if __name__ == "__main__":
    main()
