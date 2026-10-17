import io
import os
from contextlib import asynccontextmanager
from typing import Any

import torch
from dotenv import find_dotenv, load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel
from transformers import AutoImageProcessor, AutoModelForImageClassification

# Load environment variables searching upward from CWD and project root
load_dotenv(find_dotenv(usecwd=True))
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", ".env"), override=False)
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"), override=False)

MODEL_ID = os.getenv("MODEL_ID", "dennisjooo/Birds-Classifier-EfficientNetB2")
MODEL_LOCAL_ONLY = os.getenv("MODEL_LOCAL_ONLY", "false").lower() in {"1", "true", "yes"}
MAX_IMAGE_BYTES = int(os.getenv("MAX_IMAGE_BYTES", str(8 * 1024 * 1024)))
TOP_K_DEFAULT = 5


class Prediction(BaseModel):
    label: str
    score: float


class PredictionResponse(BaseModel):
    model_id: str
    predictions: list[Prediction]
    disclaimer: str = "Predictions are suggestions; scores may not be calibrated and the model may not recognize this image."


class ModelRuntime:
    def __init__(self) -> None:
        self.processor: Any = None
        self.model: Any = None
        self.device = "cpu"

    def load(self) -> None:
        self.processor = AutoImageProcessor.from_pretrained(
            MODEL_ID, local_files_only=MODEL_LOCAL_ONLY
        )
        self.model = AutoModelForImageClassification.from_pretrained(
            MODEL_ID, local_files_only=MODEL_LOCAL_ONLY
        )
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model.to(self.device)
        self.model.eval()

    def predict(self, image: Image.Image, top_k: int = TOP_K_DEFAULT) -> list[dict[str, Any]]:
        if self.model is None or self.processor is None:
            raise RuntimeError("Model is not loaded")
        inputs = self.processor(images=image, return_tensors="pt")
        inputs = {key: value.to(self.device) for key, value in inputs.items()}
        with torch.inference_mode():
            logits = self.model(**inputs).logits
            scores = torch.softmax(logits, dim=-1)[0]
        count = min(max(1, top_k), scores.shape[-1])
        values, indices = torch.topk(scores, k=count)
        labels = self.model.config.id2label
        return [
            {"label": str(labels.get(int(index), f"class_{int(index)}")), "score": float(score)}
            for score, index in zip(values.cpu().tolist(), indices.cpu().tolist())
        ]


runtime = ModelRuntime()


@asynccontextmanager
async def lifespan(_: FastAPI):
    runtime.load()
    yield


from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="TrailSense AI",
    description=(
        "Bird classification API powered by EfficientNetB2, "
        "plus a Gemma 4 Nature Intelligence Assistant. "
        "First startup may download model files."
    ),
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Nature Intelligence Assistant — single registration via router
from app.nature_router import router as nature_router  # noqa: E402
app.include_router(nature_router)

STATIC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist"))
ASSETS_DIR = os.path.join(STATIC_DIR, "assets")
FALLBACK_FRONTEND = os.path.join(os.path.dirname(__file__), "static", "index.html")

if os.path.isdir(ASSETS_DIR):
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")
if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.isfile(index_file):
        return FileResponse(index_file)
    if os.path.isfile(FALLBACK_FRONTEND):
        return FileResponse(FALLBACK_FRONTEND)
    raise HTTPException(status_code=503, detail="Frontend is not available.")


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok" if runtime.model is not None else "not_ready",
        "model_id": MODEL_ID,
        "device": runtime.device,
        "local_files_only": MODEL_LOCAL_ONLY,
    }


@app.post("/predict", response_model=PredictionResponse)
async def predict(file: UploadFile = File(...)) -> PredictionResponse:
    if file.content_type not in {"image/jpeg", "image/png", "image/webp", "image/bmp"}:
        raise HTTPException(status_code=415, detail="Upload a JPEG, PNG, WEBP, or BMP image.")
    raw = await file.read(MAX_IMAGE_BYTES + 1)
    if not raw:
        raise HTTPException(status_code=400, detail="The uploaded image is empty.")
    if len(raw) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail=f"Image exceeds {MAX_IMAGE_BYTES} bytes.")
    try:
        with Image.open(io.BytesIO(raw)) as source:
            image = source.convert("RGB")
    except (UnidentifiedImageError, OSError):
        raise HTTPException(status_code=400, detail="The uploaded file is not a valid image.") from None
    try:
        predictions = runtime.predict(image)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail="Model is not ready.") from exc
    return PredictionResponse(model_id=MODEL_ID, predictions=predictions)
