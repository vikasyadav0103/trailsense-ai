# Local bird inference service

A small FastAPI service for running bird image classification locally. The model is loaded once at startup and inference uses local model files after the initial download.

## Model choice

Default model: [dennisjooo/Birds-Classifier-EfficientNetB2](https://huggingface.co/dennisjooo/Birds-Classifier-EfficientNetB2). Its model card declares Apache-2.0 and describes a fine-tuned EfficientNet-B2 classifier trained on a 525-species bird dataset. This is a practical proof-of-concept model, not a guarantee of global coverage or real-world accuracy. Validate label coverage and predictions against local Indian bird photos before making broader claims.

Model weights are downloaded from Hugging Face the first time unless `MODEL_LOCAL_ONLY=true`. Set `MODEL_ID` to use another compatible Transformers image-classification model. Review that model's license separately.

## Run locally

Python 3.11 is recommended.

```bash
cd ai-service
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8001
```

The first run requires internet access to download model files. After download, set `MODEL_LOCAL_ONLY=true` and run with network disconnected to test local inference.

## API

- `GET /health` — readiness and model metadata.
- `POST /predict` — multipart form field `file`; returns ranked labels and scores.
- `POST /api/nature/guide` — accepts a predicted species, action (`explain`, `ask`, or `mission`), and optional question.
- `GET /` — responsive web interface for the full demo flow.

Example:

```bash
curl -F "file=@bird.jpg" http://127.0.0.1:8001/predict
```

Scores are model confidence scores, not necessarily calibrated probabilities. A classifier always chooses among its known labels, even when the image is not a bird. Treat results as suggestions.

## Tests

```bash
pytest
```

Tests use a fake classifier and do not download model weights.
