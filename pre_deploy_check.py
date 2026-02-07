import os
import sys
import json
import subprocess
from pathlib import Path
import py_compile

ROOT = Path(__file__).resolve().parent

FILES_TO_CHECK = [
    ROOT / "app" / "main.py",
    ROOT / "app" / "models" / "schemas.py",
    ROOT / "app" / "utils" / "audio.py",
    ROOT / "app" / "utils" / "url_downloader.py",
]

def check_requirements() -> dict:
    req = ROOT / "requirements_production.txt"
    result = {"exists": req.exists(), "packages": []}
    if not req.exists():
        return result
    content = req.read_text(encoding="utf-8").splitlines()
    for line in content:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        result["packages"].append(line)
    return result

def check_syntax(files) -> dict:
    out = {"ok": True, "errors": []}
    for f in files:
        try:
            py_compile.compile(str(f), doraise=True)
        except Exception as e:
            out["ok"] = False
            out["errors"].append({"file": str(f), "error": str(e)})
    return out

def run_pytest() -> dict:
    try:
        r = subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=str(ROOT), capture_output=True, text=True)
        return {"exit_code": r.returncode, "stdout": r.stdout, "stderr": r.stderr}
    except Exception as e:
        return {"exit_code": -1, "error": str(e)}

def check_dockerfile() -> dict:
    df = ROOT / "Dockerfile"
    return {"exists": df.exists(), "size": df.stat().st_size if df.exists() else 0}

def document_env() -> dict:
    envs = {
        "API_KEY": os.getenv("API_KEY", "<not set>"),
        "MODEL_PATH": os.getenv("MODEL_PATH", "<optional>"),
        "URL_FETCH_MODE": os.getenv("URL_FETCH_MODE", "online/offline"),
    }
    return envs

def main():
    report = {
        "requirements": check_requirements(),
        "syntax": check_syntax(FILES_TO_CHECK),
        "pytest": run_pytest(),
        "dockerfile": check_dockerfile(),
        "env": document_env(),
    }
    print(json.dumps(report, indent=2))
    if report["syntax"]["ok"] is False or report["pytest"]["exit_code"] != 0 or report["dockerfile"]["exists"] is False:
        sys.exit(1)

if __name__ == "__main__":
    main()
