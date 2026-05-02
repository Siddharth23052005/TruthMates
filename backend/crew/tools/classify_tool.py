"""
CivicClassifyTool — CrewAI tool that classifies scraped posts as civic
or non-civic using BERT/IndicBERT embeddings and a civic-topic anchor.
"""

from __future__ import annotations

import json
import re
from typing import Type

import torch
from crewai.tools import BaseTool
from langdetect import DetectorFactory, detect
from pydantic import BaseModel, Field
from transformers import AutoModel, AutoTokenizer


# ── Language detection (deterministic) ───────────────────────────────────────

DetectorFactory.seed = 0


# ── Model names ─────────────────────────────────────────────────────────────

_EN_MODEL = "bert-base-uncased"
_INDIC_MODEL = "ai4bharat/indic-bert"


# ── Civic anchor text (ASCII only) ──────────────────────────────────────────

_CIVIC_ANCHOR_EN = (
    "government scheme election policy aadhaar ration card pm scheme "
    "welfare subsidy ministry public service notification"
)
_CIVIC_ANCHOR_INDIC = (
    "sarkar yojana chunav niti aadhaar ration card pm yojana "
    "kalyan subsidy mantralaya jan sewa notification"
)

_CIVIC_KEYWORDS = {
    "government",
    "scheme",
    "election",
    "policy",
    "aadhaar",
    "ration",
    "ration card",
    "pm",
    "yojana",
    "welfare",
    "subsidy",
    "ministry",
    "public service",
    "notification",
}

_CONFIDENCE_THRESHOLD = 0.75


# ── Input schema ────────────────────────────────────────────────────────────

class CivicClassifyInput(BaseModel):
    """Input schema for CivicClassifyTool."""

    posts_json: str = Field(
        ...,
        description=(
            "JSON string containing a list of civic post objects with fields: "
            "title, description, link, pub_date, source."
        ),
    )


# ── Tool implementation ─────────────────────────────────────────────────────

class CivicClassifyTool(BaseTool):
    """
    Classifies a list of posts as civic or non-civic.

    Adds: label, confidence, language, needs_review.
    """

    name: str = "CivicClassifyTool"
    description: str = (
        "Classifies posts as civic or non-civic using BERT/IndicBERT embeddings. "
        "Input: JSON list of posts. Output: JSON list with label, confidence, "
        "language, needs_review fields."
    )
    args_schema: Type[BaseModel] = CivicClassifyInput

    def _run(self, posts_json: str) -> str:
        posts = _safe_parse(posts_json)
        if not isinstance(posts, list):
            return json.dumps([], ensure_ascii=True)

        results: list[dict] = []
        for post in posts:
            title = (post.get("title") or "").strip()
            description = (post.get("description") or "").strip()
            text = _normalize_text(f"{title}. {description}")

            language = _detect_language(text)
            label, confidence, needs_review = _classify_text(text, language)

            results.append(
                {
                    **post,
                    "label": label,
                    "confidence": round(confidence, 4),
                    "language": language,
                    "needs_review": needs_review,
                }
            )

        return json.dumps(results, ensure_ascii=True, indent=2)


# ── Helpers ─────────────────────────────────────────────────────────────────

_model_cache: dict[str, tuple[AutoTokenizer, AutoModel]] = {}
_anchor_cache: dict[str, torch.Tensor] = {}


def _safe_parse(text: str) -> list:
    """Parse JSON, stripping markdown fences if present."""
    text = re.sub(r"```(?:json)?\s*", "", text).strip()
    text = text.rstrip("`").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return []


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _detect_language(text: str) -> str:
    if re.search(r"[\u0900-\u097F]", text):
        return "hi"
    try:
        return detect(text)
    except Exception:
        return "unknown"


def _get_model(model_name: str) -> tuple[AutoTokenizer, AutoModel]:
    if model_name in _model_cache:
        return _model_cache[model_name]

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModel.from_pretrained(model_name)
    model.eval()
    _model_cache[model_name] = (tokenizer, model)
    return tokenizer, model


def _embed_text(text: str, model_name: str) -> torch.Tensor:
    tokenizer, model = _get_model(model_name)
    inputs = tokenizer(
        text,
        truncation=True,
        max_length=256,
        return_tensors="pt",
    )
    with torch.no_grad():
        outputs = model(**inputs)

    if hasattr(outputs, "pooler_output") and outputs.pooler_output is not None:
        vector = outputs.pooler_output
    else:
        vector = outputs.last_hidden_state[:, 0, :]

    vector = torch.nn.functional.normalize(vector, p=2, dim=1)
    return vector.squeeze(0)


def _get_anchor(model_name: str) -> torch.Tensor:
    if model_name in _anchor_cache:
        return _anchor_cache[model_name]

    anchor_text = _CIVIC_ANCHOR_EN if model_name == _EN_MODEL else _CIVIC_ANCHOR_INDIC
    anchor = _embed_text(anchor_text, model_name)
    _anchor_cache[model_name] = anchor
    return anchor


def _keyword_boost(text: str) -> float:
    lowered = text.lower()
    for keyword in _CIVIC_KEYWORDS:
        if keyword in lowered:
            return 0.1
    return 0.0


def _classify_text(text: str, language: str) -> tuple[str, float, bool]:
    if language == "en":
        model_name = _EN_MODEL
    else:
        model_name = _INDIC_MODEL

    anchor = _get_anchor(model_name)
    vector = _embed_text(text, model_name)

    similarity = torch.nn.functional.cosine_similarity(
        vector.unsqueeze(0), anchor.unsqueeze(0)
    ).item()
    confidence = (similarity + 1.0) / 2.0
    confidence = min(1.0, max(0.0, confidence + _keyword_boost(text)))

    label = "civic" if confidence >= _CONFIDENCE_THRESHOLD else "non-civic"
    needs_review = confidence < _CONFIDENCE_THRESHOLD

    return label, confidence, needs_review
