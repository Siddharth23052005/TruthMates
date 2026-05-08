from __future__ import annotations

import json
import re

from pydantic import BaseModel, Field

from core.constants import (
    MEDIA_ANALYSIS_ROUTE_OUT_OF_SCOPE_EXIT,
    MEDIA_ANALYSIS_ROUTE_SATIRE_EXIT,
    MEDIA_ANALYSIS_ROUTE_VERIFY,
    MEDIA_CONTENT_CATEGORY_COMMENTARY,
    MEDIA_CONTENT_CATEGORY_GOVERNMENT,
    MEDIA_CONTENT_CATEGORY_OUT_OF_SCOPE,
    MEDIA_CONTENT_CATEGORY_SATIRE,
)
from core.llm import build_crewai_llm, media_llm_provider_order


class ContentClassification(BaseModel):
    content_category: str = Field(
        ...,
        description="government_claim | commentary | satire | out_of_scope",
    )
    analysis_route: str = Field(
        ...,
        description="VERIFY | SATIRE_EXIT | OUT_OF_SCOPE_EXIT",
    )
    rationale: str = Field(..., description="Short reason for the classification decision.")
    summary: str = Field(..., description="One or two sentences describing the media content.")


def _strip_markdown_json(text: str) -> str:
    text = re.sub(r"```(?:json)?\s*", "", text).strip()
    return text.rstrip("`").strip()


def _classification_prompt(transcript: str, title: str, input_type: str) -> str:
    return f"""
Classify this {input_type} before any fact-checking.

TITLE:
{title or "Unknown"}

TRANSCRIPT:
{transcript[:3000]}

Return ONLY valid JSON:
{{
  "content_category": "government_claim | commentary | satire | out_of_scope",
  "analysis_route": "VERIFY | SATIRE_EXIT | OUT_OF_SCOPE_EXIT",
  "rationale": "short reason",
  "summary": "1-2 sentence summary"
}}

Rules:
- Use "government_claim" when the speaker makes a factual claim about government policy, officials, elections, public schemes, taxes, budgets, public statistics, or other civic matters that should be verified.
- Use "commentary" when the content discusses civic or government topics as opinion, reaction, or analysis without a concrete factual claim requiring verification. Commentary should still route to VERIFY if it includes a checkable factual claim.
- Use "satire" when the content is comedic, parodic, exaggerated for humor, or clearly not intended as a literal factual assertion. Satire must route to SATIRE_EXIT.
- Use "out_of_scope" when the content is unrelated to civic, government, or public-affairs claims. Out-of-scope content must route to OUT_OF_SCOPE_EXIT.
- Be conservative. If the content includes even one concrete civic factual claim, route to VERIFY.
- Do not perform fact-checking yet. Only classify the nature of the content and the correct analysis route.
""".strip()


def _normalize_classification(raw: ContentClassification) -> ContentClassification:
    category = (raw.content_category or "").strip().lower()
    route = (raw.analysis_route or "").strip().upper()

    valid_categories = {
        MEDIA_CONTENT_CATEGORY_GOVERNMENT,
        MEDIA_CONTENT_CATEGORY_COMMENTARY,
        MEDIA_CONTENT_CATEGORY_SATIRE,
        MEDIA_CONTENT_CATEGORY_OUT_OF_SCOPE,
    }
    valid_routes = {
        MEDIA_ANALYSIS_ROUTE_VERIFY,
        MEDIA_ANALYSIS_ROUTE_SATIRE_EXIT,
        MEDIA_ANALYSIS_ROUTE_OUT_OF_SCOPE_EXIT,
    }

    if category not in valid_categories:
        category = MEDIA_CONTENT_CATEGORY_GOVERNMENT
    if route not in valid_routes:
        route = MEDIA_ANALYSIS_ROUTE_VERIFY

    if category == MEDIA_CONTENT_CATEGORY_SATIRE:
        route = MEDIA_ANALYSIS_ROUTE_SATIRE_EXIT
    if category == MEDIA_CONTENT_CATEGORY_OUT_OF_SCOPE:
        route = MEDIA_ANALYSIS_ROUTE_OUT_OF_SCOPE_EXIT

    return ContentClassification(
        content_category=category,
        analysis_route=route,
        rationale=(raw.rationale or "").strip() or "Classification rationale unavailable.",
        summary=(raw.summary or "").strip() or "Content summary unavailable.",
    )


def _run_once(transcript: str, title: str, input_type: str, provider: str) -> ContentClassification:
    from crewai import Agent, Crew, Process, Task

    llm = build_crewai_llm(provider, temperature=0.0)
    agent = Agent(
        role="Content Classifier",
        goal="Route media content into the correct analysis path before fact-checking.",
        backstory="You are a skeptical civic editor who decides whether content should be verified, treated as satire, or marked out of scope.",
        llm=llm,
        verbose=True,
    )
    prompt = _classification_prompt(transcript, title, input_type)
    task = Task(
        description=prompt,
        expected_output="Valid JSON matching the requested schema.",
        agent=agent,
    )
    crew = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=True)

    for attempt in range(2):
        result = crew.kickoff()
        raw_text = result.raw if hasattr(result, "raw") else str(result)
        clean_text = _strip_markdown_json(raw_text)
        try:
            parsed = ContentClassification.model_validate_json(clean_text)
            return _normalize_classification(parsed)
        except Exception as exc:
            if attempt >= 1:
                raise RuntimeError(f"Content classification failed validation: {exc}") from exc
            schema_hint = json.dumps(ContentClassification.model_json_schema(), indent=2)
            retry_task = Task(
                description=(
                    f"{prompt}\n\nPREVIOUS ATTEMPT FAILED VALIDATION: {exc}\n"
                    f"You MUST return valid JSON matching this exact schema:\n{schema_hint}\n"
                    "No markdown fences. No commentary. ONLY the JSON."
                ),
                expected_output="Valid JSON matching the requested schema.",
                agent=agent,
            )
            crew = Crew(agents=[agent], tasks=[retry_task], process=Process.sequential, verbose=True)
    raise RuntimeError("Content classification failed.")


def classify_media_content(transcript: str, *, title: str = "", input_type: str = "video") -> tuple[ContentClassification, str]:
    last_error: Exception | None = None
    for provider in media_llm_provider_order():
        try:
            return _run_once(transcript, title, input_type, provider), provider
        except Exception as exc:
            last_error = exc
            continue
    raise RuntimeError(f"Content classification failed across providers: {last_error}") from last_error
