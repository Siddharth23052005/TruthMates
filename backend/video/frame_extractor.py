from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from core.logging import get_logger, log_event, stage_duration_ms, stage_start

logger = get_logger("truthmates.video.frame_extractor")

_TARGET_FRAME_COUNT = 5
_FRAME_PERCENTILES = (0.10, 0.25, 0.50, 0.75, 0.90)
_VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".m4v", ".avi"}


def _probe_duration(video_path: str) -> float | None:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_entries",
        "format=duration",
        video_path,
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return None
    try:
        payload = json.loads(result.stdout or "{}")
        duration = float(payload.get("format", {}).get("duration") or 0.0)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    return duration if duration > 0 else None


def _frame_targets(duration_seconds: float) -> list[float]:
    if duration_seconds <= 0:
        return [0.0]
    if duration_seconds < 5:
        frame_count = max(1, min(_TARGET_FRAME_COUNT, int(duration_seconds)))
        if frame_count == 1:
            return [duration_seconds / 2]
        spacing = duration_seconds / (frame_count + 1)
        return [spacing * index for index in range(1, frame_count + 1)]
    return [duration_seconds * pct for pct in _FRAME_PERCENTILES]


def _video_directory_path(video_path: str) -> Path:
    path = Path(video_path)
    return path.parent if path.suffix.lower() in _VIDEO_EXTENSIONS else path.parent


def extract_keyframes(video_path: str, *, request_id: str | None = None) -> list[str]:
    started = stage_start()

    if not video_path or not os.path.isfile(video_path):
        log_event(
            logger,
            "stage_failed",
            level="warning",
            request_id=request_id,
            stage="video_frame_extraction",
            error=f"Video file not found: {video_path}",
        )
        return []

    duration_seconds = _probe_duration(video_path)
    if duration_seconds is None:
        log_event(
            logger,
            "stage_failed",
            level="warning",
            request_id=request_id,
            stage="video_frame_extraction",
            error="Could not determine video duration with ffprobe.",
        )
        return []

    output_dir = _video_directory_path(video_path)
    frame_paths: list[str] = []

    try:
        for index, timestamp in enumerate(_frame_targets(duration_seconds), start=1):
            frame_path = output_dir / f"keyframe_{index}.jpg"
            command = [
                "ffmpeg",
                "-y",
                "-ss",
                f"{timestamp:.3f}",
                "-i",
                video_path,
                "-frames:v",
                "1",
                "-q:v",
                "2",
                str(frame_path),
            ]
            result = subprocess.run(command, capture_output=True, text=True, check=False)
            if result.returncode == 0 and frame_path.is_file():
                frame_paths.append(str(frame_path))
        log_event(
            logger,
            "stage_complete",
            request_id=request_id,
            stage="video_frame_extraction",
            duration_ms=stage_duration_ms(started),
            frame_count=len(frame_paths),
            duration_seconds=round(duration_seconds, 2),
        )
        return frame_paths
    except OSError as exc:
        log_event(
            logger,
            "stage_failed",
            level="warning",
            request_id=request_id,
            stage="video_frame_extraction",
            error=str(exc),
        )
        return []
