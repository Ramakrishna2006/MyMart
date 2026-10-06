"""REST API blueprints. Every endpoint lives under /api and returns JSON."""

from . import admin, auth, cart, dataset, orders, products

BLUEPRINTS = [auth.bp, products.bp, cart.bp, orders.bp, admin.bp, dataset.bp]
