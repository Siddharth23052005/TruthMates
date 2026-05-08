from __future__ import annotations

from fastapi import APIRouter

from db.mongo import get_heatmap_counts, get_latest_trending, get_top_trending_claims

router = APIRouter(prefix="/api", tags=["Trending"])


def _severity_from_bucket(bucket: dict) -> str:
    misleading = int(bucket.get("misleading", 0))
    unverified = int(bucket.get("unverified", 0))
    total = int(bucket.get("total", 0))
    if total <= 0:
        return "Low"
    ratio = (misleading + unverified) / total
    if ratio >= 0.6:
        return "High"
    if ratio >= 0.3:
        return "Medium"
    return "Low"


@router.get("/trending")
async def get_trending() -> dict:
    rows = await get_latest_trending(limit=20)
    items: list[dict] = []
    for row in rows:
        row["id"] = str(row.pop("_id"))
        timestamp = row.get("timestamp")
        if timestamp is not None and hasattr(timestamp, "isoformat"):
            row["timestamp"] = timestamp.isoformat()
        items.append(row)
    return {"count": len(items), "items": items}


@router.get("/heatmap")
async def get_heatmap() -> dict:
    buckets = await get_heatmap_counts()
    items: list[dict] = []
    for bucket in buckets:
        category = bucket.get("_id") or "Politics"
        items.append(
            {
                "category": category,
                "count": int(bucket.get("total", 0)),
                "verdicts": {
                    "misleading": int(bucket.get("misleading", 0)),
                    "unverified": int(bucket.get("unverified", 0)),
                    "verified": int(bucket.get("verified", 0)),
                },
                "severity": _severity_from_bucket(bucket),
            }
        )
    return {"count": len(items), "items": items}


@router.get("/trending-claims")
async def get_trending_claims(region: str | None = None) -> dict:
    rows = await get_top_trending_claims(region=region, limit=10)
    items: list[dict] = []
    for row in rows:
        row["id"] = str(row.pop("_id"))
        timestamp = row.get("timestamp")
        if timestamp is not None and hasattr(timestamp, "isoformat"):
            row["timestamp"] = timestamp.isoformat()
        items.append(row)
    return {"count": len(items), "items": items}
