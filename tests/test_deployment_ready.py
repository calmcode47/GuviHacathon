import os
import time
import base64
from pathlib import Path
import requests
import pytest

if os.getenv("RUN_URL_TESTS") != "1":
    pytest.skip("Skipping remote deployment tests in local environment", allow_module_level=True)

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
API_KEY = os.getenv("API_KEY", "sk_test_key")

def _load_sample_base64() -> str:
    root = Path(__file__).resolve().parents[1]
    sample_path = root / "data" / "human" / "english" / "english_proto_000.mp3"
    with open(sample_path, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")

def _assert_response_structure(j: dict):
    assert j.get("status") == "success"
    assert j.get("classification") in ("AI_GENERATED", "HUMAN", "BORDERLINE")
    assert isinstance(j.get("confidenceScore"), (int, float))
    assert isinstance(j.get("explanation"), str)
    assert isinstance(j.get("audioQuality"), dict)

def test_health_endpoint():
    r = requests.get(f"{BASE_URL}/health", timeout=10)
    assert r.status_code == 200
    j = r.json()
    assert j.get("status") == "ok"
    assert "model_loaded" in j

def test_openapi_info():
    r = requests.get(f"{BASE_URL}/openapi.json", timeout=10)
    assert r.status_code == 200
    j = r.json()
    assert j.get("openapi") is not None
    assert "paths" in j
    assert "/api/voice-detection" in j["paths"]
    assert "/health" in j["paths"]

def test_dual_auth_and_url_input():
    url = f"{BASE_URL}/api/voice-detection"
    headers_bearer = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    payload = {"language": "English", "audioFormat": "mp3", "audioUrl": "https://file-examples.com/wp-content/uploads/2017/11/file_example_MP3_700KB.mp3"}
    t0 = time.time()
    r = requests.post(url, headers=headers_bearer, json=payload, timeout=60)
    dt = time.time() - t0
    assert r.status_code == 200
    _assert_response_structure(r.json())
    assert dt < 5.0
    headers_api = {"x-api-key": API_KEY, "Content-Type": "application/json"}
    r2 = requests.post(url, headers=headers_api, json=payload, timeout=60)
    assert r2.status_code == 200
    _assert_response_structure(r2.json())

def test_base64_input_still_works():
    url = f"{BASE_URL}/api/voice-detection"
    audio_b64 = _load_sample_base64()
    headers_bearer = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    payload = {"language": "English", "audioFormat": "mp3", "audioBase64": audio_b64}
    r = requests.post(url, headers=headers_bearer, json=payload, timeout=60)
    assert r.status_code == 200
    _assert_response_structure(r.json())

def test_error_handling_and_format():
    url = f"{BASE_URL}/api/voice-detection"
    headers = {"x-api-key": API_KEY, "Content-Type": "application/json"}
    audio_b64 = _load_sample_base64()
    payload_both = {"language": "English", "audioFormat": "mp3", "audioBase64": audio_b64, "audioUrl": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3"}
    r = requests.post(url, headers=headers, json=payload_both, timeout=60)
    assert r.status_code == 400
    j = r.json()
    assert j.get("status") == "error"
    payload_bad_url = {"language": "English", "audioFormat": "mp3", "audioUrl": "not-a-url"}
    r2 = requests.post(url, headers=headers, json=payload_bad_url, timeout=60)
    assert r2.status_code in (400, 500)
    j2 = r2.json()
    assert j2.get("status") == "error"
