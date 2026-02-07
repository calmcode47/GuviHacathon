import argparse
import base64
import json
import time
import requests
from pathlib import Path

def get_health(url: str) -> dict:
    r = requests.get(f"{url}/health", timeout=10)
    return {"status_code": r.status_code, "json": (r.json() if r.headers.get("Content-Type","").startswith("application/json") else r.text)}

def post_voice(url: str, headers: dict, payload: dict, timeout: int = 60) -> dict:
    t0 = time.time()
    r = requests.post(f"{url}/api/voice-detection", headers=headers, json=payload, timeout=timeout)
    dt = (time.time() - t0) * 1000.0
    out = {"status_code": r.status_code, "latency_ms": round(dt, 2)}
    try:
        out["json"] = r.json()
    except Exception:
        out["text"] = r.text
    return out

def load_local_b64() -> str:
    p = Path(__file__).resolve().parents[0] / "data" / "human" / "english" / "english_proto_000.mp3"
    with open(p, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True, help="Base URL, e.g., https://guvihacathon-production.up.railway.app")
    ap.add_argument("--api-key", required=True)
    args = ap.parse_args()
    base = args.url.rstrip("/")
    headers_bearer = {"Authorization": f"Bearer {args.api_key}", "Content-Type": "application/json"}
    headers_api = {"x-api-key": args.api_key, "Content-Type": "application/json"}
    health = get_health(base)
    url_payload = {"language":"English","audioFormat":"mp3","audioUrl":"https://file-examples.com/wp-content/uploads/2017/11/file_example_MP3_700KB.mp3"}
    b64_payload = {"language":"English","audioFormat":"mp3","audioBase64": load_local_b64()}
    res_url_bearer = post_voice(base, headers_bearer, url_payload)
    res_url_api = post_voice(base, headers_api, url_payload)
    res_b64_bearer = post_voice(base, headers_bearer, b64_payload)
    res_b64_api = post_voice(base, headers_api, b64_payload)
    summary = {
        "health": health,
        "url_bearer": res_url_bearer,
        "url_api": res_url_api,
        "b64_bearer": res_b64_bearer,
        "b64_api": res_b64_api,
    }
    print(json.dumps(summary, indent=2))

if __name__ == "__main__":
    main()
