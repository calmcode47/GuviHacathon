@echo off
setlocal enabledelayedexpansion
python -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
echo Activate: .venv\Scripts\activate.bat
