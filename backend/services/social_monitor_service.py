"""
Social Monitor orchestration service.

Connects scraping → existing TruthMates analysis pipeline → human-style analysis → persistence.
Each scraped post is verified through the full pipeline to determine if it's actually misleading.
Results are persisted for the moderator dashboard.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Optional

from core.logging import get_logger, log_event, stage_duration_ms, stage_start
from db.mongo import get_db
from models.social_schemas import (
    CrawlConfig,
    CrawlResponse,
    HumanStyleAnalysis,
    MonitorEntry,
    ScrapedSocialPost,
    SocialStatsResponse,
)
from services.social_scraping_service import crawl_all_platforms

logger = get_logger("truthmates.social_monitor")

_MAX_POSTS = 50

# ── Crawl state (in-memory, single-instance) ────────────────────────────────

_crawl_state: dict = {
    "is_running": False,
    "total_scraped": 0,
    "analyzed": 0,
    "flagged": 0,
    "current_post": "",
    "errors": [],
}


def get_crawl_status() -> dict:
    """Return the current crawl state for polling."""
    return {**_crawl_state}


async def run_crawl_background(
    keywords: list[str],
    platforms: list[str] | None = None,
    max_posts: int = _MAX_POSTS,
) -> None:
    """
    Background crawl runner. Saves each entry to MongoDB immediately
    after analysis so the frontend sees posts appear one by one.
    """
    global _crawl_state

    if _crawl_state["is_running"]:
        return

    _crawl_state.update({
        "is_running": True,
        "total_scraped": 0,
        "analyzed": 0,
        "flagged": 0,
        "current_post": "Starting crawl...",
        "errors": [],
    })

    try:
        if not keywords:
            keywords = [
                "India government policy fake",
                "PIB fact check",
                "modi scheme false",
                "aadhaar scam",
                "UPI fraud news",
            ]

        # 1. Scrape all platforms
        _crawl_state["current_post"] = "Scraping platforms..."
        log_event(logger, "bg_crawl_started", platforms=platforms or "all", keywords=keywords)
        raw_posts = await crawl_all_platforms(keywords, platforms=platforms, max_posts=max_posts)
        _crawl_state["total_scraped"] = len(raw_posts)

        if not raw_posts:
            _crawl_state["current_post"] = "No posts found"
            _crawl_state["is_running"] = False
            return

        # 2. Filter seen posts
        _crawl_state["current_post"] = "Filtering duplicates..."
        new_posts = await _filter_seen_posts(raw_posts)

        if not new_posts:
            _crawl_state["current_post"] = "All posts already seen"
            _crawl_state["is_running"] = False
            return

        # 3. Analyze one by one — save immediately after each
        for i, post in enumerate(new_posts[:_MAX_POSTS]):
            _crawl_state["current_post"] = f"Analyzing {i + 1}/{len(new_posts)}: {post.content[:60]}..."
            try:
                entry = await analyze_single_post(post)
                await save_monitor_entry(entry)
                _crawl_state["analyzed"] = i + 1
                if entry.analysis and entry.analysis.is_misleading:
                    _crawl_state["flagged"] += 1
            except Exception as exc:
                _crawl_state["errors"].append(str(exc)[:100])
                log_event(logger, "bg_post_error", post_id=post.post_id, error=str(exc))

        _crawl_state["current_post"] = "Crawl complete"
        log_event(
            logger, "bg_crawl_complete",
            total=_crawl_state["total_scraped"],
            analyzed=_crawl_state["analyzed"],
            flagged=_crawl_state["flagged"],
        )
    except Exception as exc:
        _crawl_state["current_post"] = f"Crawl failed: {str(exc)[:100]}"
        _crawl_state["errors"].append(str(exc)[:200])
        log_event(logger, "bg_crawl_failed", error=str(exc))
    finally:
        _crawl_state["is_running"] = False


# ── Analysis helpers ─────────────────────────────────────────────────────────


def _build_human_analysis(pipeline_result) -> HumanStyleAnalysis:
    """
    Convert a TruthMates ValidateResponse into a human-style analysis.
    Extracts the reasoning into sections that read like a human fact-checker.
    """
    if not pipeline_result or not hasattr(pipeline_result, "posts") or not pipeline_result.posts:
        return HumanStyleAnalysis(
            critical_thinking="Unable to analyze this post — the analysis pipeline returned no results.",
            evidence_summary="No evidence was retrieved.",
            correct_information="Could not determine the correct information.",
            sources=[],
            verdict="UNVERIFIED",
            trust_score=0.0,
            is_misleading=False,
            confidence=0.0,
        )

    post = pipeline_result.posts[0]

    # Build critical thinking section
    critical_thinking = ""
    if post.verdict_reason:
        critical_thinking = post.verdict_reason
    elif post.content_category:
        critical_thinking = f"This post was classified as '{post.content_category}'. "
        if post.analysis_route:
            critical_thinking += f"Analysis route: {post.analysis_route}. "

    if post.misleading_reason:
        critical_thinking += f"\n\nKey concern: {post.misleading_reason}"

    if post.countercheck_note:
        critical_thinking += f"\n\nContradiction check: {post.countercheck_note}"

    if not critical_thinking:
        if post.verdict in ("REFUTED", "MISLEADING"):
            critical_thinking = (
                "This claim makes specific factual assertions that can be verified against official sources. "
                "The evidence retrieved contradicts the claims made in this post."
            )
        elif post.verdict == "SUPPORTED":
            critical_thinking = (
                "This claim aligns with information from official and trusted sources. "
                "No contradicting evidence was found."
            )
        else:
            critical_thinking = (
                "This claim could not be conclusively verified. "
                "Insufficient evidence was available from trusted sources."
            )

    # Build evidence summary
    evidence_parts = []
    if post.source_weight_summary:
        evidence_parts.append(post.source_weight_summary)
    if post.sources:
        for src in post.sources[:5]:
            evidence_parts.append(f"• Source: {src}")
    if post.source_match and post.source_match > 0:
        evidence_parts.append(f"• Best source similarity: {post.source_match:.0f}%")
    if post.llm_confidence and post.llm_confidence > 0:
        evidence_parts.append(f"• AI confidence in analysis: {post.llm_confidence:.0f}%")

    evidence_summary = "\n".join(evidence_parts) if evidence_parts else "No matching evidence was found in trusted databases."

    # Build correct information
    correct_info = ""
    if post.counter_english:
        correct_info = post.counter_english
    elif post.verdict == "SUPPORTED":
        correct_info = "This post appears to contain accurate information based on available evidence."
    elif post.verdict in ("REFUTED", "MISLEADING"):
        correct_info = "The claims in this post are contradicted by official sources."
    else:
        correct_info = "Insufficient evidence to determine the correct information."

    is_misleading = post.verdict in ("REFUTED", "MISLEADING")

    return HumanStyleAnalysis(
        critical_thinking=critical_thinking,
        evidence_summary=evidence_summary,
        correct_information=correct_info,
        sources=post.sources or [],
        verdict=post.verdict,
        trust_score=post.trust_score,
        is_misleading=is_misleading,
        confidence=post.llm_confidence or 0.0,
    )


# ── Core orchestration ───────────────────────────────────────────────────────


async def analyze_single_post(post: ScrapedSocialPost) -> MonitorEntry:
    """
    Run a single scraped post through the TruthMates analysis pipeline.
    Returns a MonitorEntry with human-style analysis.
    """
    from services.pipeline_service import analyze_claim

    entry = MonitorEntry(post=post, status="pending")

    try:
        result = await analyze_claim(
            post.content,
            source_ref=post.post_url or post.post_id,
        )
        analysis = _build_human_analysis(result)

        # Build suggested reply only for misleading posts
        suggested_reply = None
        if analysis.is_misleading:
            suggested_reply = (
                f"⚠️ Fact Check: {analysis.correct_information}\n\n"
                f"Sources: {', '.join(analysis.sources[:3]) if analysis.sources else 'Official government records'}"
            )

        entry = MonitorEntry(
            post=post,
            analysis=analysis,
            status="analyzed",
            suggested_reply=suggested_reply,
        )
    except Exception as exc:
        log_event(
            logger, "post_analysis_failed",
            platform=post.platform,
            post_id=post.post_id,
            error=str(exc),
        )
        entry = MonitorEntry(
            post=post,
            analysis=HumanStyleAnalysis(
                critical_thinking=f"Analysis failed: {str(exc)[:200]}",
                evidence_summary="Pipeline error occurred during analysis.",
                correct_information="Unable to determine — analysis failed.",
                sources=[],
                verdict="UNVERIFIED",
                trust_score=0.0,
                is_misleading=False,
                confidence=0.0,
            ),
            status="analyzed",
        )

    return entry


async def run_crawl(
    keywords: list[str],
    platforms: Optional[list[str]] = None,
    max_posts: int = _MAX_POSTS,
) -> CrawlResponse:
    """
    Run a full crawl cycle:
    1. Scrape posts from all platforms
    2. Filter out already-seen posts
    3. Analyze each through TruthMates pipeline
    4. Save to social_monitor collection
    """
    started = stage_start()
    errors: list[str] = []

    if not keywords:
        keywords = [
            "India government policy fake",
            "PIB fact check",
            "modi scheme false",
            "aadhaar scam",
            "UPI fraud news",
        ]

    # 1. Scrape
    log_event(logger, "crawl_started", platforms=platforms or "all", keywords=keywords, max_posts=max_posts)
    raw_posts = await crawl_all_platforms(keywords, platforms=platforms, max_posts=max_posts)
    log_event(logger, "scrape_complete", total_scraped=len(raw_posts))

    if not raw_posts:
        return CrawlResponse(status="success", crawled=0, analyzed=0, flagged=0, errors=["No posts scraped"])

    # 2. Filter already-seen posts
    new_posts = await _filter_seen_posts(raw_posts)
    log_event(logger, "dedup_complete", new_posts=len(new_posts), filtered_out=len(raw_posts) - len(new_posts))

    if not new_posts:
        return CrawlResponse(
            status="success",
            crawled=len(raw_posts),
            analyzed=0,
            flagged=0,
            errors=["All scraped posts were already seen"],
        )

    # 3. Analyze each post (sequentially to avoid LLM rate limits)
    analyzed = 0
    flagged = 0
    for post in new_posts[:_MAX_POSTS]:
        try:
            entry = await analyze_single_post(post)
            await save_monitor_entry(entry)
            analyzed += 1
            if entry.analysis and entry.analysis.is_misleading:
                flagged += 1
        except Exception as exc:
            error_msg = f"Failed to analyze post {post.post_id}: {str(exc)[:100]}"
            errors.append(error_msg)
            log_event(logger, "post_analysis_error", post_id=post.post_id, error=str(exc))

    duration = stage_duration_ms(started)
    log_event(
        logger, "crawl_complete",
        crawled=len(raw_posts), analyzed=analyzed, flagged=flagged,
        duration_ms=duration,
    )

    return CrawlResponse(
        status="success",
        crawled=len(raw_posts),
        analyzed=analyzed,
        flagged=flagged,
        errors=errors,
    )


# ── MongoDB persistence ─────────────────────────────────────────────────────


async def save_monitor_entry(entry: MonitorEntry) -> None:
    """Upsert a monitor entry by platform + post_id."""
    collection = get_db()["social_monitor"]
    doc = entry.model_dump(mode="json")

    await collection.update_one(
        filter={
            "post.platform": entry.post.platform,
            "post.post_id": entry.post.post_id,
        },
        update={"$set": doc},
        upsert=True,
    )


async def _filter_seen_posts(posts: list[ScrapedSocialPost]) -> list[ScrapedSocialPost]:
    """Filter out posts that already exist in the social_monitor collection."""
    if not posts:
        return []

    collection = get_db()["social_monitor"]
    post_ids = [p.post_id for p in posts]

    cursor = collection.find(
        {"post.post_id": {"$in": post_ids}},
        {"post.post_id": 1},
    )
    seen_ids = {doc["post"]["post_id"] async for doc in cursor}

    return [p for p in posts if p.post_id not in seen_ids]


async def get_monitor_entries(
    status: Optional[str] = None,
    verdict: Optional[str] = None,
    platform: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[MonitorEntry]:
    """Query monitor entries with optional filters."""
    collection = get_db()["social_monitor"]
    query: dict = {}

    if status:
        query["status"] = status
    if verdict:
        query["analysis.verdict"] = verdict
    if platform:
        query["post.platform"] = platform

    cursor = (
        collection.find(query)
        .sort("created_at", -1)
        .skip(offset)
        .limit(limit)
    )

    entries = []
    async for doc in cursor:
        doc.pop("_id", None)
        try:
            entries.append(MonitorEntry(**doc))
        except Exception:
            pass

    return entries


async def update_entry_status(
    entry_id: str,
    action: str,
    moderator_note: Optional[str] = None,
    edited_reply: Optional[str] = None,
) -> Optional[MonitorEntry]:
    """Update the status of a monitor entry (approve/reject)."""
    collection = get_db()["social_monitor"]

    update_fields = {
        "status": action,
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
    }
    if moderator_note:
        update_fields["moderator_note"] = moderator_note
    if edited_reply:
        update_fields["suggested_reply"] = edited_reply

    result = await collection.find_one_and_update(
        {"entry_id": entry_id},
        {"$set": update_fields},
        return_document=True,
    )

    if result:
        result.pop("_id", None)
        return MonitorEntry(**result)
    return None


async def get_entry_by_id(entry_id: str) -> Optional[MonitorEntry]:
    """Get a single monitor entry by its entry_id."""
    collection = get_db()["social_monitor"]
    doc = await collection.find_one({"entry_id": entry_id})
    if doc:
        doc.pop("_id", None)
        return MonitorEntry(**doc)
    return None


async def get_social_stats() -> SocialStatsResponse:
    """Aggregate dashboard statistics from the social_monitor collection."""
    collection = get_db()["social_monitor"]

    total = await collection.count_documents({})
    misleading = await collection.count_documents({"analysis.is_misleading": True})
    accurate = await collection.count_documents({"analysis.verdict": "SUPPORTED"})
    unverified = await collection.count_documents(
        {"analysis.verdict": {"$in": ["UNVERIFIED", "INSUFFICIENT_EVIDENCE"]}}
    )
    pending = await collection.count_documents({"status": {"$in": ["pending", "analyzed"]}})
    approved = await collection.count_documents({"status": "approved"})
    rejected = await collection.count_documents({"status": "rejected"})

    # Count by platform
    by_platform: dict[str, int] = {}
    for platform in ["twitter", "youtube", "reddit", "instagram"]:
        count = await collection.count_documents({"post.platform": platform})
        if count > 0:
            by_platform[platform] = count

    return SocialStatsResponse(
        total_scraped=total,
        total_misleading=misleading,
        total_accurate=accurate,
        total_unverified=unverified,
        pending_review=pending,
        approved=approved,
        rejected=rejected,
        by_platform=by_platform,
    )
