from __future__ import annotations

import types
import sys
from pathlib import Path

import pytest


BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from models.schemas import VideoUnderstanding  # noqa: E402
from services import media_pipeline_service  # noqa: E402
from services.video_understanding_service import (  # noqa: E402
    TranscriptResult,
    VisionResult,
    describe_from_transcript,
    merge_understanding,
    understand_video,
)


def test_merge_understanding_returns_vision_only_without_transcript():
    vision = VisionResult(
        description="A speaker at a podium in a press room.",
        content_type="GOVERNMENT_SPEECH",
        setting="indoor press room",
        detected_language="en",
        confidence=0.9,
    )
    fallback = TranscriptResult(
        description="Video of 12 seconds with no detectable speech",
        detected_language="unknown",
        confidence=0.05,
    )

    result = merge_understanding(vision, fallback)

    assert result.understanding_source == "vision_only"
    assert result.description == "A speaker at a podium in a press room."


def test_merge_understanding_returns_vision_plus_transcript_when_partial_speech_exists():
    vision = VisionResult(
        description="A street interview with banners visible in the background.",
        content_type="NEWS_REPORT",
        visible_text="Breaking News",
        setting="outdoor street",
        detected_language="en",
        confidence=0.82,
    )
    fallback = TranscriptResult(
        description="Partial speech detected: prices are rising across the city center",
        detected_language="en",
        confidence=0.2,
    )

    result = merge_understanding(vision, fallback)

    assert result.understanding_source == "vision+transcript"
    assert "Supporting transcript note" in result.description


def test_merge_understanding_returns_transcript_metadata_when_vision_low_confidence():
    vision = VisionResult(
        description="Blurry stage footage.",
        content_type="UNKNOWN",
        confidence=0.2,
    )
    fallback = TranscriptResult(
        description="Partial speech detected: this is a five word sample transcript",
        detected_language="en",
        confidence=0.2,
    )

    result = merge_understanding(vision, fallback)

    assert result.understanding_source == "transcript+metadata"
    assert result.description.startswith("Partial speech detected:")
    assert result.estimated_content_type == "UNKNOWN"


def test_describe_from_transcript_uses_partial_speech_prefix():
    result = describe_from_transcript(
        partial_transcript="one two three four five six seven",
        duration_seconds=18,
        filename="demo.mp4",
        detected_language="en",
    )

    assert result.description == "Partial speech detected: one two three four five six seven"
    assert result.confidence == 0.2


def test_describe_from_transcript_uses_language_fallback():
    result = describe_from_transcript(
        partial_transcript=None,
        duration_seconds=11,
        filename="demo.mp4",
        detected_language="hi",
    )

    assert result.description == "Video in hi with no extractable speech content"
    assert result.detected_language == "hi"


def test_describe_from_transcript_uses_duration_fallback():
    result = describe_from_transcript(
        partial_transcript=None,
        duration_seconds=9,
        filename="demo.mp4",
        detected_language=None,
    )

    assert result.description == "Video of 9 seconds with no detectable speech"
    assert result.detected_language == "unknown"


@pytest.mark.asyncio
async def test_understand_video_attaches_understanding_when_no_frames(monkeypatch):
    monkeypatch.setattr(
        "services.video_understanding_service.extract_keyframes",
        lambda _video_path, request_id=None: [],
    )

    result = await understand_video(
        video_path="demo.mp4",
        partial_transcript="",
        duration_seconds=6,
        filename="demo.mp4",
        request_id="req-1",
    )

    assert isinstance(result, VideoUnderstanding)
    assert result.understanding_source == "metadata_only"
    assert "no detectable speech" in result.description


@pytest.mark.asyncio
async def test_media_pipeline_returns_partial_failure_with_video_understanding(monkeypatch):
    async def fake_understand_video(*args, **kwargs):
        return VideoUnderstanding(
            description="A short clip showing a person speaking indoors.",
            visual_context="indoor room",
            detected_language="en",
            estimated_content_type="PERSONAL",
            confidence=0.55,
            understanding_source="vision+transcript",
        )

    async def fake_save(_posts):
        return None

    fake_extractor = types.ModuleType("video.extractor")
    fake_extractor.validate_url = lambda url: url
    fake_extractor.extract_video_artifacts = lambda url, validate=False: {
        "temp_dir": None,
        "video_path": "demo.mp4",
        "audio_path": "demo.wav",
        "transcript": "too short to verify",
        "language": "en",
        "title": "Demo title",
        "duration_seconds": 12,
        "language_warning": None,
        "word_count": 4,
        "transcript_valid": False,
        "transcript_validation_error": "Could not extract meaningful speech from this video. Only 4 words detected (minimum: 30).",
        "transcript_error": None,
    }
    fake_extractor.cleanup_artifacts = lambda _temp_dir: None
    fake_analyzer = types.ModuleType("video.analyzer")
    fake_analyzer.run_video_analysis_crew = lambda transcript: (_ for _ in ()).throw(RuntimeError("should not be called"))

    monkeypatch.setitem(sys.modules, "video.extractor", fake_extractor)
    monkeypatch.setitem(sys.modules, "video.analyzer", fake_analyzer)
    monkeypatch.setattr("services.media_pipeline_service.understand_video", fake_understand_video)
    monkeypatch.setattr("services.media_pipeline_service.save_validated_posts", fake_save)

    response = await media_pipeline_service.analyze_video_url("https://example.com/video", request_id="req-2")

    assert response.status == "partial_failure"
    assert response.posts[0].verdict == "INSUFFICIENT_EVIDENCE"
    assert response.posts[0].pipeline_status == "partial_failure"
    assert response.posts[0].pipeline_error == "Not enough speech to verify claims. Minimum 30 words required."
    assert response.posts[0].video_understanding is not None
    assert response.posts[0].video_understanding.description == "A short clip showing a person speaking indoors."
