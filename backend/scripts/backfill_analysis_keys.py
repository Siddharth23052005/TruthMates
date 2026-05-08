from __future__ import annotations

import asyncio

from db.identity import build_analysis_key
from db.mongo import get_db


async def main() -> None:
    collection = get_db()["civic_validated"]
    updated = 0

    async for doc in collection.find({"analysis_key": {"$exists": False}}):
        claim = (doc.get("claim") or "").strip()
        if not claim:
            continue

        source_ref = (
            doc.get("source_ref")
            or doc.get("video_url")
            or doc.get("link")
            or claim
        )
        analysis_key = build_analysis_key(
            claim=claim,
            input_type=doc.get("input_type") or "text",
            source_ref=source_ref,
        )
        await collection.update_one(
            {"_id": doc["_id"]},
            {"$set": {"analysis_key": analysis_key, "source_ref": source_ref}},
        )
        updated += 1

    print(f"Backfilled analysis_key for {updated} civic_validated documents.")


if __name__ == "__main__":
    asyncio.run(main())
