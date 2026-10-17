"""
Nature Intelligence Assistant router.

POST /api/nature/guide
"""

from __future__ import annotations

import logging
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from app.gemma_service import generate_nature_guide

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/nature", tags=["Nature Intelligence"])

VALID_ACTIONS = {"explain", "ask", "mission"}
MIN_GUIDE_CONFIDENCE = 0.50


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------
class NatureGuideRequest(BaseModel):
    species: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Predicted species label from the bird classifier.",
    )
    confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Classifier confidence score (0–1), if available.",
    )
    action: Literal["explain", "ask", "mission"] = Field(
        default="explain",
        description="Requested action: explain | ask | mission.",
    )
    user_question: str | None = Field(
        default=None,
        max_length=500,
        description="Optional nature-related question (used when action='ask').",
    )
    question: str | None = Field(
        default=None,
        max_length=500,
        description="Alias for user_question.",
    )

    @field_validator("species")
    @classmethod
    def species_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("species must not be blank")
        return v.strip()

    @property
    def effective_question(self) -> str | None:
        return self.user_question or self.question


class NatureGuideResponse(BaseModel):
    species: str
    summary: str
    interesting_facts: list[str]
    observation_tips: list[str]
    outdoor_mission: str
    safety_note: str
    disclaimer: str = (
        "Information is AI-generated and has not been independently verified. "
        "Always observe wildlife from a safe, respectful distance."
    )


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------
@router.post("/guide", response_model=NatureGuideResponse)
async def nature_guide(request: NatureGuideRequest) -> NatureGuideResponse:
    """
    Generate a Gemma 4 nature intelligence response for the predicted species.

    - **explain**: Plain-language description + facts + observation tips.
    - **ask**: Answer the user's nature-related question about the species.
    - **mission**: Return an actionable outdoor observation activity.
    """
    if request.confidence is not None and request.confidence < MIN_GUIDE_CONFIDENCE:
        raise HTTPException(
            status_code=422,
            detail=(
                "The bird prediction is too uncertain for Nature AI. "
                "Upload a clearer bird photo or select a stronger prediction."
            ),
        )
    try:
        data = await generate_nature_guide(
            species=request.species,
            confidence=request.confidence,
            action=request.action,
            user_question=request.effective_question,
        )
    except RuntimeError as exc:
        # API key not configured
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ConnectionError as exc:
        # Network / rate-limit / auth failures
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        # Unparseable model output
        logger.warning("Invalid Gemma response: %s", exc)
        raise HTTPException(
            status_code=502,
            detail="The AI model returned an unexpected response. Please try again.",
        ) from exc

    return NatureGuideResponse(**data)
