"""
Video/Audio Analysis Schemas — Pydantic Data Contracts
=======================================================
Defines strict schemas for all inter-agent communication and final output.
Every agent output is validated against these models before being passed
downstream — no raw LLM strings cross component boundaries.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from models.schemas import VideoUnderstanding


# ── Agent 1: Video Analyst Output ────────────────────────────────────────────


class ExtractedClaim(BaseModel):
    """A single government-related claim extracted from the transcript."""

    claim_text: str = Field(
        ..., description="The specific claim made in the video."
    )
    misleading_aspect: str = Field(
        ..., description="What kind of misinformation this claim represents."
    )


class VideoAnalysisOutput(BaseModel):
    """Validated output from the Video Analyst agent."""

    summary: str = Field(
        ..., description="2-3 sentence description of the video content."
    )
    claims: list[ExtractedClaim] = Field(
        ..., min_length=1, description="Extracted government-related claims."
    )


# ── Agent 2: Fact Checker Output ─────────────────────────────────────────────


class FactCheckMatch(BaseModel):
    """A single evidence match from Pinecone or Google Fact Check."""

    fact_text: str = Field(..., description="The verified fact text.")
    similarity: float = Field(
        ..., ge=0.0, le=1.0, description="Cosine similarity score."
    )
    source_url: str = Field(default="", description="URL of the source.")
    source_type: Literal["pinecone", "google_fact_check"] = Field(
        ..., description="Which retrieval system found this match."
    )


class VerifiedClaim(BaseModel):
    """A claim after fact-checking with verification results."""

    claim_text: str
    misleading_aspect: str
    verification_label: Literal["verified", "unverified", "source_unavailable"] = Field(
        ..., description="verified=matched, unverified=no match, source_unavailable=API error."
    )
    matches: list[FactCheckMatch] = Field(default_factory=list)
    correction: str = Field(
        ..., description="Plain-language correction with cited source."
    )


# ── Final Output ─────────────────────────────────────────────────────────────


class VideoInfo(BaseModel):
    """Metadata about the processed video."""

    url: str
    title: str = "Unknown"
    duration_seconds: Optional[int] = None


class PoCReport(BaseModel):
    """Successful analysis run output."""

    status: Literal["success"] = "success"
    video: VideoInfo
    summary: str
    claims: list[VerifiedClaim]
    video_understanding: Optional[VideoUnderstanding] = None


class PoCError(BaseModel):
    """Failed analysis run output."""

    status: Literal["error"] = "error"
    error: str
    video_url: str = ""
