import os

from fastapi.testclient import TestClient

os.environ.setdefault("API_KEY", "sk_test_key")

from app.main import app  # noqa: E402


client = TestClient(app)


def test_health_endpoint():
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("status") == "ok"
    assert "model_loaded" in data

