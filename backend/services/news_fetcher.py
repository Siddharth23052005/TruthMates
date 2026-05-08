from __future__ import annotations

import os

from newsapi import NewsApiClient
from dotenv import load_dotenv

load_dotenv()


def fetch_related_articles(keyword: str, limit: int = 5) -> list[dict]:
    """
    Fetch top related NewsAPI articles for a keyword.
    Returns a normalized list of article dictionaries.
    """
    api_key = os.environ.get("NEWSAPI_KEY", "").strip()
    if not api_key or not keyword.strip():
        return []

    try:
        client = NewsApiClient(api_key=api_key)
        response = client.get_everything(
            q=keyword,
            language="en",
            sort_by="publishedAt",
            page_size=limit,
        )
        articles = response.get("articles", []) if isinstance(response, dict) else []
    except Exception:
        return []

    normalized: list[dict] = []
    for article in articles[:limit]:
        source = article.get("source") or {}
        normalized.append(
            {
                "headline": article.get("title") or "",
                "source": source.get("name") or "Unknown",
                "url": article.get("url") or "",
                "publishedAt": article.get("publishedAt"),
                "description": article.get("description") or "",
            }
        )
    return normalized
