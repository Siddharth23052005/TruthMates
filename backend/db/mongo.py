"""
MongoDB Atlas client using Motor (async) for the TruthMates project.

Collections:
  civic_posts — stores scraped RSS post data with timestamps.
    civic_classified — stores classified civic posts.
    civic_verified — stores verified civic posts with evidence.
        civic_counter_info — stores counter-info results with trust score.
    civic_validated — stores validated outputs with final verdict.
        agent_monitor_logs — stores monitoring decisions.

Upsert strategy: match on 'link' field to prevent duplicates across scrape runs.
"""

import os
from datetime import datetime, timedelta, timezone

import motor.motor_asyncio
from dotenv import load_dotenv
from db.identity import build_analysis_key

load_dotenv()

# ── Client singleton ──────────────────────────────────────────────────────────

_client: motor.motor_asyncio.AsyncIOMotorClient | None = None


def get_client() -> motor.motor_asyncio.AsyncIOMotorClient:
    """Return (and lazily initialise) the Motor client singleton."""
    global _client
    if _client is None:
        uri = os.environ.get("MONGODB_URI")
        if not uri:
            raise EnvironmentError(
                "MONGODB_URI is not set. Please configure it in your .env file."
            )
        _client = motor.motor_asyncio.AsyncIOMotorClient(uri)
    return _client


def get_db() -> motor.motor_asyncio.AsyncIOMotorDatabase:
    """Return the TruthMates database."""
    db_name = os.environ.get("MONGODB_DB_NAME", "truthmates")
    return get_client()[db_name]


# ── CRUD helpers ──────────────────────────────────────────────────────────────

async def save_posts(posts: list[dict]) -> int:
    """
    Upsert a list of civic post dicts into the 'civic_posts' collection.

    Each post is upserted by its 'link' field.
    A 'scraped_at' UTC timestamp is added/updated on every write.

    Returns the number of documents processed.
    """
    if not posts:
        return 0

    collection = get_db()["civic_posts"]
    now = datetime.now(timezone.utc)
    processed = 0

    for post in posts:
        link = post.get("link", "").strip()
        if not link:
            continue  # Skip posts without a URL

        document = {**post, "scraped_at": now}

        await collection.update_one(
            filter={"link": link},
            update={"$set": document},
            upsert=True,
        )
        processed += 1

    return processed


async def save_classified_posts(posts: list[dict]) -> int:
    """
    Upsert a list of classified civic post dicts into 'civic_classified'.

    Each post is upserted by its 'link' field.
    A 'classified_at' UTC timestamp is added/updated on every write.

    Returns the number of documents processed.
    """
    if not posts:
        return 0

    collection = get_db()["civic_classified"]
    now = datetime.now(timezone.utc)
    processed = 0

    for post in posts:
        link = post.get("link", "").strip()
        if not link:
            continue

        document = {**post, "classified_at": now}

        await collection.update_one(
            filter={"link": link},
            update={"$set": document},
            upsert=True,
        )
        processed += 1

    return processed


async def save_verified_posts(posts: list[dict]) -> int:
    """
    Upsert a list of verified civic post dicts into 'civic_verified'.

    Each post is upserted by its 'link' field.
    A 'verified_at' UTC timestamp is added/updated on every write.

    Returns the number of documents processed.
    """
    if not posts:
        return 0

    collection = get_db()["civic_verified"]
    now = datetime.now(timezone.utc)
    processed = 0

    for post in posts:
        link = post.get("link", "").strip()
        if not link:
            continue

        document = {**post, "verified_at": now}

        await collection.update_one(
            filter={"link": link},
            update={"$set": document},
            upsert=True,
        )
        processed += 1

    return processed


async def save_counter_info_posts(posts: list[dict]) -> int:
    """
    Upsert a list of counter-info post dicts into 'civic_counter_info'.

    Each post is upserted by its 'link' field.
    A 'generated_at' UTC timestamp is added/updated on every write.

    Returns the number of documents processed.
    """
    if not posts:
        return 0

    collection = get_db()["civic_counter_info"]
    now = datetime.now(timezone.utc)
    processed = 0

    for post in posts:
        link = post.get("link", "").strip()
        if not link:
            continue

        document = {**post, "generated_at": now}

        await collection.update_one(
            filter={"link": link},
            update={"$set": document},
            upsert=True,
        )
        processed += 1

    return processed


