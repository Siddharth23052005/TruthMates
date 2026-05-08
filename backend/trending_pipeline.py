import asyncio
import json
import os
from datetime import datetime, timezone

from groq import AsyncGroq
from core.logging import get_logger, log_event
from db.mongo import get_db
from rss_fetcher import fetch_rss_feeds

logger = get_logger("truthmates.trending_pipeline")

client = None
def get_groq_client():
    global client
    if not client:
        client = AsyncGroq(api_key=os.environ.get("GROQ_API_KEY"))
    return client

async def is_duplicate(title: str) -> bool:
    collection = get_db()["trending_claims"]
    six_hours_ago = datetime.now(timezone.utc).timestamp() - (6 * 3600)
    six_hours_ago_dt = datetime.fromtimestamp(six_hours_ago, tz=timezone.utc)
    count = await collection.count_documents({
        "headline": title,
        "timestamp": {"$gte": six_hours_ago_dt}
    }, limit=1)
    return count > 0

async def analyze_claim(title: str) -> dict | None:
    prompt = f"""You are a misinformation analyst. Given this news headline, extract the core claim
and assign a misleading score from 50 to 100 (50 = possibly misleading, 100 = definitely false).
Return only JSON: {{"claim": "...", "score": 75, "verdict": "Misleading", "reasoning": "..."}}

HEADLINE: {title}"""
    try:
        groq_client = get_groq_client()
        response = await groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-8b-instant",
            response_format={"type": "json_object"},
            temperature=0
        )
        content = response.choices[0].message.content
        return json.loads(content)
    except Exception as exc:
        logger.error(f"Groq LLM analysis failed for '{title}': {exc}")
        return None

async def run() -> dict:
    entries = await asyncio.to_thread(fetch_rss_feeds)
    collection = get_db()["trending_claims"]
    
    fetched = len(entries)
    filtered = 0
    stored = 0
    discarded = 0
    
    for entry in entries:
        title = entry["title"]
        if await is_duplicate(title):
            filtered += 1
            continue
            
        analysis = await analyze_claim(title)
        if not analysis:
            discarded += 1
            continue
            
        score = analysis.get("score", 0)
        if score >= 50:
            doc = {
                "claim": analysis.get("claim", ""),
                "headline": title,
                "source": entry["source"],
                "url": entry["link"],
                "score": score,
                "verdict": analysis.get("verdict", "Misleading"),
                "reasoning": analysis.get("reasoning", ""),
                "region": "IN",
                "timestamp": datetime.now(timezone.utc),
                "ttl": "7 days"
            }
            await collection.insert_one(doc)
            stored += 1
        else:
            discarded += 1
            
    payload = {
        "feeds_fetched": fetched,
        "items_filtered_duplicate": filtered,
        "items_stored": stored,
        "items_discarded": discarded
    }
    log_event(logger, "trending_pipeline_complete", **payload)
    return payload
