"""
Video Analysis Module
=====================
Public API for video/audio extraction, transcription, and claim analysis.

Usage:
    from video.extractor import extract_transcript, transcribe_audio_file
    from video.analyzer import run_video_analysis_crew
    from video.schemas import PoCReport, VerifiedClaim

All imports are lazy — the heavy dependencies (sentence_transformers,
yt-dlp, etc.) only load when the functions are actually called.
"""
