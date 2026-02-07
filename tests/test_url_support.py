import os
import base64
from pathlib import Path
import requests
import pytest

if os.getenv("RUN_URL_TESTS") != "1":
    pytest.skip("Skipping URL tests in local environment", allow_module_level=True)

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
API_KEY = os.getenv("API_KEY", "sk_test_key")

TEST_URLS = {
    "small_generic": "https://file-examples.com/wp-content/uploads/2017/11/file_example_MP3_700KB.mp3",
    "medium_generic": "https://www.learningcontainer.com/wp-content/uploads/2020/02/Kalimba.mp3",
    "large_generic": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
    "tiny_generic": "https://interactive-examples.mdn.mozilla.net/media/cc0-audio/t-rex-roar.mp3",
}

def _load_sample_base64() -> str:
    root = Path(__file__).resolve().parents[1]
    sample_path = root / "data" / "human" / "english" / "english_proto_000.mp3"
    with open(sample_path, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")

def _assert_success(resp_json: dict):
    assert resp_json.get("status") == "success"
    assert resp_json.get("classification") in ("AI_GENERATED", "HUMAN", "BORDERLINE")
    assert isinstance(resp_json.get("confidenceScore"), (int, float))
    assert isinstance(resp_json.get("explanation"), str)
    aq = resp_json.get("audioQuality")
    assert isinstance(aq, dict)
    for k in ["formatValid", "sampleRateSuspect", "shortAudio", "durationSeconds", "sampleRate", "channels"]:
        assert k in aq

def test_url_with_bearer_auth():
    url = f"{BASE_URL}/api/voice-detection"
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    payload = {"language": "English", "audioFormat": "mp3", "audioUrl": TEST_URLS["small_generic"]}
    r = requests.post(url, headers=headers, json=payload, timeout=60)
    assert r.status_code == 200
    _assert_success(r.json())

def test_url_with_api_key_auth():
    url = f"{BASE_URL}/api/voice-detection"
    headers = {"x-api-key": API_KEY, "Content-Type": "application/json"}
    payload = {"language": "English", "audioFormat": "mp3", "audioUrl": TEST_URLS["medium_generic"]}
    r = requests.post(url, headers=headers, json=payload, timeout=60)
    assert r.status_code == 200
    _assert_success(r.json())

def test_base64_with_bearer_auth():
    url = f"{BASE_URL}/api/voice-detection"
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    audio_b64 = _load_sample_base64()
    payload = {"language": "English", "audioFormat": "mp3", "audioBase64": audio_b64}
    r = requests.post(url, headers=headers, json=payload, timeout=60)
    assert r.status_code == 200
    _assert_success(r.json())

def test_base64_with_api_key_auth():
    url = f"{BASE_URL}/api/voice-detection"
    headers = {"x-api-key": API_KEY, "Content-Type": "application/json"}
    audio_b64 = _load_sample_base64()
    payload = {"language": "English", "audioFormat": "mp3", "audioBase64": audio_b64}
    r = requests.post(url, headers=headers, json=payload, timeout=60)
    assert r.status_code == 200
    _assert_success(r.json())

def test_both_inputs_error():
    url = f"{BASE_URL}/api/voice-detection"
    headers = {"x-api-key": API_KEY, "Content-Type": "application/json"}
    audio_b64 = _load_sample_base64()
    payload = {"language": "English", "audioFormat": "mp3", "audioBase64": audio_b64, "audioUrl": TEST_URLS["small_generic"]}
    r = requests.post(url, headers=headers, json=payload, timeout=60)
    assert r.status_code == 400
    j = r.json()
    assert j.get("status") == "error"

def test_neither_input_error():
    url = f"{BASE_URL}/api/voice-detection"
    headers = {"x-api-key": API_KEY, "Content-Type": "application/json"}
    payload = {"language": "English", "audioFormat": "mp3"}
    r = requests.post(url, headers=headers, json=payload, timeout=60)
    assert r.status_code == 400
    j = r.json()
    assert j.get("status") == "error"

def test_invalid_url_format_error():
    url = f"{BASE_URL}/api/voice-detection"
    headers = {"x-api-key": API_KEY, "Content-Type": "application/json"}
    payload = {"language": "English", "audioFormat": "mp3", "audioUrl": "not-a-url"}
    r = requests.post(url, headers=headers, json=payload, timeout=60)
    assert r.status_code in (400, 500)
    j = r.json()
    assert j.get("status") == "error"

def test_no_auth_header_error():
    url = f"{BASE_URL}/api/voice-detection"
    payload = {"language": "English", "audioFormat": "mp3", "audioUrl": TEST_URLS["tiny_generic"]}
    r = requests.post(url, json=payload, timeout=60)
    assert r.status_code == 401
    j = r.json()
    assert j.get("status") == "error"

def test_invalid_api_key_error():
    url = f"{BASE_URL}/api/voice-detection"
    headers = {"Authorization": "Bearer wrong_key", "Content-Type": "application/json"}
    payload = {"language": "English", "audioFormat": "mp3", "audioUrl": TEST_URLS["large_generic"]}
    r = requests.post(url, headers=headers, json=payload, timeout=60)
    assert r.status_code == 401
    j = r.json()
    assert j.get("status") == "error"

