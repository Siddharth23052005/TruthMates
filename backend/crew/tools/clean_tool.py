"""
CleanDedupTool — Custom CrewAI tool that cleans and deduplicates raw RSS data
for the TruthMates project.

Operations performed:
  1. Strip HTML tags from 'description' field
  2. Normalize 'pubDate' to ISO 8601 format
  3. Deduplicate by 'link' URL (first-wins)
  4. Rename 'pubDate' → 'pub_date'
"""

import json
import re
from email.utils import parsedate_to_datetime
from typing import Type

from bs4 import BeautifulSoup
from crewai.tools import BaseTool
from pydantic import BaseModel, Field


# ── Input Schema ──────────────────────────────────────────────────────────────

class CleanDedupInput(BaseModel):
    """Input schema for CleanDedupTool."""

    raw_json: str = Field(
        ...,
        description=(
            "JSON string containing a list of raw civic post objects with fields: "
            "title, description, link, pubDate, source."
        ),
    )


# ── Tool Implementation ───────────────────────────────────────────────────────

class CleanDedupTool(BaseTool):
    """
    Cleans and deduplicates a raw list of RSS post objects.

    Input : JSON string (list of raw post dicts)
    Output: JSON string (list of cleaned, deduplicated post dicts)
    """

    name: str = "CleanDedupTool"
    description: str = (
        "Cleans HTML from descriptions, normalizes pubDate to ISO 8601, "
        "deduplicates by link URL, and renames 'pubDate' to 'pub_date'. "
        "Input: raw JSON string from RSSFetchTool. "
        "Output: clean JSON array of civic posts."
    )
    args_schema: Type[BaseModel] = CleanDedupInput

    def _run(self, raw_json: str) -> str:
        """Execute the cleaning and deduplication pipeline."""
        # 1. Parse input — handle cases where the LLM wraps JSON in markdown
        posts = self._safe_parse(raw_json)
        if not isinstance(posts, list):
            return json.dumps([], ensure_ascii=False)

        cleaned: list[dict] = []
        seen_links: set[str] = set()

        for post in posts:
            link = (post.get("link") or "").strip()

            # 2. Deduplicate — skip if we've already seen this URL
            if not link or link in seen_links:
                continue
            seen_links.add(link)

            # 3. Strip HTML from description
            raw_desc = post.get("description") or ""
            clean_desc = self._strip_html(raw_desc)

            # 4. Normalize pubDate → ISO 8601
            raw_date = post.get("pubDate") or post.get("pub_date") or ""
            iso_date = self._normalize_date(raw_date)

            cleaned.append(
                {
                    "title": (post.get("title") or "").strip(),
                    "description": clean_desc,
                    "link": link,
                    "pub_date": iso_date,
                    "source": (post.get("source") or "Unknown").strip(),
                }
            )

        return json.dumps(cleaned, ensure_ascii=False, indent=2)

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _safe_parse(text: str) -> list:
        """Parse JSON, stripping markdown code fences if present."""
        # Remove ```json ... ``` wrappers that LLMs sometimes add
        text = re.sub(r"```(?:json)?\s*", "", text).strip()
        text = text.rstrip("`").strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return []

    @staticmethod
    def _strip_html(html_text: str) -> str:
        """Remove all HTML tags and collapse whitespace."""
        soup = BeautifulSoup(html_text, "html.parser")
        text = soup.get_text(separator=" ")
        # Collapse multiple spaces / newlines
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _normalize_date(date_str: str) -> str | None:
        """
        Convert an RFC 2822 / arbitrary date string to ISO 8601.
        Returns None if the date cannot be parsed.
        """
        if not date_str:
            return None
        try:
            dt = parsedate_to_datetime(date_str)
            return dt.isoformat()
        except Exception:
            pass

        # Try stripping timezone words and re-parsing
        cleaned = re.sub(r"\s+[A-Z]{2,4}$", "", date_str.strip())
        for fmt in (
            "%a, %d %b %Y %H:%M:%S",
            "%d %b %Y %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d",
        ):
            try:
                from datetime import datetime
                return datetime.strptime(cleaned, fmt).isoformat()
            except ValueError:
                continue

        return None  # Unparseable
