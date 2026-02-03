import os
import json
import argparse
import subprocess


def check_model_json(path: str) -> dict:
    ok = os.path.isfile(path)
    details = {"exists": ok}
    if not ok:
        return {"pass": False, "details": details}
    try:
        with open(path, "r", encoding="utf-8") as f:
            obj = json.load(f)
        keys = ["mean", "std", "weights", "bias", "calib_a", "calib_c"]
        missing = [k for k in keys if k not in obj]
        details["missing_keys"] = missing
        return {"pass": len(missing) == 0, "details": details}
    except Exception as e:
        return {"pass": False, "details": {"error": str(e)}}


def run_py(cmd: list) -> tuple:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        return proc.returncode == 0, proc.stdout.strip(), proc.stderr.strip()
    except Exception as e:
        return False, "", str(e)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="app/model/model.json")
    ap.add_argument("--output", default="DEPLOYMENT_READY.md")
    args = ap.parse_args()
    lines = []
    # Model JSON
    mres = check_model_json(args.model)
    lines.append(f"- Model JSON present and valid: {'PASS' if mres['pass'] else 'FAIL'}")
    # verify_api
    ok, out, err = run_py(["python", "verify_api.py", "--model", args.model])
    lines.append(f"- API verification script: {'PASS' if ok else 'FAIL'}")
    # Accuracy
    acc_ok = False
    try:
        with open("results/training_report.json", "r", encoding="utf-8") as f:
            rep = json.load(f)
        acc_ok = rep.get("accuracy_test", rep.get("accuracy", 0)) >= 0.7
        ece_ok = rep.get("ece_test", 1.0) <= 0.15
    except Exception:
        pass
    lines.append(f"- Accuracy ≥ 70%: {'PASS' if acc_ok else 'FAIL'}")
    lines.append(f"- ECE ≤ 0.15: {'PASS' if (ece_ok if 'ece_ok' in locals() else False) else 'FAIL'}")
    # Latency
    lat_ok = False
    try:
        with open("results/benchmark_results.json", "r", encoding="utf-8") as f:
            bench = json.load(f)
        lat_ok = bench.get("p95_latency_ms", 9999) < 5000
    except Exception:
        pass
    lines.append(f"- Latency p95 < 5s: {'PASS' if lat_ok else 'FAIL'}")
    # API import
    try:
        import importlib
        mod = importlib.import_module("app.main")
        _ = getattr(mod, "app", None)
        api_ok = _ is not None
    except Exception:
        api_ok = False
    lines.append(f"- API imports without errors: {'PASS' if api_ok else 'FAIL'}")
    # Save
    with open(args.output, "w", encoding="utf-8") as f:
        f.write("# Deployment Readiness\n\n")
        f.write("\n".join(lines) + "\n")
    print("OK")


if __name__ == "__main__":
    main()
