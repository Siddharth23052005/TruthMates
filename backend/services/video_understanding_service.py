from __future__ import annotations

import base64
import json
import re
from pathlib import Path
from typing import Literal, Optional

import httpx
from pydantic import BaseModel, Field

from core.llm import get_vision_client_config
from core.logging import get_logger, log_event, stage_duration_ms, stage_start
from models.schemas import VideoUnderstanding
from video.frame_extractor import extract_keyframes

logger = get_logger("truthmates.video.understanding")

_VISION_PROMPT = """You are analyzing frames from a video to describe its content for a civic fact-checking system.

Look at all provided frames together and answer:
1. What is happening in this video?
2. What kind of content is this? (government speech, news report, protest, entertainment,
   personal video, advertisement, other)
3. Are any text overlays, banners, or captions visible? If yes, what do they say?
4. What is the setting? (indoor/outdoor, official venue, street, studio, other)
5. What language appears to be spoken or displayed?

Be specific and factual. Do not guess political identity of speakers unless official
branding or text makes it unambiguous. Do not speculate beyond what is visible.

Respond ONLY in this JSON format:
{
  "description": "one paragraph plain description of the video content",
  "content_type": "GOVERNMENT_SPEECH | NEWS_REPORT | PROTEST | ENTERTAINMENT | PERSONAL | ADVERTISEMENT | UNKNOWN",
  "visible_text": "any text visible in frames, or null",
  "setting": "description of physical setting",
  "detected_language": "en | hi | te | ta | mr | bn | unknown",
  "confidence": 0.0 to 1.0
}"""

_ALLOWED_CONTENT_TYPES = {
    "GOVERNMENT_SPEECH",
    "NEWS_REPORT",
    "PROTEST",
    "ENTERTAINMENT",
    "PERSONAL",
    "ADVERTISEMENT",
    "UNKNOWN",
}
_ALLOWED_LANGUAGES = {"en", "hi", "te", "ta", "mr", "bn", "unknown"}


class VisionResult(BaseModel):
    description: str
    content_type: str = "UNKNOWN"
    visible_text: Optional[str] = None
    setting: Optional[str] = None
    detected_language: str = "unknown"
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    source: Literal["vision"] = "vision"


class TranscriptResult(BaseModel):
    description: str
    content_type: str = "UNKNOWN"
    detected_language: str = "unknown"
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    source: Literal["transcript+metadata"] = "transcript+metadata"


def _normalize_language(value: Optional[str]) -> str:
    normalized = (value or "unknown").strip().lower()
    return normalized if normalized in _ALLOWED_LANGUAGES else "unknown"


def _normalize_content_type(value: Optional[str]) -> str:
    normalized = (value or "UNKNOWN").strip().upper()
    return normalized if normalized in _ALLOWED_CONTENT_TYPES else "UNKNOWN"


def _extract_text_response(content) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text")
                if text:
                    parts.append(str(text))
        return "\n".join(parts).strip()
    return str(content).strip()


def _parse_vision_json(raw_text: str) -> VisionResult:
    clean = raw_text.strip()
    try:
        payload = json.loads(clean)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", clean, re.DOTALL)
        if not match:
            return VisionResult(description=clean or "Vision description unavailable", confidence=0.0)
        try:
            payload = json.loads(match.group())
        except json.JSONDecodeError:
            return VisionResult(description=clean or "Vision description unavailable", confidence=0.0)

    return VisionResult(
        description=str(payload.get("description") or "Vision description unavailable").strip(),
        content_type=_normalize_content_type(payload.get("content_type")),
        visible_text=payload.get("visible_text") or None,
        setting=payload.get("setting") or None,
        detected_language=_normalize_language(payload.get("detected_language")),
        confidence=max(0.0, min(1.0, float(payload.get("confidence") or 0.0))),
    )


