from datetime import datetime
from typing import Optional
from pydantic import BaseModel, HttpUrl, Field


class CivicPost(BaseModel):
    """Represents a single civic post scraped from PIB or MyGov RSS feed."""

    title: str = Field(..., description="Headline of the civic post")
    description: str = Field(..., description="Body / summary text (HTML stripped)")
    link: str = Field(..., description="Canonical URL of the post")
    pub_date: Optional[str] = Field(None, description="Published date in ISO 8601 format")
    source: str = Field(..., description="Feed source name (PIB | MyGov)")
    scraped_at: Optional[datetime] = Field(
        default_factory=datetime.utcnow,
        description="UTC timestamp when this record was scraped",
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class ScrapeResponse(BaseModel):
    """FastAPI response schema for the /scrape endpoint."""

    status: str
    count: int
    posts: list[CivicPost]


class ClassifiedPost(CivicPost):
    """Represents a classified civic post with metadata."""

    label: str = Field(..., description="civic | non-civic")
    confidence: float = Field(..., description="Model confidence in label")
    language: str = Field(..., description="Detected language code")
    needs_review: bool = Field(
        ..., description="True if confidence below threshold"
    )


class ClassifyResponse(BaseModel):
    """FastAPI response schema for the /classify endpoint."""

    status: str
    count: int
    posts: list[ClassifiedPost]


class EvidenceMatch(BaseModel):
    """Represents a matched fact for a claim."""

    fact_text: str = Field(..., description="Matched fact text")
    similarity: float = Field(..., description="Similarity score 0-1")
    source_url: str = Field(..., description="Source URL for the fact")
    source_type: str = Field(..., description="pinecone | google_fact_check")


class VerifiedPost(ClassifiedPost):
    """Represents a verified post with evidence matches."""

    verification_label: str = Field(..., description="verified | unverified")
    matches: list[EvidenceMatch]
    crowdsource_reports: Optional[float] = Field(
        0.0, description="Crowdsource reports score 0-1"
    )
    deepfake_score: Optional[float] = Field(
        0.0, description="Deepfake score 0-1"
    )


class VerifyResponse(BaseModel):
    """FastAPI response schema for the /verify endpoint."""

    status: str
    count: int
    posts: list[VerifiedPost]


class CounterInfoPost(VerifiedPost):
    """Represents a counter-info post with corrections and trust score."""

    correction_en: str = Field(..., description="Plain language correction")
    correction_hi: str = Field(..., description="Hindi translation of correction")
    trust_score: float = Field(..., description="Trust score 0-100")
    trust_label: str = Field(..., description="Red | Yellow | Green")


class GenerateResponse(BaseModel):
    """FastAPI response schema for the /generate endpoint."""

    status: str
    count: int
    posts: list[CounterInfoPost]


class ValidationFlags(BaseModel):
    """Flags produced by the output validator."""

    contradicts_pib_fact: bool
    invalid_source_url: bool
    trust_score_mismatch: bool
    missing_hindi: bool
    hallucinated_stats: bool


class ValidatedPost(BaseModel):
    """Represents a validated output with final verdict."""

    claim: str
    verdict: str
    trust_score: float
    counter_english: str
    counter_hindi: str
    sources: list[str]
    flags: ValidationFlags
    # Real analysis metrics (0-100 scale)
    llm_confidence: Optional[float] = Field(0.0, description="LLM confidence percentage 0-100")
    source_match: Optional[float] = Field(0.0, description="Best source similarity percentage 0-100")
    source_found: Optional[float] = Field(0.0, description="Whether an official source was found 0 or 100")
    deepfake_score: Optional[float] = Field(0.0, description="Deepfake detection score 0-100")
    crowd_reports: Optional[float] = Field(0.0, description="Crowdsource reports score 0-100")
    input_type: Optional[str] = Field("text", description="Input type: text | video | audio")
    content_summary: Optional[str] = Field(None, description="Short summary of the input content")
    video_title: Optional[str] = Field(None, description="Video title if input was video/audio")
    video_url: Optional[str] = Field(None, description="Video URL if input was video")
    validated_at: Optional[datetime] = Field(
        default_factory=datetime.utcnow,
        description="UTC timestamp when this record was validated",
    )


class ValidateResponse(BaseModel):
    """FastAPI response schema for the /validate endpoint."""

    status: str
    count: int
    posts: list[ValidatedPost]


class MonitorLog(BaseModel):
    """Represents a single monitoring decision entry."""

    id: Optional[str] = None
    agent_name: str
    input: str
    output: str
    status: str
    retries: int
    checks: Optional[dict] = None
    timestamp: datetime


class MonitorLogsResponse(BaseModel):
    """Response schema for monitor logs endpoint."""

    status: str
    count: int
    logs: list[MonitorLog]
