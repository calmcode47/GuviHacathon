import shutil
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
SUB = ROOT / "submission"
CODE_FILES = [
    ROOT / "app" / "main.py",
    ROOT / "app" / "utils" / "url_downloader.py",
    ROOT / "app" / "utils" / "audio.py",
    ROOT / "app" / "models" / "schemas.py",
]
DOC_FILES = [
    ROOT / "submission" / "README.md",
    ROOT / "submission" / "API.md",
    ROOT / "submission" / "APPROACH.md",
    ROOT / "ROUND2_CHANGES.md",
    ROOT / "ENDPOINT_TESTER_GUIDE.md",
]
OUT_FILES = [
    ROOT / "validation_checklist.md",
    ROOT / "debugging_guide.md",
]

def copy_files():
    SUB.mkdir(parents=True, exist_ok=True)
    code_dir = SUB / "code"
    code_dir.mkdir(exist_ok=True)
    for f in CODE_FILES:
        shutil.copy2(f, code_dir / f.name)
    for f in DOC_FILES:
        shutil.copy2(f, SUB / f.name if f.parent != SUB else f)
    for f in OUT_FILES:
        shutil.copy2(f, SUB / f.name)

def write_test_results():
    p = subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=str(ROOT), capture_output=True, text=True)
    (SUB / "TEST_RESULTS.txt").write_text(p.stdout + "\n" + p.stderr, encoding="utf-8")

def write_deploy_verification(url: str, api_key: str):
    if not url or not api_key:
        return
    p = subprocess.run([sys.executable, str(ROOT / "post_deploy_verify.py"), "--url", url, "--api-key", api_key], cwd=str(ROOT), capture_output=True, text=True)
    (SUB / "DEPLOY_VERIFY.json").write_text(p.stdout or p.stderr, encoding="utf-8")

def main():
    copy_files()
    write_test_results()
    url = ""
    api_key = ""
    if len(sys.argv) >= 3:
        url = sys.argv[1]
        api_key = sys.argv[2]
    write_deploy_verification(url, api_key)
    print("Submission bundle updated at", str(SUB))

if __name__ == "__main__":
    main()