def _frame_to_data_url(frame_path: str) -> str:
    encoded = base64.b64encode(Path(frame_path).read_bytes()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def _detect_language_from_transcript(partial_transcript: Optional[str]) -> str:
    text = (partial_transcript or "").strip()
    if not text:
        return "unknown"
    if re.search(r"[\u0900-\u097F]", text):
        return "hi"
    if re.search(r"[A-Za-z]", text):
        return "en"
    return "unknown"


def _has_partial_transcript(fallback: TranscriptResult) -> bool:
    return fallback.description.startswith("Partial speech detected:")


async def describe_from_vision(frame_paths: list[str], request_id: str) -> VisionResult:
    started = stage_start()
    if not frame_paths:
        result = VisionResult(description="Frame extraction failed", confidence=0.0)
        log_event(
            logger,
            "stage_complete",
            request_id=request_id,
            stage="video_vision_description",
            duration_ms=stage_duration_ms(started),
            provider="unavailable",
            confidence=result.confidence,
            content_type=result.content_type,
        )
        return result

    client_config = get_vision_client_config()
    if client_config is None:
        result = VisionResult(description="Vision model unavailable", confidence=0.0)
        log_event(
            logger,
            "stage_complete",
            request_id=request_id,
            stage="video_vision_description",
            duration_ms=stage_duration_ms(started),
            provider="unavailable",
            confidence=result.confidence,
            content_type=result.content_type,
        )
        return result

    message_content = [{"type": "text", "text": _VISION_PROMPT}]
    for frame_path in frame_paths:
        message_content.append(
            {
                "type": "image_url",
                "image_url": {"url": _frame_to_data_url(frame_path)},
            }
        )

    payload = {
        "model": client_config["model"],
        "temperature": 0,
        "messages": [{"role": "user", "content": message_content}],
        "response_format": {"type": "json_object"},
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{client_config['base_url'].rstrip('/')}/chat/completions",
                headers={
                    "Authorization": f"Bearer {client_config['api_key']}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            raw_text = _extract_text_response(
                response.json().get("choices", [{}])[0].get("message", {}).get("content", "")
            )
            result = _parse_vision_json(raw_text)
    except Exception as exc:
        log_event(
            logger,
            "stage_failed",
            level="warning",
            request_id=request_id,
            stage="video_vision_description",
            error=str(exc),
        )
        result = VisionResult(description="Vision description unavailable", confidence=0.0)

    log_event(
        logger,
        "stage_complete",
        request_id=request_id,
        stage="video_vision_description",
        duration_ms=stage_duration_ms(started),
        provider=client_config["provider"],
        confidence=result.confidence,
        content_type=result.content_type,
    )
    return result


def describe_from_transcript(
    partial_transcript: Optional[str],
    duration_seconds: float,
    filename: str,
    detected_language: Optional[str],
) -> TranscriptResult:
    del filename
    transcript = (partial_transcript or "").strip()
    words = transcript.split()
    language = _normalize_language(detected_language)

    if len(words) >= 5:
        truncated = " ".join(words[:200])
        return TranscriptResult(
            description=f"Partial speech detected: {truncated}",
            detected_language=language,
            confidence=0.2,
        )

    if language != "unknown":
        return TranscriptResult(
            description=f"This video contains no extractable speech or dialogue. Background audio detected appears to be related to {language.upper()}.",
            detected_language=language,
            confidence=0.05,
        )

    return TranscriptResult(
        description=f"This {duration_seconds:.0f}-second video contains no detectable speech, dialogue, or extractable audio content.",
        detected_language="unknown",
        confidence=0.05,
    )


def merge_understanding(vision: VisionResult, fallback: TranscriptResult) -> VideoUnderstanding:
    has_partial_transcript = _has_partial_transcript(fallback)

    if vision.confidence >= 0.70:
        description = vision.description
        understanding_source: Literal["vision+transcript", "vision_only"] = "vision_only"
        if has_partial_transcript:
            description = f"{vision.description} Supporting transcript note: {fallback.description}"
            understanding_source = "vision+transcript"
        return VideoUnderstanding(
            description=description,
            visual_context=vision.setting,
            detected_language=vision.detected_language if vision.detected_language != "unknown" else fallback.detected_language,
            estimated_content_type=vision.content_type,
            visible_text=vision.visible_text,
            confidence=vision.confidence,
            understanding_source=understanding_source,
        )

    if vision.confidence >= 0.40:
        combined_confidence = round((vision.confidence + fallback.confidence) / 2, 3)
        return VideoUnderstanding(
            description=f"{vision.description} {fallback.description}".strip(),
            visual_context=vision.setting,
            detected_language=vision.detected_language if vision.detected_language != "unknown" else fallback.detected_language,
            estimated_content_type=vision.content_type,
            visible_text=vision.visible_text,
            confidence=combined_confidence,
            understanding_source="vision+transcript",
        )

    return VideoUnderstanding(
        description=fallback.description,
        visual_context=None,
        detected_language=fallback.detected_language,
        estimated_content_type="UNKNOWN",
        visible_text=None,
        confidence=fallback.confidence,
        understanding_source="transcript+metadata",
    )


async def understand_video(
    video_path: str,
    partial_transcript: Optional[str],
    duration_seconds: float,
    filename: str,
    request_id: str,
) -> VideoUnderstanding:
    frame_paths = extract_keyframes(video_path, request_id=request_id)
    if frame_paths:
        vision = await describe_from_vision(frame_paths, request_id)
    else:
        vision = VisionResult(description="Frame extraction failed", confidence=0.0)

    detected_language = _detect_language_from_transcript(partial_transcript)
    fallback = describe_from_transcript(
        partial_transcript=partial_transcript,
        duration_seconds=duration_seconds,
        filename=filename,
        detected_language=detected_language,
    )

    understanding = merge_understanding(vision, fallback)
    if not frame_paths and not _has_partial_transcript(fallback) and fallback.detected_language == "unknown":
        understanding = understanding.model_copy(update={"understanding_source": "metadata_only"})

    log_event(
        logger,
        "stage_complete",
        request_id=request_id,
        stage="video_understanding_merge",
        understanding_source=understanding.understanding_source,
        confidence=understanding.confidence,
    )
    return understanding
