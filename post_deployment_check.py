import argparse
import requests
import time


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    args = ap.parse_args()
    base = args.url.rstrip("/")
    lines = []
    ok = True
    try:
        r = requests.get(f"{base}/health", timeout=10)
        lines.append(f"- Health endpoint: {'PASS' if r.ok else 'FAIL'}")
        ok = ok and r.ok
    except Exception:
        lines.append("- Health endpoint: FAIL")
        ok = False
    try:
        t0 = time.perf_counter()
        r = requests.get(f"{base}/info", timeout=10)
        t1 = time.perf_counter()
        lt = (t1 - t0) * 1000.0
        lines.append(f"- Info endpoint: {'PASS' if r.ok else 'FAIL'} ({lt:.1f}ms)")
        ok = ok and r.ok
    except Exception:
        lines.append("- Info endpoint: FAIL")
        ok = False
    lines.append(f"- Overall: {'PASS' if ok else 'FAIL'}")
    with open("POST_DEPLOYMENT_REPORT.md", "w", encoding="utf-8") as f:
        f.write("# Post Deployment Report\n\n")
        f.write("\n".join(lines) + "\n")
    print("OK")


if __name__ == "__main__":
    main()
