"""
Start MyMart on your computer.

    python run.py

Then open http://localhost:5000 in your browser.
On the very first run the database is created and the sample dataset
(data/*.csv) is loaded automatically.
"""

import os

from backend.app import create_app

app = create_app()

if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "1") == "1"
    print(f"\n  MyMart is running ->  http://localhost:{port}\n"
          f"     Admin login: {app.config['ADMIN_EMAIL']} / (see README)\n")
    app.run(host=host, port=port, debug=debug)
