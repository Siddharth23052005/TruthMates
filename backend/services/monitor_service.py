from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from core.logging import get_logger, log_event
from crew.classifier_crew import classify_headline_description
from db.mongo import recent_topic_exists, save_trending_results
from services.news_fetcher import fetch_related_articles
from services.trends_fetcher import get_top_rising_queries_india

logger = get_logger("truthmates.monitor_service")


def _categorize_topic(topic: str) -> str:
    topic_l = (topic or "").lower()
    health_terms = ("health", "vaccine", "virus", "flu", "covid", "disease", "hospital")
    politics_terms = ("election", "minister", "government", "parliament", "policy", "politics")
    science_terms = ("space", "nasa", "research", "science", "technology", "ai")
    finance_terms = ("bank", "stock", "market", "rupee", "inflation", "finance", "economy")

    if any(term in topic_l for term in health_terms):
        return "Health"
    if any(term in topic_l for term in politics_terms):
        return "Politics"
    if any(term in topic_l for term in science_terms):
        return "Science"
    if any(term in topic_l for term in finance_terms):
        return "Finance"
    return "Politics"


async def run() -> dict:
    """
    Full monitoring pipeline:
    Trends -> duplicate filter -> NewsAPI -> Crew classifier -> MongoDB.
    """
    topics = await asyncio.to_thread(get_top_rising_queries_india, 5)
    inserted = 0
    skipped = 0
    processed_topics = 0

    for topic in topics:
        is_duplicate = await recent_topic_exists(topic, hours=6)
        if is_duplicate:
            skipped += 1
            continue

        processed_topics += 1
        category = _categorize_topic(topic)
        articles = await asyncio.to_thread(fetch_related_articles, topic, 5)
        records: list[dict] = []

        for article in articles:
            try:
                classification = await asyncio.to_thread(
                    classify_headline_description,
                    article.get("headline", ""),
                    article.get("description", ""),
                )
            except Exception:
                classification = {
                    "verdict": "Unverified",
                    "trust_score": 50,
                    "reasoning": "Classification failed; saved with fallback verdict.",
                }
            records.append(
                {
                    "topic": topic,
                    "category": category,
                    "headline": article.get("headline", ""),
                    "source": article.get("source", ""),
                    "url": article.get("url", ""),
                    "publishedAt": article.get("publishedAt"),
                    "description": article.get("description", ""),
                    "trust_score": classification.get("trust_score", 50),
                    "verdict": classification.get("verdict", "Unverified"),
                    "reasoning": classification.get("reasoning", ""),
                    "region": "IN",
                    "timestamp": datetime.now(timezone.utc),
                }
            )

        inserted += await save_trending_results(records)

    payload = {
        "topics_detected": len(topics),
        "topics_processed": processed_topics,
        "topics_skipped_duplicate": skipped,
        "records_inserted": inserted,
    }
    log_event(logger, "monitor_pipeline_complete", **payload)
    return payload
