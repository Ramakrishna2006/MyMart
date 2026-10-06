@echo off
REM One-click start for Windows: creates a virtual environment, installs
REM the libraries (first time only) and starts MyMart on http://localhost:5000
cd /d "%~dp0"
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)
call venv\Scripts\activate.bat
pip install -q -r requirements.txt
python run.py
pause
