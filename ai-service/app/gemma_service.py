"""
Gemma 4 Nature Intelligence service.

Calls the Google GenAI API (Gemini API) with the verified model identifier.
All credentials are read from environment variables—never hardcoded.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

from app.prompts import NATURE_GUIDE_SYSTEM, build_nature_guide_prompt

from dotenv import find_dotenv, load_dotenv

# Ensure environment variables are loaded
load_dotenv(find_dotenv(usecwd=True))
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"), override=False)
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"), override=False)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
_MODEL_DEFAULT = "gemma-4-26b-a4b-it"
_TIMEOUT_SECONDS_DEFAULT = 60

# Required top-level keys in every valid response
_REQUIRED_KEYS = {
    "species",
    "summary",
    "interesting_facts",
    "observation_tips",
    "outdoor_mission",
    "safety_note",
}

# ---------------------------------------------------------------------------
# Client (lazy singleton)
# ---------------------------------------------------------------------------
_client: Any = None


def _get_client() -> Any:
    global _client
    if _client is None:
        api_key = os.getenv("GEMMA_API_KEY", "")
        if not api_key:
            raise RuntimeError(
                "GEMMA_API_KEY is not set. "
                "Add it to your .env file and restart the server."
            )
        from google import genai

        timeout = int(os.getenv("GEMMA_TIMEOUT", str(_TIMEOUT_SECONDS_DEFAULT)))
        _client = genai.Client(api_key=api_key, http_options={"timeout": timeout * 1000})
    return _client


# ---------------------------------------------------------------------------
# Response validation
# ---------------------------------------------------------------------------
def _extract_json(text: str) -> dict[str, Any]:
    """Strip optional markdown fences and parse JSON."""
    stripped = text.strip()
    # Remove ```json ... ``` or ``` ... ``` wrappers if present
    stripped = re.sub(r"^```(?:json)?\s*", "", stripped, flags=re.IGNORECASE)
    stripped = re.sub(r"\s*```$", "", stripped)
    stripped = stripped.strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        # Fallback: extract the JSON object bounded by outermost { and }
        match = re.search(r"\{.*\}", stripped, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise


def _validate_response(data: dict[str, Any]) -> dict[str, Any]:
    """Ensure all required keys exist; coerce missing/wrong types to safe defaults."""
    if not isinstance(data, dict):
        raise ValueError("Gemma response must be a JSON object")
    for key in _REQUIRED_KEYS:
        if key not in data:
            data[key] = [] if key in {"interesting_facts", "observation_tips"} else ""
    # Coerce list fields
    for list_key in ("interesting_facts", "observation_tips"):
        if not isinstance(data[list_key], list):
            data[list_key] = [str(data[list_key])] if data[list_key] else []
    # Coerce string fields
    for str_key in ("species", "summary", "outdoor_mission", "safety_note"):
        if not isinstance(data[str_key], str):
            data[str_key] = str(data[str_key])
    return data


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
async def generate_nature_guide(
    species: str,
    confidence: float | None,
    action: str,
    user_question: str | None,
) -> dict[str, Any]:
    """
    Call Gemma 4 via the Gemini API and return a validated structured response.

    Raises:
        RuntimeError: GEMMA_API_KEY not configured.
        ValueError: Model returned unparseable or structurally invalid JSON.
        ConnectionError: Network or API availability problem.
    """
    client = _get_client()
    user_prompt = build_nature_guide_prompt(species, confidence, action, user_question)

    try:
        model_name = os.getenv("GEMMA_MODEL", _MODEL_DEFAULT)
        response = client.models.generate_content(
            model=model_name,
            contents=user_prompt,
            config={
                "system_instruction": NATURE_GUIDE_SYSTEM,
                "temperature": 0.4,
                "max_output_tokens": 3072,
                "response_mime_type": "application/json",
            },
        )
    except Exception as exc:
        status = getattr(exc, "code", None) or getattr(exc, "status_code", None)
        if status == 401:
            raise ConnectionError(
                "Gemma API authentication failed. Check your GEMMA_API_KEY."
            ) from exc
        if status == 429:
            raise ConnectionError(
                "Gemma API rate limit reached. Please wait and try again."
            ) from exc
        logger.error("Gemma API error: %s", exc)
        raise ConnectionError(f"Gemma API returned an error: {exc}") from exc

    raw_text: str = ""
    try:
        raw_text = response.text or ""
        data = _extract_json(raw_text)
        return _validate_response(data)
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        logger.error("Gemma response parse error. Raw text: %r", raw_text)
        raise ValueError(
            f"Gemma returned an unexpected response format: {exc}"
        ) from exc
