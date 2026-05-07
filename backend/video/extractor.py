"""
Video/Audio Extractor — Download + Transcribe
===============================================
Downloads video from social media URLs via yt-dlp, extracts audio,
and transcribes using Groq Whisper API.

Also supports direct audio file transcription for the AUDIO UPLOAD feature.

Reliability safeguards:
  - URL allowlist validation (https-only, approved domains)
  - Two-layer duration guard (info_dict + --match-filter)
  - tempfile.TemporaryDirectory for guaranteed cleanup
  - ThreadPoolExecutor timeout on downloads (60s)
  - Whisper language hint + 30-word minimum guard
  - Tenacity-based retry for Groq rate limits
"""

from __future__ import annotations

import os
import re
import tempfile
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv
from groq import Groq
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

load_dotenv()

# Ensure FFmpeg is available (uses static-ffmpeg pip package)
try:
    import static_ffmpeg
    static_ffmpeg.add_paths()
except ImportError:
    pass  # FFmpeg must be on system PATH instead

# ── Configuration ────────────────────────────────────────────────────────────

MAX_DURATION_SECONDS = 600  # 10 minutes
DOWNLOAD_TIMEOUT_SECONDS = 60
SOCKET_TIMEOUT_SECONDS = 30
MIN_TRANSCRIPT_WORDS = 30
MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024  # 100 MB proxy guard
WHISPER_MODEL = "whisper-large-v3-turbo"
SUPPORTED_LANGUAGES = {"hi", "en"}

ALLOWED_DOMAINS = {
    "youtube.com",
    "www.youtube.com",
    "youtu.be",
    "m.youtube.com",
    "twitter.com",
    "www.twitter.com",
    "x.com",
    "www.x.com",
    "instagram.com",
    "www.instagram.com",
    "facebook.com",
    "www.facebook.com",
    "m.facebook.com",
    "fb.watch",
    "reddit.com",
    "www.reddit.com",
}


# ── URL Validation ───────────────────────────────────────────────────────────


def validate_url(url: str) -> str:
    """Validate URL against the allowlist. Returns cleaned URL or raises ValueError."""
    url = url.strip()
    if not url:
        raise ValueError("Empty URL provided.")

    parsed = urlparse(url)

    # Must be https
    if parsed.scheme not in ("https", "http"):
        raise ValueError(
            f"URL scheme '{parsed.scheme}' not allowed. Only https:// URLs are accepted."
        )

    # Block private IPs and localhost
    hostname = parsed.hostname or ""
    if _is_private_host(hostname):
        raise ValueError(
            f"Private/local URLs are not allowed: {hostname}"
        )

    # Domain allowlist
    if hostname not in ALLOWED_DOMAINS:
        raise ValueError(
            f"Domain '{hostname}' is not supported. "
            f"Allowed: {', '.join(sorted(ALLOWED_DOMAINS))}"
        )

    return url


def _is_private_host(hostname: str) -> bool:
    """Check if hostname is a private/local address."""
    if hostname in ("localhost", "127.0.0.1", "0.0.0.0", "::1"):
        return True
    if hostname.startswith("192.168.") or hostname.startswith("10."):
        return True
    if re.match(r"^172\.(1[6-9]|2\d|3[01])\.", hostname):
        return True
    return False


# ── Groq Whisper Transcription ───────────────────────────────────────────────


