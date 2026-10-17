# TrailSense AI 🌿

**An AI-powered nature companion — identify birds and explore the outdoors.**

TrailSense AI helps you spend less time on screens and more time outdoors.
Photograph a bird, get an instant classification, then ask Gemma 4 to explain
the species, answer your nature questions, or suggest an outdoor observation
mission.

> **Status:** Active hackathon project (Hacktoberfest Hack Day Mumbai 2026).
> End-to-end functionality is verified for the bird-classification pipeline.
> Gemma 4 integration requires an internet connection and a valid API key.

---

## Architecture & request flow

```
Web UI
  │
  ├─ POST /predict  ──────────────────────────────────────────────────────────
  │       │                                                                   │
  │  ai-service (FastAPI)                                               (Local)
  │       │                                                                   │
  │  EfficientNetB2 classifier ─► Predicted species + confidence             │
  │       │                                                                   │
  ├─ POST /api/nature/guide  ─────────────────────────────────────────────────
  │       │                                                                   │
  │  gemma_service.py ──► Google Gemini API (gemma-4-26b-a4b-it)     (Online)
  │       │
  │  Structured JSON response:
  │    species / summary / interesting_facts /
  │    observation_tips / outdoor_mission / safety_note
  │
  └─ Displayed in UI
```

```
Bird photograph → EfficientNetB2 classifier → Predicted species
                                                     │
                                          Gemma 4 Nature Assistant
                                                     │
                                    Explanation / Q&A / Outdoor mission
```

---

## Features

| Feature | Endpoint | Description |
|---------|----------|-------------|
| Bird identification | `POST /predict` | Upload a photo → top-5 species predictions |
| Explain This Bird | `POST /api/nature/guide` (`action=explain`) | Plain-language species description |
| Ask Nature AI | `POST /api/nature/guide` (`action=ask`) | Answer a nature question about the bird |
| Generate Outdoor Mission | `POST /api/nature/guide` (`action=mission`) | Actionable wildlife observation activity |
| Health check | `GET /health` | Service and model status |

---

## Setup and installation

### Single-container deployment

The root `Dockerfile` builds the React/Vite frontend and packages it with the FastAPI backend in one image. Configure `.env`, then run:

```bash
docker compose up --build
```

Open `http://localhost:8000`. The same container serves the React interface, `/predict`, and `/api/nature/guide`. The first startup may download EfficientNetB2 weights; the Compose volume preserves the model cache across restarts.

### Web UI

The Web UI is served directly by the FastAPI service at `http://localhost:8000/`. When the server is running, simply open your browser and navigate to `http://127.0.0.1:8000/` to use the interactive application.

### Prerequisites

- Python 3.10 or later
- A [Google AI Studio](https://aistudio.google.com/app/apikey) API key (free tier available)

### 1. Clone the repository

```bash
git clone https://github.com/your-org/trailsense-ai.git
cd trailsense-ai
```

### 2. Create a virtual environment

```bash
cd ai-service
python -m venv venv
# Windows
.\venv\Scripts\Activate.ps1
# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp ../.env.example ../.env
# Edit .env and set GEMMA_API_KEY
```

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GEMMA_API_KEY` | **Yes** | — | Google AI Studio API key |
| `GEMMA_MODEL` | No | `gemma-4-26b-a4b-it` | Gemma 4 model identifier |
| `GEMMA_TIMEOUT` | No | `30` | API timeout in seconds |
| `MODEL_ID` | No | `dennisjooo/Birds-Classifier-EfficientNetB2` | HuggingFace classifier model |
| `MODEL_LOCAL_ONLY` | No | `false` | Prevent model downloads |
| `MAX_IMAGE_BYTES` | No | `8388608` | Upload size limit (bytes) |

### 5. Run the server

```bash
# From the ai-service directory
uvicorn app.main:app --reload
```

Server starts at **http://127.0.0.1:8000**
Interactive API docs at **http://127.0.0.1:8000/docs**

---

## Using the new features

### Explain This Bird

```bash
curl -X POST http://127.0.0.1:8000/api/nature/guide \
  -H "Content-Type: application/json" \
  -d '{"species": "Indian Peafowl", "confidence": 0.91, "action": "explain"}'
```

### Ask Nature AI

```bash
curl -X POST http://127.0.0.1:8000/api/nature/guide \
  -H "Content-Type: application/json" \
  -d '{"species": "Indian Peafowl", "action": "ask", "user_question": "What do peacocks eat?"}'
```

### Generate Outdoor Mission

```bash
curl -X POST http://127.0.0.1:8000/api/nature/guide \
  -H "Content-Type: application/json" \
  -d '{"species": "Indian Peafowl", "action": "mission"}'
```

---

## Running tests

```bash
# From the ai-service directory, with venv active
python -m pytest tests/ -v
```

All tests mock the Gemma API — **no real API key or network access is required** to run the test suite.

---

## AI model and API limitations

- **EfficientNetB2 classifier**: Predictions are suggestions; the model may not recognise all species or images. Confidence scores are not calibrated probabilities.
- **Gemma 4 (hosted)**: Responses are AI-generated and have **not** been independently verified against a wildlife reference database. Do not treat them as authoritative scientific information.
- **Internet required**: The Gemma 4 inference call requires an active internet connection. The bird classifier runs locally and continues to work without connectivity.
- **Rate limits**: The free-tier Gemini API has daily usage quotas.

---

## Privacy considerations

- Uploaded images are processed in memory and never stored by the AI service.
- Gemma 4 prompts include only the predicted species label and the user's question — no raw image data is sent to Google.
- Set `GEMMA_API_KEY` only in `.env`, which is excluded from Git by `.gitignore`.

---

## Contributing

Contributions are welcome. Please discuss substantial changes in an issue and include reproducible tests. Do not commit model weights, personal photos, or API keys.

## License

Source code: MIT License. Model weights and datasets may have separate terms.

Challenge: [Hacktoberfest Open-Source AI Challenge — Week 1: Touch Grass](https://dev.to/challenges/hacktoberfest-week1-2026-10-05).
