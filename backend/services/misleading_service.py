from __future__ import annotations

import json
import re

from pydantic import BaseModel, Field

from core.llm import build_crewai_llm, media_llm_provider_order
from services.source_weighting_service import weighted_evidence_summary


class MisleadingAssessment(BaseModel):
    is_misleading: bool
    misleading_reason: str | None = None
    missing_context: bool = False
    wrong_time_place_or_sample: bool = False
    selective_quote: bool = False
    false_framing: bool = False
    media_caption_mismatch: bool = False
    statistic_scope_mismatch: bool = False
    insufficient_evidence: bool = False
    confidence: float = Field(..., ge=0.0, le=1.0)
    rationale: str


def _strip_markdown_json(text: str) -> str:
    text = re.sub(r"```(?:json)?\s*", "", text).strip()
    return text.rstrip("`").strip()


def _misleading_prompt(
    *,
    claim: str,
    evidence_summary: str,
    content_summary: str,
    correction_text: str,
    input_type: str,
) -> str:
    return f"""
Assess whether this {input_type} claim is misleading.

CLAIM:
{claim}

CONTENT SUMMARY:
{content_summary or "No content summary provided."}

CURRENT CORRECTION:
{correction_text or "No correction text yet."}

WEIGHTED EVIDENCE:
{evidence_summary or "No trusted evidence was retrieved."}

Misleading detection checklist:
1. Is the claim technically true but missing context that reverses its meaning?
2. Is a statistic real but from the wrong time period, place, population, or sample?
3. Is an official source being selectively quoted while omitting a contradictory part?
4. Is the framing designed to push a false conclusion even if individual facts are real?
5. For media inputs, does the caption/title/voice-over misrepresent what is shown or said?
6. Does the claim use a real number or event in a way that overstates its scope or relevance?

Return ONLY valid JSON:
{{
  "is_misleading": true,
  "misleading_reason": "specific short explanation or null",
  "missing_context": true,
  "wrong_time_place_or_sample": false,
  "selective_quote": false,
  "false_framing": true,
  "media_caption_mismatch": false,
  "statistic_scope_mismatch": false,
  "insufficient_evidence": false,
  "confidence": 0.82,
  "rationale": "brief reason grounded in the evidence"
}}

Rules:
- Set is_misleading to true only when the evidence supports a specific misleading mechanism.
- misleading_reason must explain HOW it misleads, not just say that it does.
- If evidence is missing or weak, set insufficient_evidence=true and do not invent a misleading mechanism.
- Do not guess facts that are not present in the evidence summary.
""".strip()


def _run_once(prompt: str, provider: str) -> MisleadingAssessment:
    from crewai import Agent, Crew, Process, Task

    llm = build_crewai_llm(provider, temperature=0.0)
    agent = Agent(
        role="Misleading Detector",
        goal="Explain whether a claim misleads and identify the exact mechanism.",
        backstory="You are a skeptical fact-checker who distinguishes outright falsehoods from context manipulation.",
        llm=llm,
        verbose=True,
    )
    task = Task(description=prompt, expected_output="Valid JSON matching the requested schema.", agent=agent)
    crew = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=True)

    for attempt in range(2):
        result = crew.kickoff()
        raw_text = result.raw if hasattr(result, "raw") else str(result)
        clean_text = _strip_markdown_json(raw_text)
        try:
            return MisleadingAssessment.model_validate_json(clean_text)
        except Exception as exc:
            if attempt >= 1:
                raise RuntimeError(f"Misleading assessment failed validation: {exc}") from exc
            schema_hint = json.dumps(MisleadingAssessment.model_json_schema(), indent=2)
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
    raise RuntimeError("Misleading assessment failed.")


def assess_misleading(
    *,
    claim: str,
    matches: list,
    content_summary: str = "",
    correction_text: str = "",
    input_type: str = "text",
) -> MisleadingAssessment:
    if not matches:
        return MisleadingAssessment(
            is_misleading=False,
            misleading_reason=None,
            insufficient_evidence=True,
            confidence=0.0,
            rationale="No trusted evidence was available for a misleadingness assessment.",
        )

    prompt = _misleading_prompt(
        claim=claim,
        evidence_summary=weighted_evidence_summary(matches),
        content_summary=content_summary,
        correction_text=correction_text,
        input_type=input_type,
    )

    last_error: Exception | None = None
    for provider in media_llm_provider_order():
        try:
            return _run_once(prompt, provider)
        except Exception as exc:
            last_error = exc
            continue
    raise RuntimeError(f"Misleading assessment failed across providers: {last_error}") from last_error
