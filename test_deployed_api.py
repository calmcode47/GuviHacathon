import argparse
import time
import base64
import requests


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--english-sample", default="")
    ap.add_argument("--api-key", default="sk_test_123456789")
    args = ap.parse_args()
    base = args.url.rstrip("/")
    rep = {"health": False, "info": False, "english": False, "non_english": False, "auth_401": False, "bad_request_400": False, "latency_ms": 0.0}
    t0 = time.perf_counter()
    r = requests.get(f"{base}/health", timeout=10)
    rep["health"] = r.ok
    r = requests.get(f"{base}/info", timeout=10)
    rep["info"] = r.ok
    b64 = ""
    if args.english_sample:
        with open(args.english_sample, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
    payload = {"language": "English", "audioFormat": "mp3", "audioBase64": b64}
    headers = {"Content-Type": "application/json", "x-api-key": args.api_key}
    r = requests.post(f"{base}/api/voice-detection", json=payload, headers=headers, timeout=20)
    rep["english"] = r.ok
    payload["language"] = "Tamil"
    r = requests.post(f"{base}/api/voice-detection", json=payload, headers=headers, timeout=20)
    rep["non_english"] = r.ok
    r = requests.post(f"{base}/api/voice-detection", json=payload, headers={"Content-Type": "application/json", "x-api-key": "bad"}, timeout=10)
    rep["auth_401"] = (r.status_code == 401)
    r = requests.post(f"{base}/api/voice-detection", json={"language": "English"}, headers=headers, timeout=10)
    rep["bad_request_400"] = (r.status_code == 400)
    t1 = time.perf_counter()
    rep["latency_ms"] = float((t1 - t0) * 1000.0)
    print(rep)


if __name__ == "__main__":
    main()
