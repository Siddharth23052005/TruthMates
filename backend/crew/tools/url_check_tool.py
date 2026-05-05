"""
UrlCheckTool — CrewAI tool to verify source URLs are reachable.
"""

from __future__ import annotations

import json
from typing import Type

import requests
from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class UrlCheckInput(BaseModel):
    """Input schema for UrlCheckTool."""

    urls: list[str] = Field(
        ..., description="List of source URLs to check for reachability."
    )


class UrlCheckTool(BaseTool):
    """Checks whether URLs are reachable using HTTP HEAD/GET."""

    name: str = "UrlCheckTool"
    description: str = (
        "Checks if each URL is reachable (HTTP status < 400). "
        "Input: list of URLs. Output: JSON list of {url, reachable, status_code}."
    )
    args_schema: Type[BaseModel] = UrlCheckInput

    def _run(self, urls: list[str]) -> str:
        results = []
        for url in urls:
            url = (url or "").strip()
            if not url:
                results.append({"url": url, "reachable": False, "status_code": None})
                continue

            status_code = None
            reachable = False

            try:
                response = requests.head(url, timeout=8, allow_redirects=True)
                status_code = response.status_code
                reachable = status_code < 400
            except Exception:
                try:
                    response = requests.get(url, timeout=8, allow_redirects=True)
                    status_code = response.status_code
                    reachable = status_code < 400
                except Exception:
                    reachable = False

            results.append(
                {
                    "url": url,
                    "reachable": reachable,
                    "status_code": status_code,
                }
            )

        return json.dumps(results, ensure_ascii=True, indent=2)
