import base64
import os
from pathlib import Path

from fastapi.testclient import TestClient


os.environ.setdefault("API_KEY", "sk_test_key")

from app.main import app  # noqa: E402


client = TestClient(app)


def _load_sample_mp3() -> str:
    root = Path(__file__).resolve().parents[1]
    sample_path = (
        root
        / "data"
        / "human"
        / "english"
        / "english_proto_000.mp3"
    )
    with open(sample_path, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")


def test_voice_detection_success():
    audio_b64 = _load_sample_mp3()
    payload = {
        "language": "English",
        "audioFormat": "mp3",
        "audioBase64": audio_b64,
    }
    headers = {"x-api-key": "sk_test_key"}
    resp = client.post("/api/voice-detection", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["language"] == "English"
    assert data["classification"] in ("AI_GENERATED", "HUMAN", "BORDERLINE")
    assert 0.0 <= data["confidenceScore"] <= 1.0
    assert isinstance(data["explanation"], str) and data["explanation"]


def test_voice_detection_invalid_api_key():
    audio_b64 = _load_sample_mp3()
    payload = {
        "language": "English",
        "audioFormat": "mp3",
        "audioBase64": audio_b64,
    }
    headers = {"x-api-key": "wrong_key"}
    resp = client.post("/api/voice-detection", json=payload, headers=headers)
    assert resp.status_code == 401

