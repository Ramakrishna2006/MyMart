#!/usr/bin/env bash
# One-click start for macOS / Linux: creates a venv, installs libraries, runs the app.
set -e
cd "$(dirname "$0")"
[ -d venv ] || python3 -m venv venv
source venv/bin/activate
pip install -q -r requirements.txt
python run.py
