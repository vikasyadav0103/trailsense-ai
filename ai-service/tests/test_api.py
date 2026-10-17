import io

from fastapi.testclient import TestClient
from PIL import Image

from app.main import app


def make_png() -> bytes:
    image = Image.new("RGB", (16, 16), color=(30, 120, 60))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


class FakeRuntime:
    model = object()
    device = "cpu"

    def load(self):
        # Do not download the real model during API tests.
        return None

    def predict(self, image, top_k=5):
        assert image.mode == "RGB"
        return [{"label": "Test bird", "score": 0.91}]


def test_predict_returns_ranked_predictions(monkeypatch):
    monkeypatch.setattr("app.main.runtime", FakeRuntime())
    with TestClient(app) as client:
        response = client.post(
            "/predict",
            files={"file": ("bird.png", make_png(), "image/png")},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["predictions"][0]["label"] == "Test bird"
    assert body["predictions"][0]["score"] == 0.91


def test_rejects_non_image_content_type(monkeypatch):
    monkeypatch.setattr("app.main.runtime", FakeRuntime())
    with TestClient(app) as client:
        response = client.post(
            "/predict", files={"file": ("notes.txt", b"hello", "text/plain")}
        )
    assert response.status_code == 415


def test_rejects_invalid_image(monkeypatch):
    monkeypatch.setattr("app.main.runtime", FakeRuntime())
    with TestClient(app) as client:
        response = client.post(
            "/predict", files={"file": ("bad.png", b"not an image", "image/png")}
        )
    assert response.status_code == 400


def test_nature_guide_returns_structured_response(monkeypatch):
    async def fake_guide(*args, **kwargs):
        return {"species": "Test bird", "summary": "A helpful summary.", "interesting_facts": ["Fact"], "observation_tips": ["Tip"], "outdoor_mission": "Watch quietly.", "safety_note": "Keep your distance."}
    monkeypatch.setattr("app.nature_router.generate_nature_guide", fake_guide)
    with TestClient(app) as client:
        response = client.post("/api/nature/guide", json={"species": "Test bird", "action": "explain"})
    assert response.status_code == 200
    assert response.json()["outdoor_mission"] == "Watch quietly."



def test_nature_guide_rejects_invalid_action():
    with TestClient(app) as client:
        response = client.post("/api/nature/guide", json={"species": "Test bird", "action": "hack"})
    assert response.status_code == 422


def test_nature_guide_requires_species():
    with TestClient(app) as client:
        response = client.post("/api/nature/guide", json={"action": "explain"})
    assert response.status_code == 422


def test_root_serves_index():
    with TestClient(app) as client:
        response = client.get("/")
    assert response.status_code == 200
    assert "TrailSense AI" in response.text
