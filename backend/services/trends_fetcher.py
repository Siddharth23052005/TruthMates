from __future__ import annotations

import xml.etree.ElementTree as ET

import requests
from pytrends.request import TrendReq


def _rss_fallback(limit: int) -> list[str]:
    try:
        response = requests.get("https://trends.google.com/trending/rss?geo=IN", timeout=10)
        response.raise_for_status()
        root = ET.fromstring(response.text)
        titles = root.findall("./channel/item/title")
        queries: list[str] = []
        for item in titles:
            query = (item.text or "").strip()
            if query and query not in queries:
                queries.append(query)
            if len(queries) >= limit:
                break
        return queries
    except Exception:
        return []


def get_top_rising_queries_india(limit: int = 5) -> list[str]:
    """
    Fetch top rising Google Trends queries for India.
    Returns an empty list on rate-limit or API failures.
    """
    try:
        pytrends = TrendReq(hl="en-US", tz=330)
        trending_df = pytrends.trending_searches(pn="india")
        if trending_df is None or trending_df.empty:
            return _rss_fallback(limit)

        queries: list[str] = []
        for value in trending_df[0].tolist():
            query = str(value).strip()
            if query and query not in queries:
                queries.append(query)
            if len(queries) >= limit:
                break
        return queries
    except Exception:
        return _rss_fallback(limit)