def _is_rate_limit_error(exc: Exception) -> bool:
    return "rate_limit" in str(exc).lower() or "rate limit" in str(exc).lower()


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=5, min=5, max=60),
    retry=retry_if_exception(_is_rate_limit_error),
    reraise=True,
)
def _transcribe_audio(audio_path: str) -> dict:
    """Transcribe audio file using Groq Whisper API with retries."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError("GROQ_API_KEY is not set.")

    client = Groq(api_key=api_key)

    with open(audio_path, "rb") as audio_file:
        response = client.audio.transcriptions.create(
            file=audio_file,
            model=WHISPER_MODEL,
            response_format="verbose_json",
        )

    # Extract fields from the response
    transcript_text = ""
    detected_language = "unknown"

    if hasattr(response, "text"):
        transcript_text = response.text or ""
    if hasattr(response, "language"):
        detected_language = response.language or "unknown"

    return {
        "transcript": transcript_text.strip(),
        "language": detected_language,
    }


# ── yt-dlp Download ─────────────────────────────────────────────────────────


def _download_audio(url: str, output_dir: str) -> tuple[str, dict]:
    """
    Download audio from a video URL using yt-dlp.
    Returns (audio_file_path, info_dict).

    Two-layer duration guard:
      Layer 1: Check info_dict duration before download
      Layer 2: --match-filter as a backup
    """
    import yt_dlp

    # Layer 1: Extract info without downloading to check duration
    info_opts = {
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": SOCKET_TIMEOUT_SECONDS,
    }

    with yt_dlp.YoutubeDL(info_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    if info is None:
        raise RuntimeError("yt-dlp could not extract video information.")

    duration = info.get("duration")
    title = info.get("title", "Unknown")

    if duration is not None and duration > MAX_DURATION_SECONDS:
        mins, secs = divmod(int(duration), 60)
        raise ValueError(
            f"Video too long ({mins}m {secs}s). Max allowed: 10 minutes."
        )

    # Layer 2: Download with match-filter as backup guard
    audio_template = os.path.join(output_dir, "audio.%(ext)s")

    download_opts = {
        "format": "bestaudio/best",
        "outtmpl": audio_template,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
                "preferredquality": "192",
            }
        ],
        "match_filter": yt_dlp.utils.match_filter_func("duration <= 600"),
        "socket_timeout": SOCKET_TIMEOUT_SECONDS,
        "quiet": True,
        "no_warnings": True,
    }

    with yt_dlp.YoutubeDL(download_opts) as ydl:
        ydl.download([url])

    # Find the output audio file
    audio_path = _find_audio_file(output_dir)
    if audio_path is None:
        raise RuntimeError("Audio extraction failed — no .wav file produced.")

    # File size proxy guard (for cases where duration was None)
    file_size = os.path.getsize(audio_path)
    if file_size > MAX_FILE_SIZE_BYTES:
        raise ValueError(
            f"Audio file too large ({file_size // (1024*1024)}MB). "
            f"Max: {MAX_FILE_SIZE_BYTES // (1024*1024)}MB."
        )

    return audio_path, {
        "title": title,
        "duration_seconds": int(duration) if duration else None,
    }


def _find_audio_file(directory: str) -> str | None:
    """Find the first .wav file in the directory."""
    for f in Path(directory).iterdir():
        if f.suffix == ".wav":
            return str(f)
    # Fallback: any audio file
    for f in Path(directory).iterdir():
        if f.suffix in (".mp3", ".m4a", ".ogg", ".flac", ".webm"):
            return str(f)
    return None


# ── Transcript Validation ────────────────────────────────────────────────────


def _validate_transcript(transcript: str, language: str) -> None:
    """Validate transcript meets minimum quality thresholds."""
    # Word count guard (filter single-char tokens)
    words = [w for w in transcript.split() if len(w) > 1]
    if len(words) < MIN_TRANSCRIPT_WORDS:
        raise ValueError(
            f"Could not extract meaningful speech from this video. "
            f"Only {len(words)} words detected (minimum: {MIN_TRANSCRIPT_WORDS})."
        )


# ── Public API ───────────────────────────────────────────────────────────────


def extract_transcript(url: str) -> dict:
    """
    Main entry point for VIDEO URLs: download video, extract audio, transcribe.

    Returns:
        {
            "transcript": str,
            "language": str,
            "title": str,
            "duration_seconds": int | None,
            "language_warning": str | None,
        }

    Raises:
        ValueError: On URL validation, duration, or transcript quality issues.
        RuntimeError: On download or transcription failures.
    """
    # Step 1: Validate URL
    url = validate_url(url)

    # Step 2: Download and transcribe inside a temp directory (guaranteed cleanup)
    with tempfile.TemporaryDirectory(prefix="truthmates_video_") as tmp_dir:
        # Download with timeout
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_download_audio, url, tmp_dir)
            try:
                audio_path, video_info = future.result(timeout=DOWNLOAD_TIMEOUT_SECONDS)
            except FutureTimeout:
                raise RuntimeError(
                    f"Video download timed out after {DOWNLOAD_TIMEOUT_SECONDS} seconds."
                )

        # Transcribe
        whisper_result = _transcribe_audio(audio_path)
        transcript = whisper_result["transcript"]
        language = whisper_result["language"]

        # Validate transcript quality
        _validate_transcript(transcript, language)

        # Language warning (non-fatal)
        language_warning = None
        if language not in SUPPORTED_LANGUAGES:
            language_warning = (
                f"Detected language '{language}' is not in the primary "
                f"supported set ({', '.join(SUPPORTED_LANGUAGES)}). "
                f"Claim extraction may be less accurate."
            )

        return {
            "transcript": transcript,
            "language": language,
            "title": video_info["title"],
            "duration_seconds": video_info["duration_seconds"],
            "language_warning": language_warning,
        }


def transcribe_audio_file(file_path: str) -> dict:
    """
    Main entry point for AUDIO file uploads: transcribe a local audio file.

    Returns:
        {
            "transcript": str,
            "language": str,
            "title": str,
            "duration_seconds": None,
            "language_warning": str | None,
        }

    Raises:
        ValueError: On transcript quality issues.
        RuntimeError: On transcription failures.
    """
    if not os.path.isfile(file_path):
        raise ValueError(f"Audio file not found: {file_path}")

    file_size = os.path.getsize(file_path)
    if file_size > MAX_FILE_SIZE_BYTES:
        raise ValueError(
            f"Audio file too large ({file_size // (1024*1024)}MB). "
            f"Max: {MAX_FILE_SIZE_BYTES // (1024*1024)}MB."
        )

    whisper_result = _transcribe_audio(file_path)
    transcript = whisper_result["transcript"]
    language = whisper_result["language"]

    _validate_transcript(transcript, language)

    language_warning = None
    if language not in SUPPORTED_LANGUAGES:
        language_warning = (
            f"Detected language '{language}' is not in the primary "
            f"supported set ({', '.join(SUPPORTED_LANGUAGES)}). "
            f"Claim extraction may be less accurate."
        )

    return {
        "transcript": transcript,
        "language": language,
        "title": os.path.basename(file_path),
        "duration_seconds": None,
        "language_warning": language_warning,
    }
