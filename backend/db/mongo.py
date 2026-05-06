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
from datetime import datetime, timezone

import motor.motor_asyncio
from dotenv import load_dotenv

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

    Each post is upserted by its 'claim' field.
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

        document = {**post, "validated_at": now}

        await collection.update_one(
            filter={"claim": claim},
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


async def ping_db() -> bool:
    """Check if the MongoDB connection is alive. Returns True on success."""
    try:
        await get_client().admin.command("ping")
        return True
    except Exception:
        return False
