"""
API routes for the Social Media Monitor feature.

All endpoints are admin-protected and rate-limited.
Provides CRUD operations for monitor entries and crawl triggers.

The /crawl endpoint runs in the background so the frontend can poll
for new entries appearing one by one as they get analyzed.
"""

from __future__ import annotations

import asyncio
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from typing import Optional

from api.deps import limiter, require_admin_api_key
from core.config import get_settings
from core.logging import get_logger, log_event
from models.social_schemas import (
    CrawlResponse,
    MonitorEntryListResponse,
    ReviewRequest,
    SocialStatsResponse,
)
from services.social_monitor_service import (
    get_crawl_status,
    get_entry_by_id,
    get_monitor_entries,
    get_social_stats,
    run_crawl_background,
    update_entry_status,
)

logger = get_logger("truthmates.social_routes")

router = APIRouter(prefix="/social", tags=["Social Monitor"])


@router.post(
    "/crawl",
    dependencies=[Depends(require_admin_api_key)],
)
@limiter.limit(get_settings().admin_rate_limit)
async def trigger_crawl(
    request: Request,
    background_tasks: BackgroundTasks,
    keywords: list[str] = Query(
        default=["India government fake news", "PIB fact check", "modi scheme false"],
        description="Keywords to search for across platforms",
    ),
    platforms: Optional[list[str]] = Query(
        default=None,
        description="Platforms to crawl: twitter, youtube, reddit, instagram. Defaults to all.",
    ),
    max_posts: int = Query(default=50, le=50, description="Maximum posts to scrape (hard cap: 50)"),
):
    """
    Trigger a social media crawl in the background.

    Returns immediately with status "crawling". The frontend should poll
    /social/entries and /social/crawl-status to see posts appear one by one.
    """
    background_tasks.add_task(run_crawl_background, keywords, platforms, max_posts)
    return {"status": "crawling", "message": "Crawl started. Posts will appear as they are analyzed."}


@router.get(
    "/crawl-status",
    dependencies=[Depends(require_admin_api_key)],
)
@limiter.limit(get_settings().admin_rate_limit)
async def crawl_status(request: Request):
    """Check if a crawl is currently running and how many posts have been processed."""
    return get_crawl_status()


@router.get(
    "/entries",
    response_model=MonitorEntryListResponse,
    dependencies=[Depends(require_admin_api_key)],
)
@limiter.limit(get_settings().admin_rate_limit)
async def list_entries(
    request: Request,
    status: Optional[str] = Query(default=None, description="Filter by status: pending, analyzed, approved, rejected"),
    verdict: Optional[str] = Query(default=None, description="Filter by verdict: SUPPORTED, REFUTED, MISLEADING, etc."),
    platform: Optional[str] = Query(default=None, description="Filter by platform: twitter, youtube, reddit, instagram"),
    limit: int = Query(default=50, le=100, description="Max entries to return"),
    offset: int = Query(default=0, ge=0, description="Pagination offset"),
):
    """List monitor entries with optional filters."""
    entries = await get_monitor_entries(
        status=status,
        verdict=verdict,
        platform=platform,
        limit=limit,
        offset=offset,
    )
    return MonitorEntryListResponse(status="success", count=len(entries), entries=entries)


@router.get(
    "/entries/{entry_id}",
    dependencies=[Depends(require_admin_api_key)],
)
@limiter.limit(get_settings().admin_rate_limit)
async def get_entry(request: Request, entry_id: str):
    """Get a single monitor entry with full analysis details."""
    entry = await get_entry_by_id(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail=f"Entry {entry_id} not found")
    return {"status": "success", "entry": entry}


@router.post(
    "/entries/{entry_id}/review",
    dependencies=[Depends(require_admin_api_key)],
)
@limiter.limit(get_settings().admin_rate_limit)
async def review_entry(request: Request, entry_id: str, payload: ReviewRequest):
    """
    Moderator review action: approve or reject an entry.
    Optionally edit the suggested reply text and add a moderator note.
    """
    updated = await update_entry_status(
        entry_id=entry_id,
        action=payload.action,
        moderator_note=payload.moderator_note,
        edited_reply=payload.edited_reply,
    )
    if not updated:
        raise HTTPException(status_code=404, detail=f"Entry {entry_id} not found")
    return {"status": "success", "entry": updated}


@router.get(
    "/stats",
    response_model=SocialStatsResponse,
    dependencies=[Depends(require_admin_api_key)],
)
@limiter.limit(get_settings().admin_rate_limit)
async def get_stats(request: Request):
    """Dashboard statistics: totals by verdict, platform, and review status."""
    return await get_social_stats()