async def save_validated_posts(posts: list[dict]) -> int:
    """
    Upsert a list of validated output dicts into 'civic_validated'.

    Each post is upserted by its 'analysis_key' field.
    A 'validated_at' UTC timestamp is added/updated on every write.

    Returns the number of documents processed.
    """
    if not posts:
        return 0

    collection = get_db()["civic_validated"]
    now = datetime.now(timezone.utc)
    processed = 0

    for post in posts:
        claim = (post.get("claim") or "").strip()
        if not claim:
            continue

        analysis_key = (post.get("analysis_key") or "").strip()
        source_ref = (
            post.get("source_ref")
            or post.get("video_url")
            or post.get("link")
            or claim
        )
        if not analysis_key:
            analysis_key = build_analysis_key(
                claim=claim,
                input_type=post.get("input_type") or "text",
                source_ref=source_ref,
            )

        document = {
            **post,
            "analysis_key": analysis_key,
            "source_ref": source_ref,
            "validated_at": now,
        }

        await collection.update_one(
            filter={"analysis_key": analysis_key},
            update={"$set": document},
            upsert=True,
        )
        processed += 1

    return processed


async def save_monitor_log(entry: dict) -> None:
    """Insert a monitoring log entry into 'agent_monitor_logs'."""
    collection = get_db()["agent_monitor_logs"]
    await collection.insert_one(entry)


async def get_monitor_logs(limit: int = 100) -> list[dict]:
    """Return recent monitoring logs, newest first."""
    collection = get_db()["agent_monitor_logs"]
    cursor = collection.find().sort("timestamp", -1).limit(limit)
    return [doc async for doc in cursor]


async def get_validated_posts(limit: int = 500) -> list[dict]:
    """Return recent validated posts, newest first."""
    collection = get_db()["civic_validated"]
    cursor = collection.find().sort("validated_at", -1).limit(limit)
    return [doc async for doc in cursor]


async def count_validated_posts() -> int:
    """Return the total number of validated posts."""
    collection = get_db()["civic_validated"]
    return await collection.count_documents({})


async def ping_db() -> bool:
    """Check if the MongoDB connection is alive. Returns True on success."""
    try:
        await get_client().admin.command("ping")
        return True
    except Exception:
        return False


async def recent_topic_exists(topic: str, hours: int = 6) -> bool:
    """Check whether a topic was stored in the last N hours."""
    topic = (topic or "").strip().lower()
    if not topic:
        return False
    threshold = datetime.now(timezone.utc) - timedelta(hours=hours)
    collection = get_db()["trending_results"]
    count = await collection.count_documents(
        {"topic_normalized": topic, "timestamp": {"$gte": threshold}},
        limit=1,
    )
    return count > 0


async def save_trending_results(records: list[dict]) -> int:
    """Insert normalized trending monitoring records."""
    if not records:
        return 0

    collection = get_db()["trending_results"]
    docs: list[dict] = []
    for record in records:
        topic = (record.get("topic") or "").strip()
        url = (record.get("url") or "").strip()
        if not topic or not url:
            continue
        timestamp = record.get("timestamp") or datetime.now(timezone.utc)
        docs.append(
            {
                **record,
                "topic": topic,
                "topic_normalized": topic.lower(),
                "timestamp": timestamp,
            }
        )
    if not docs:
        return 0
    result = await collection.insert_many(docs)
    return len(result.inserted_ids)


async def get_latest_trending(limit: int = 20) -> list[dict]:
    """Return latest trending results sorted by newest timestamp first."""
    collection = get_db()["trending_results"]
    cursor = collection.find().sort("timestamp", -1).limit(limit)
    return [doc async for doc in cursor]


async def get_heatmap_counts() -> list[dict]:
    """Aggregate verdict counts grouped by category."""
    collection = get_db()["trending_results"]
    pipeline = [
        {
            "$group": {
                "_id": "$category",
                "total": {"$sum": 1},
                "misleading": {
                    "$sum": {
                        "$cond": [{"$eq": [{"$toLower": "$verdict"}, "misleading"]}, 1, 0]
                    }
                },
                "unverified": {
                    "$sum": {
                        "$cond": [{"$eq": [{"$toLower": "$verdict"}, "unverified"]}, 1, 0]
                    }
                },
                "verified": {
                    "$sum": {
                        "$cond": [{"$eq": [{"$toLower": "$verdict"}, "verified"]}, 1, 0]
                    }
                },
            }
        },
        {"$sort": {"total": -1}},
    ]
    return [doc async for doc in collection.aggregate(pipeline)]

async def setup_indexes() -> None:
    """Create indexes, including TTL for trending_claims."""
    collection = get_db()["trending_claims"]
    await collection.create_index("timestamp", expireAfterSeconds=7 * 24 * 3600)

async def get_top_trending_claims(region: str | None = None, limit: int = 10) -> list[dict]:
    """Fetch top claims sorted by score descending."""
    collection = get_db()["trending_claims"]
    query = {}
    if region:
        query["region"] = region
    cursor = collection.find(query).sort("score", -1).limit(limit)
    return [doc async for doc in cursor]

