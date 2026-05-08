from __future__ import annotations

import json
import re
from typing import Literal

from pydantic import BaseModel, Field

from core.llm import build_crewai_llm, media_llm_provider_order
from services.misleading_service import MisleadingAssessment
from services.source_weighting_service import aggregate_weight_score, weighted_evidence_summary


class VerdictAssessment(BaseModel):
    verdict: Literal[
        "SUPPORTED",
        "REFUTED",
        "MISLEADING",
        "UNVERIFIED",
        "INSUFFICIENT_EVIDENCE",
    ]
    explanation: str
    countercheck_note: str
    source_weight_score: float = Field(..., ge=0.0, le=100.0)
    confidence: float = Field(..., ge=0.0, le=1.0)


def _strip_markdown_json(text: str) -> str:
    text = re.sub(r"```(?:json)?\s*", "", text).strip()
    return text.rstrip("`").strip()


def _verdict_prompt(
    *,
    claim: str,
    verification_label: str,
    evidence_summary: str,
    misleading: MisleadingAssessment,
    input_type: str,
) -> str:
    return f"""
Decide the final verdict for this {input_type} claim like a skeptical human fact-checker.

CLAIM:
{claim}

VERIFICATION LABEL:
{verification_label}

WEIGHTED EVIDENCE:
{evidence_summary or "No trusted evidence was retrieved."}

MISLEADING ASSESSMENT:
{misleading.model_dump_json()}

Reasoning style:
- First reaction: ask whether the claim makes sense on its face or sounds extraordinary.
- Source instinct: weigh official government, regulator, and primary institutional sources above commentary or open-web sources.
- Evidence weighing: explain whether the strongest evidence supports, refutes, or only partially addresses the claim.
- Counter-check: actively look for the strongest evidence in the opposite direction and record it in countercheck_note.
- Plain language: explanation must sound like a smart friend, not a legal disclaimer.

Return ONLY valid JSON:
{{
  "verdict": "SUPPORTED | REFUTED | MISLEADING | UNVERIFIED | INSUFFICIENT_EVIDENCE",
  "explanation": "max 3 sentences, direct language",
  "countercheck_note": "one sentence about the strongest opposing evidence considered",
  "source_weight_score": 78.5,
  "confidence": 0.81
}}

Rules:
- If misleading.is_misleading is true, prefer MISLEADING unless the evidence clearly refutes the claim outright.
- If verification_label is source_unavailable or misleading.insufficient_evidence is true, use INSUFFICIENT_EVIDENCE.
- Use UNVERIFIED when evidence exists but does not firmly support or refute the claim.
- Do not use legalistic filler. Avoid phrases like "it should be noted", "based on the available information", "cannot be definitively concluded", or "appears to suggest".
""".strip()


def _run_once(prompt: str, provider: str) -> VerdictAssessment:
    from crewai import Agent, Crew, Process, Task

    llm = build_crewai_llm(provider, temperature=0.0)
    agent = Agent(
        role="Verdict Synthesizer",
        goal="Weigh the evidence, challenge the first conclusion, and return the most defensible verdict.",
        backstory="You are an experienced civic fact-check editor who writes direct, evidence-led verdicts.",
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
            return VerdictAssessment.model_validate_json(clean_text)
        except Exception as exc:
            if attempt >= 1:
                raise RuntimeError(f"Verdict assessment failed validation: {exc}") from exc
            schema_hint = json.dumps(VerdictAssessment.model_json_schema(), indent=2)
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
    raise RuntimeError("Verdict assessment failed.")


def assess_verdict(
    *,
    claim: str,
    verification_label: str,
    matches: list,
    misleading: MisleadingAssessment,
    input_type: str = "text",
) -> VerdictAssessment:
    weight_score = aggregate_weight_score(matches)
    if verification_label == "source_unavailable" or misleading.insufficient_evidence:
        return VerdictAssessment(
            verdict="INSUFFICIENT_EVIDENCE",
            explanation="Trusted sources were not available, so this claim could not be verified yet.",
            countercheck_note="No stronger contradictory evidence was available because retrieval did not complete.",
            source_weight_score=weight_score,
            confidence=0.0,
        )
    if not matches:
        return VerdictAssessment(
            verdict="UNVERIFIED",
            explanation="Trusted sources did not provide enough evidence to support or refute this claim.",
            countercheck_note="No strong contradictory evidence was found in the retrieved material.",
            source_weight_score=weight_score,
            confidence=0.2,
        )

    prompt = _verdict_prompt(
        claim=claim,
        verification_label=verification_label,
        evidence_summary=weighted_evidence_summary(matches),
        misleading=misleading,
        input_type=input_type,
    )

    last_error: Exception | None = None
    for provider in media_llm_provider_order():
        try:
            verdict = _run_once(prompt, provider)
            return verdict.model_copy(update={"source_weight_score": weight_score})
        except Exception as exc:
            last_error = exc
            continue
    raise RuntimeError(f"Verdict assessment failed across providers: {last_error}") from last_error


def is_overly_hedged(text: str) -> bool:
    lowered = (text or "").lower()
    banned_phrases = (
        "it should be noted",
        "based on the available information",
        "cannot be definitively concluded",
        "appears to suggest",
    )
    return any(phrase in lowered for phrase in banned_phrases)
