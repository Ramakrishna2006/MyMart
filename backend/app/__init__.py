"""
MyMart application factory.

    backend/app
    ├── config.py      settings (.env)
    ├── extensions.py  db + login manager
    ├── models/        database tables
    ├── api/           REST endpoints  (/api/...)
    └── seed.py        loads data/*.csv into the database

The frontend (plain HTML/CSS/JS in /frontend) is served by the same Flask
server, so the whole project runs on one address: http://localhost:5000
"""

from flask import Flask, jsonify, request, send_from_directory
from werkzeug.exceptions import HTTPException

from .config import FRONTEND_DIR, INSTANCE_DIR, Config
from .extensions import db, login_manager
from .utils import ApiError

# Pages of the frontend: URL path -> html file
PAGES = {
    "": "index.html",
    "product": "product.html",
    "login": "login.html",
    "register": "register.html",
    "cart": "cart.html",
    "checkout": "checkout.html",
    "orders": "orders.html",
    "admin": "admin.html",
    "dataset": "dataset.html",
    "about": "about.html",
}


def create_app(config_class=Config):
    app = Flask(__name__, static_folder=None)
    app.config.from_object(config_class)
    app.json.sort_keys = False  # keep JSON keys in the order we write them
    INSTANCE_DIR.mkdir(parents=True, exist_ok=True)

    # ---- extensions --------------------------------------------------------
    db.init_app(app)
    login_manager.init_app(app)

    from .models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    @login_manager.unauthorized_handler
    def unauthorized():
        return jsonify({"error": "Please log in first."}), 401

    # ---- API ----------------------------------------------------------------
    from .api import BLUEPRINTS

    for bp in BLUEPRINTS:
        app.register_blueprint(bp)

    @app.get("/api/health")
    def health():
        return {"status": "ok", "app": "MyMart"}

    # ---- errors: JSON for /api, normal pages otherwise ----------------------
    @app.errorhandler(ApiError)
    def handle_api_error(err):
        db.session.rollback()
        return jsonify({"error": err.message}), err.status

    @app.errorhandler(HTTPException)
    def handle_http(err):
        if request.path.startswith("/api/"):
            return jsonify({"error": err.description}), err.code
        if err.code == 404:
            return send_from_directory(FRONTEND_DIR, "404.html"), 404
        return err

    @app.errorhandler(Exception)
    def handle_unexpected(err):  # pragma: no cover - safety net
        db.session.rollback()
        app.logger.exception(err)
        return jsonify({"error": "Something went wrong on the server."}), 500

    # ---- frontend -------------------------------------------------------------
    @app.get("/")
    @app.get("/<page>")
    def page(page=""):
        filename = PAGES.get(page)
        if filename is None:
            return send_from_directory(FRONTEND_DIR, "404.html"), 404
        return send_from_directory(FRONTEND_DIR, filename)

    @app.get("/static/<path:filename>")
    def static_files(filename):
        return send_from_directory(FRONTEND_DIR, filename)

    # ---- database -------------------------------------------------------------
    with app.app_context():
        db.create_all()
        if app.config.get("AUTO_SEED"):
            from .seed import ensure_admin, is_empty, seed_database

            if is_empty():
                quiet = app.config.get("TESTING", False)
                if not quiet:
                    print(" * First run: loading the sample dataset from data/*.csv ...")
                seed_database(verbose=not quiet)
            ensure_admin()

    return app
