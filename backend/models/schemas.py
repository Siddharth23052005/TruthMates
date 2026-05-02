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
