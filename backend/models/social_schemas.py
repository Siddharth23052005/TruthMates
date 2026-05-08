"""
Schemas for the Social Media Monitor feature.

Covers scraped posts, human-style analysis results, monitor entries,
crawl configuration, and API response contracts.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class ScrapedSocialPost(BaseModel):
    """A single post scraped from a social media platform."""

    platform: str = Field(..., description="twitter | youtube | reddit | instagram")
    post_id: str = Field(..., description="Platform-specific unique post identifier")
    author_handle: str = Field("", description="@username or channel name")
    author_name: str = Field("", description="Display name of the author")
    content: str = Field(..., description="Full text content of the post")
    post_url: str = Field("", description="Direct URL to the original post")
    posted_at: Optional[datetime] = Field(None, description="When the post was originally published")
    engagement: Optional[dict] = Field(
        default_factory=dict,
        description="Engagement metrics: likes, retweets/shares, replies, views",
    )
    scraped_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when this post was scraped",
    )
    media_urls: list[str] = Field(default_factory=list, description="URLs of attached images/videos")


class HumanStyleAnalysis(BaseModel):
    """Analysis structured the way a human fact-checker would reason through a post."""

    critical_thinking: str = Field(
        ...,
        description="What a critical thinker would notice about this post — red flags, missing context, logical issues",
    )
    evidence_summary: str = Field(
        ...,
        description="What the evidence says — bullet-point summary of retrieved facts",
    )
    correct_information: str = Field(
        ...,
        description="What is actually correct — the truth in plain language",
    )
    sources: list[str] = Field(default_factory=list, description="Evidence source URLs")
    verdict: str = Field(
        ...,
        description="SUPPORTED | REFUTED | MISLEADING | UNVERIFIED | OUT_OF_SCOPE | SATIRE | INSUFFICIENT_EVIDENCE",
    )
    trust_score: float = Field(0.0, description="Trust score 0-100")
    is_misleading: bool = Field(False, description="Final boolean — is this post actually misleading?")
    confidence: float = Field(0.0, description="Analysis confidence percentage 0-100")


class MonitorEntry(BaseModel):
    """A scraped post paired with its TruthMates analysis, ready for moderator review."""

    entry_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique entry identifier")
    post: ScrapedSocialPost
    analysis: Optional[HumanStyleAnalysis] = None
    status: Literal["pending", "analyzed", "approved", "rejected"] = "pending"
    suggested_reply: Optional[str] = Field(None, description="AI-generated correction text for the post")
    moderator_note: Optional[str] = Field(None, description="Note from the human moderator")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When this entry was created",
    )
    reviewed_at: Optional[datetime] = Field(None, description="When the moderator reviewed this entry")


class CrawlConfig(BaseModel):
    """Configuration for a social media crawl target."""

    platform: str = Field("twitter", description="Platform to crawl: twitter | youtube | reddit | instagram")
    keywords: list[str] = Field(default_factory=list, description="Search terms to monitor")
    accounts: list[str] = Field(default_factory=list, description="Specific accounts to monitor")
    max_posts_per_crawl: int = Field(50, description="Maximum posts to scrape per crawl run")
    enabled: bool = Field(True, description="Whether this crawl target is active")


# ── API Response Schemas ─────────────────────────────────────────────────────


class SocialStatsResponse(BaseModel):
    """Dashboard statistics."""

    total_scraped: int = 0
    total_misleading: int = 0
    total_accurate: int = 0
    total_unverified: int = 0
    pending_review: int = 0
    approved: int = 0
    rejected: int = 0
    by_platform: dict[str, int] = Field(default_factory=dict)


class MonitorEntryListResponse(BaseModel):
    """Paginated list of monitor entries."""

    status: str = "success"
    count: int = 0
    entries: list[MonitorEntry] = Field(default_factory=list)


class CrawlResponse(BaseModel):
    """Response from a crawl trigger."""

    status: str = "success"
    crawled: int = 0
    analyzed: int = 0
    flagged: int = 0
    errors: list[str] = Field(default_factory=list)


class ReviewRequest(BaseModel):
    """Moderator review action."""

    action: Literal["approved", "rejected"]
    moderator_note: Optional[str] = None
    edited_reply: Optional[str] = None
