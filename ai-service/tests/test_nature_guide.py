"""
Tests for the Nature Intelligence Assistant endpoint (POST /api/nature/guide).

All tests mock the Gemma API — no real API calls are made.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_RESPONSE = {
    "species": "Indian Peafowl",
    "summary": "A large, colourful bird native to South Asia.",
    "interesting_facts": ["Males display elaborate tail feathers.", "They are omnivores."],
    "observation_tips": ["Look for them at forest edges.", "Visit early morning."],
    "outdoor_mission": "Spend 20 minutes observing a peacock from 10 m away.",
    "safety_note": "Always keep a respectful distance from wild birds.",
}


def _mock_guide(monkeypatch, return_value=None, side_effect=None):
    """Patch generate_nature_guide in the router's imported module."""
    import app.nature_router as router_module

    async def fake(*args, **kwargs):
        if side_effect:
            raise side_effect
        return return_value or VALID_RESPONSE

    monkeypatch.setattr(router_module, "generate_nature_guide", fake)


# ---------------------------------------------------------------------------
# 1. Valid nature-guide requests
# ---------------------------------------------------------------------------

def test_explain_action_returns_structured_response(monkeypatch):
    _mock_guide(monkeypatch)
    with TestClient(app) as client:
        r = client.post(
            "/api/nature/guide",
            json={"species": "Indian Peafowl", "confidence": 0.91, "action": "explain"},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["species"] == "Indian Peafowl"
    assert isinstance(body["interesting_facts"], list)
    assert "disclaimer" in body


def test_ask_action_with_question(monkeypatch):
    _mock_guide(monkeypatch)
    with TestClient(app) as client:
        r = client.post(
            "/api/nature/guide",
            json={
                "species": "Indian Peafowl",
                "action": "ask",
                "user_question": "What do peacocks eat?",
            },
        )
    assert r.status_code == 200


def test_mission_action(monkeypatch):
    _mock_guide(monkeypatch)
    with TestClient(app) as client:
        r = client.post(
            "/api/nature/guide",
            json={"species": "Indian Peafowl", "action": "mission"},
        )
    assert r.status_code == 200
    assert r.json()["outdoor_mission"] != ""


# ---------------------------------------------------------------------------
# 2. Invalid or missing species data
# ---------------------------------------------------------------------------

def test_missing_species_returns_422(monkeypatch):
    _mock_guide(monkeypatch)
    with TestClient(app) as client:
        r = client.post("/api/nature/guide", json={"action": "explain"})
    assert r.status_code == 422


def test_blank_species_returns_422(monkeypatch):
    _mock_guide(monkeypatch)
    with TestClient(app) as client:
        r = client.post("/api/nature/guide", json={"species": "   ", "action": "explain"})
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# 3. Invalid action values
# ---------------------------------------------------------------------------

def test_invalid_action_returns_422(monkeypatch):
    _mock_guide(monkeypatch)
    with TestClient(app) as client:
        r = client.post(
            "/api/nature/guide",
            json={"species": "Crow", "action": "dance"},
        )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# 4. Malformed model responses (ValueError from gemma_service)
# ---------------------------------------------------------------------------

def test_malformed_gemma_response_returns_502(monkeypatch):
    _mock_guide(monkeypatch, side_effect=ValueError("bad JSON"))
    with TestClient(app) as client:
        r = client.post(
            "/api/nature/guide",
            json={"species": "Sparrow", "action": "explain"},
        )
    assert r.status_code == 502


# ---------------------------------------------------------------------------
# 5. Model API timeouts / network errors
# ---------------------------------------------------------------------------

def test_connection_error_returns_503(monkeypatch):
    _mock_guide(monkeypatch, side_effect=ConnectionError("timeout"))
    with TestClient(app) as client:
        r = client.post(
            "/api/nature/guide",
            json={"species": "Sparrow", "action": "explain"},
        )
    assert r.status_code == 503


# ---------------------------------------------------------------------------
# 6. Authentication and rate-limit errors
# ---------------------------------------------------------------------------

def test_runtime_error_key_missing_returns_503(monkeypatch):
    _mock_guide(monkeypatch, side_effect=RuntimeError("GEMMA_API_KEY is not set"))
    with TestClient(app) as client:
        r = client.post(
            "/api/nature/guide",
            json={"species": "Sparrow", "action": "explain"},
        )
    assert r.status_code == 503
    assert "GEMMA_API_KEY" in r.json()["detail"]


# ---------------------------------------------------------------------------
# 7. Structured response validation
# ---------------------------------------------------------------------------

def test_response_contains_all_required_fields(monkeypatch):
    _mock_guide(monkeypatch)
    with TestClient(app) as client:
        r = client.post(
            "/api/nature/guide",
            json={"species": "Indian Peafowl", "action": "explain"},
        )
    body = r.json()
    for field in ("species", "summary", "interesting_facts", "observation_tips",
                  "outdoor_mission", "safety_note", "disclaimer"):
        assert field in body, f"Missing field: {field}"


# ---------------------------------------------------------------------------
# 8. Existing bird-classification remains unaffected
# ---------------------------------------------------------------------------

import io
from PIL import Image


def make_png() -> bytes:
    img = Image.new("RGB", (16, 16), color=(30, 120, 60))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class FakeRuntime:
    model = object()
    device = "cpu"

    def load(self):
        return None

    def predict(self, image, top_k=5):
        assert image.mode == "RGB"
        return [{"label": "Indian Peafowl", "score": 0.91}]


def test_existing_predict_endpoint_still_works(monkeypatch):
    monkeypatch.setattr("app.main.runtime", FakeRuntime())
    with TestClient(app) as client:
        r = client.post(
            "/predict",
            files={"file": ("peacock.png", make_png(), "image/png")},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["predictions"][0]["label"] == "Indian Peafowl"
