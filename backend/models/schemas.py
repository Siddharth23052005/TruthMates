from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field


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


class SourceReference(BaseModel):
    """Represents a news source or reference website used during verification."""

    title: str = Field(..., description="Title or description of the source")
    url: str = Field(..., description="URL of the source website")
    source_type: str = Field(
        "web", description="Type: pinecone | google_fact_check | official | web"
    )
    similarity: Optional[float] = Field(
        None, description="Similarity score 0-1 if from evidence matching"
    )


class VideoUnderstanding(BaseModel):
    """Best-effort human-readable understanding of uploaded video content."""

    description: str
    visual_context: Optional[str] = None
    detected_language: str = "unknown"
    estimated_content_type: str = "UNKNOWN"
    visible_text: Optional[str] = None
    confidence: float = 0.0
    understanding_source: Literal[
        "vision+transcript",
        "vision_only",
        "transcript+metadata",
        "metadata_only",
    ] = "metadata_only"


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
    content_category: Optional[str] = Field(None, description="Classification category before verification")
    analysis_route: Optional[str] = Field(None, description="Verification route selected before evidence retrieval")
    misleading_reason: Optional[str] = Field(None, description="Specific reason the claim misleads when verdict is MISLEADING")
    source_weight_score: Optional[float] = Field(0.0, description="Weighted evidence score 0-100")
    countercheck_note: Optional[str] = Field(None, description="Result of contradiction check against strongest opposing evidence")
    verdict_hint: Optional[str] = Field(None, description="Precomputed verdict suggestion before final validation")


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
    overly_hedged_language: bool = False


class ValidatedPost(BaseModel):
    """Represents a validated output with final verdict."""

    claim: str
    analysis_key: str = Field(..., description="Stable composite identity for this analysis result")
    source_ref: Optional[str] = Field(None, description="Stable source reference used to build the analysis key")
    verdict: Literal[
        "SUPPORTED",
        "REFUTED",
        "MISLEADING",
        "UNVERIFIED",
        "OUT_OF_SCOPE",
        "SATIRE",
        "INSUFFICIENT_EVIDENCE",
    ]
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
    content_category: Optional[str] = Field(None, description="Media classification category before fact-checking")
    analysis_route: Optional[str] = Field(None, description="Route selected by the media classification gate")
    pipeline_status: Optional[str] = Field("complete", description="complete | short_circuit | partial_failure")
    pipeline_error: Optional[str] = Field(None, description="Error summary when a pipeline stage fails after input intake")
    misleading_reason: Optional[str] = Field(None, description="Specific explanation of how the content misleads, when applicable")
    verdict_reason: Optional[str] = Field(None, description="Human-style explanation for the final verdict")
    detailed_explanation: Optional[str] = Field(None, description="Thorough human-readable explanation of the claim analysis and findings")
    source_references: Optional[list[SourceReference]] = Field(None, description="List of news sources and websites used during verification")
    source_weight_score: Optional[float] = Field(0.0, description="Weighted evidence score 0-100")
    source_weight_summary: Optional[str] = Field(None, description="Short summary of the weighted evidence considered")
    countercheck_note: Optional[str] = Field(None, description="Summary of the strongest contradiction considered before final verdict")
    video_understanding: Optional[VideoUnderstanding] = Field(None, description="Best-effort description of uploaded video content")
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


class MonitorSummaryResponse(BaseModel):
    status: str
    total_validated: int
    verdict_counts: dict[str, int]
    monitor_status_counts: dict[str, int]
    average_trust_score: float
    timeline: list[dict]
