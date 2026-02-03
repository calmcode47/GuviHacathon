import argparse
import base64
import os
import requests

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--file", required=True)
    p.add_argument("--language", required=True, choices=["Tamil", "English", "Hindi", "Malayalam", "Telugu"])
    p.add_argument("--api-key", required=True)
    p.add_argument("--url", default="http://localhost:8000/api/voice-detection")
    args = p.parse_args()
    with open(args.file, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    payload = {
        "language": args.language,
        "audioFormat": "mp3",
        "audioBase64": b64,
    }
    headers = {"x-api-key": args.api_key, "Content-Type": "application/json"}
    r = requests.post(args.url, json=payload, headers=headers, timeout=60)
    print(r.status_code)
    try:
        print(r.json())
    except Exception:
        print(r.text)

if __name__ == "__main__":
    main()
