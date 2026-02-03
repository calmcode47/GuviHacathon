$ErrorActionPreference = "Stop"
python -m venv .venv
& ".venv\Scripts\python.exe" -m pip install --upgrade pip setuptools wheel
& ".venv\Scripts\pip.exe" install -r requirements.txt
Write-Output "Activate: .venv\Scripts\Activate.ps1"
