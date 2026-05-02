"""
RSSFetchTool — Custom CrewAI tool that fetches and parses RSS/Atom feeds
for the TruthMates project (PIB & MyGov).
"""

import json
import os
from typing import Type

import requests
from bs4 import BeautifulSoup
from crewai.tools import BaseTool
from pydantic import BaseModel, Field


# ── Input Schema ──────────────────────────────────────────────────────────────

class RSSFetchInput(BaseModel):
    """Input schema for RSSFetchTool."""

    urls: str = Field(
        ...,
        description=(
            "Comma-separated list of RSS feed URLs to fetch. "
            "Example: 'https://feed1.com/rss,https://feed2.com/rss'"
        ),
    )


# ── Tool Implementation ───────────────────────────────────────────────────────

class RSSFetchTool(BaseTool):
    """
    Fetches one or more RSS/XML feeds and extracts structured post data.

    Returns a JSON string containing a list of items with fields:
    title, description, link, pubDate, source.
    """

    name: str = "RSSFetchTool"
    description: str = (
        "Fetches RSS feed URLs and extracts post data (title, description, "
        "link, pubDate, source) from each <item> element. "
        "Input: comma-separated RSS URLs. "
        "Output: JSON array of post objects."
    )
    args_schema: Type[BaseModel] = RSSFetchInput

    # Friendly display names mapped from URL substrings
    _SOURCE_MAP: dict = {
        "pib.gov.in": "PIB",
        "mygov.in": "MyGov",
    }

    def _run(self, urls: str) -> str:
        """Execute the tool: fetch and parse all provided RSS feeds."""
        url_list = [u.strip() for u in urls.split(",") if u.strip()]
        all_items: list[dict] = []

        for url in url_list:
            source = self._detect_source(url)
            items = self._fetch_feed(url, source)
            all_items.extend(items)

        return json.dumps(all_items, ensure_ascii=False, indent=2)

    # ── Private helpers ───────────────────────────────────────────────────────

    def _detect_source(self, url: str) -> str:
        """Return a human-friendly source name for a given URL."""
        for key, name in self._SOURCE_MAP.items():
            if key in url:
                return name
        return "Unknown"

    def _fetch_feed(self, url: str, source: str) -> list[dict]:
        """Fetch a single RSS URL and parse its <item> elements."""
        try:
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (TruthMates/1.0; +https://truthmates.local)"
                )
            }
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
        except requests.RequestException as exc:
            # Graceful degradation — log and return empty list
            print(f"[RSSFetchTool] WARNING: Could not fetch '{url}': {exc}")
            return []

        return self._parse_xml(response.content, source)

    def _parse_xml(self, content: bytes, source: str) -> list[dict]:
        """Parse raw RSS XML bytes and return structured item dicts."""
        # Use lxml-xml for strict XML parsing; fall back to html.parser
        try:
            soup = BeautifulSoup(content, "lxml-xml")
        except Exception:
            soup = BeautifulSoup(content, "html.parser")

        items: list[dict] = []
        for item in soup.find_all("item"):
            items.append(
                {
                    "title": self._text(item, "title"),
                    "description": self._text(item, "description"),
                    "link": self._text(item, "link"),
                    "pubDate": self._text(item, "pubDate"),
                    "source": source,
                }
            )

        return items

    @staticmethod
    def _text(tag, child_name: str) -> str:
        """Safely extract the text of a child tag."""
        child = tag.find(child_name)
        if child is None:
            return ""
        return (child.get_text() or "").strip()
