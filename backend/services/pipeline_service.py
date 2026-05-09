from __future__ import annotations

import asyncio
import json
import os
import re
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from fastapi import HTTPException, UploadFile
from guardrails import Guard
from pydantic import BaseModel

from services.analysis_helpers import (
    INSUFFICIENT_EVIDENCE_VERDICT as _INSUFFICIENT_EVIDENCE_VERDICT,
    MISLEADING_VERDICT as _MISLEADING_VERDICT,
    REFUTED_VERDICT as _REFUTED_VERDICT,
    SUPPORTED_VERDICT as _SUPPORTED_VERDICT,
    UNVERIFIED_VERDICT as _UNVERIFIED_VERDICT,
    clamp_score as _clamp_score,
    compute_trust_score as _compute_trust_score,
    max_pinecone_similarity as _max_pinecone_similarity,
    normalize_analysis_verdict as _normalize_analysis_verdict,
    select_source_url as _select_source_url,
    verdict_assessment as _verdict_assessment,
)
from core.constants import (
    MEDIA_ANALYSIS_ROUTE_OUT_OF_SCOPE_EXIT,
    MEDIA_ANALYSIS_ROUTE_SATIRE_EXIT,
)
from core.logging import get_logger, log_event, stage_duration_ms, stage_start
from crew.classifier_crew import CivicClassifierCrew
from crew.counter_info_crew import CounterInfoCrew
from crew.evidence_crew import EvidenceRetrieverCrew
from crew.monitoring_crew import MonitoringCrew
from crew.output_validator_crew import OutputValidatorCrew
from crew.tools.classify_tool import CivicClassifyTool
from crew.tools.evidence_tool import EvidenceRetrieveTool
from crew.truthmates_crew import TruthMatesCrew
from db.identity import build_analysis_key
from db.mongo import (
    count_validated_posts,
    get_monitor_logs,
    get_validated_posts,
    ping_db,
    save_classified_posts,
    save_counter_info_posts,
    save_monitor_log,
    save_posts,
    save_validated_posts,
    save_verified_posts,
)
from models.schemas import (
    CivicPost,
    ClassifiedPost,
    ClassifyResponse,
    CounterInfoPost,
    GenerateResponse,
    MonitorLog,
    MonitorLogsResponse,
    MonitorSummaryResponse,
    ScrapeResponse,
    SourceReference,
    ValidateResponse,
    ValidatedPost,
    ValidationFlags,
    VerifiedPost,
    VerifyResponse,
)
from services.classification_service import classify_media_content
from services.misleading_service import assess_misleading
from services.observability_service import TraceContext, flush_trace
from services.source_weighting_service import weighted_evidence_summary
from services.verdict_service import assess_verdict, is_overly_hedged


logger = get_logger("truthmates.pipeline")

PIB_RSS_URL = os.environ.get("PIB_RSS_URL", "https://www.pib.gov.in/ViewRss.aspx?reg=1&lang=1")
MYGOV_RSS_URL = os.environ.get("MYGOV_RSS_URL", "https://www.mygov.in/rss-feed/")

_RETRY_BASE_DELAY_SECONDS = 10
_MAX_RETRIES = 5
_PIPELINE_DELAY_SECONDS = 3
_MAX_POSTS_PER_RUN = 10
_MAX_DESCRIPTION_CHARS = 300
_TRANSLATION_MODEL = "ai4bharat/indictrans2-en-hi"
_MAX_TRANSLATION_TOKENS = 256
_VALIDATION_MAX_RETRIES = 2
_MONITOR_MAX_RETRIES = 2
_MONITOR_PREVIEW_CHARS = 1200

_translation_tokenizer: Optional[Any] = None
_translation_model: Optional[Any] = None


class _ValidationItem(BaseModel):
    link: str
    verdict: str
    flags: ValidationFlags


class _ValidationPayload(BaseModel):
    items: list[_ValidationItem]


def _is_rate_limit_error(message: str) -> bool:
    lowered = message.lower()
    return "rate limit" in lowered or "rate_limit" in lowered or "rate_limit_exceeded" in lowered


def _is_queue_error(message: str) -> bool:
    lowered = message.lower()
    return "queue_exceeded" in lowered or "too_many_requests" in lowered or "http 429" in lowered or "error code: 429" in lowered


def _parse_tool_json(text: str) -> list[dict]:
    clean_text = re.sub(r"```(?:json)?\s*", "", text).strip().rstrip("`")
    try:
        parsed = json.loads(clean_text)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


async def _kickoff_with_retry(crew_factory, inputs: dict, fallback_factory=None, *, request_id: str | None = None, stage: str = ""):
    retries = 0
    while True:
        try:
            crew = crew_factory() if callable(crew_factory) else crew_factory
            return crew.kickoff(inputs=inputs)
        except Exception as exc:
            message = str(exc)
            log_event(
                logger,
                "llm_kickoff_error",
                request_id=request_id,
                stage=stage,
                retries=retries,
                error=message,
            )
            if (_is_rate_limit_error(message) or _is_queue_error(message)) and retries < _MAX_RETRIES:
                retries += 1
                await asyncio.sleep(_RETRY_BASE_DELAY_SECONDS)
                continue
            if (_is_rate_limit_error(message) or _is_queue_error(message)) and fallback_factory is not None:
                crew = fallback_factory() if callable(fallback_factory) else fallback_factory
                return crew.kickoff(inputs=inputs)
            raise


def _get_translator() -> tuple[Any, Any]:
    global _translation_tokenizer, _translation_model
    if _translation_tokenizer is None or _translation_model is None:
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

        _translation_tokenizer = AutoTokenizer.from_pretrained(_TRANSLATION_MODEL)
        _translation_model = AutoModelForSeq2SeqLM.from_pretrained(_TRANSLATION_MODEL)
    return _translation_tokenizer, _translation_model


def _translate_en_to_hi(text: str) -> str:
    if not text:
        return text
    try:
        tokenizer, model = _get_translator()
        inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=_MAX_TRANSLATION_TOKENS)
        outputs = model.generate(**inputs, max_length=_MAX_TRANSLATION_TOKENS)
        return tokenizer.decode(outputs[0], skip_special_tokens=True)
    except Exception:
        return text


def _trim_sentences(text: str, max_sentences: int = 3) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return text
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return " ".join(sentences[:max_sentences]).strip()


def _sources_from_matches(matches: list) -> list[str]:
    sources: list[str] = []
    for match in matches:
        url = getattr(match, "source_url", "") or ""
        if url and url not in sources:
            sources.append(url)
    return sources


def _build_source_references(matches: list) -> list[SourceReference]:
    """Build a list of SourceReference objects from evidence matches."""
    refs: list[SourceReference] = []
    seen_urls: set[str] = set()
    for match in matches:
        url = getattr(match, "source_url", "") or ""
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        fact_text = getattr(match, "fact_text", "") or ""
        source_type = getattr(match, "source_type", "web") or "web"
        similarity = float(getattr(match, "similarity", 0.0) or 0.0)
        # Build a meaningful title from the fact text
        title = fact_text[:120].strip() if fact_text else url
        if title and not title.endswith("."):
            title = title.rstrip() + "..."
        refs.append(
            SourceReference(
                title=title,
                url=url,
                source_type=source_type,
                similarity=round(similarity, 4),
            )
        )
    # Add standard reference sources if not already present
    standard_refs = [
        ("PIB Fact Check — Official Government Fact Verification", "https://pib.gov.in/FactCheck.aspx", "official"),
        ("Election Commission of India", "https://www.eci.gov.in", "official"),
    ]
    for title, url, stype in standard_refs:
        if url not in seen_urls:
            refs.append(SourceReference(title=title, url=url, source_type=stype, similarity=None))
    return refs


def _build_detailed_explanation(
    *,
    claim: str,
    verdict: str,
    verdict_reason: str,
    counter_english: str,
    misleading_reason: str,
    matches: list,
    content_summary: str,
    source_weight_summary: str,
) -> str:
    """Build a thorough, human-readable explanation of the claim analysis."""
    parts: list[str] = []

    # Section 1: What was analyzed
    parts.append(f"Claim Analyzed: \"{claim[:200]}\"")
    parts.append("")

    # Section 2: Verdict reasoning
    if verdict_reason:
        parts.append(f"Finding: {verdict_reason}")
    elif counter_english:
        # Strip the "AI Assessment:" prefix if present
        explanation = counter_english
        if explanation.startswith("AI Assessment:"):
            explanation = explanation[len("AI Assessment:"):].strip()
        parts.append(f"Finding: {explanation}")
    parts.append("")

    # Section 3: Misleading details
    if misleading_reason:
        parts.append(f"Why it may be misleading: {misleading_reason}")
        parts.append("")

    # Section 4: Evidence summary
    evidence_found = []
    for match in (matches or []):
        fact = getattr(match, "fact_text", "") or ""
        sim = float(getattr(match, "similarity", 0.0) or 0.0)
        src_url = getattr(match, "source_url", "") or ""
        src_type = getattr(match, "source_type", "") or ""
        if fact:
            type_label = "Government DB" if src_type == "pinecone" else "Fact Check" if src_type == "google_fact_check" else "Web"
            evidence_found.append(f"• [{type_label}] {fact[:150]} (similarity: {sim:.0%}, source: {src_url})")
    if evidence_found:
        parts.append("Evidence Found:")
        parts.extend(evidence_found)
        parts.append("")
    else:
        parts.append("Evidence: No matching verified facts were found in official databases or trusted fact-check sources.")
        parts.append("")

    # Section 5: Weighted source analysis
    if source_weight_summary:
        parts.append(f"Source Analysis: {source_weight_summary}")
        parts.append("")

    # Section 6: Verdict conclusion
    verdict_labels = {
        "SUPPORTED": "This claim is SUPPORTED by official sources and verified evidence.",
        "REFUTED": "This claim is REFUTED — trusted sources contradict it.",
        "MISLEADING": "This claim is MISLEADING — while it may contain partial truths, it distorts the overall picture.",
        "UNVERIFIED": "This claim is UNVERIFIED — we could not find enough evidence to confirm or deny it.",
        "INSUFFICIENT_EVIDENCE": "INSUFFICIENT EVIDENCE — trusted sources did not provide enough data to verify this claim.",
        "SATIRE": "This content is identified as SATIRE and is not a literal factual claim.",
        "OUT_OF_SCOPE": "This content is OUT OF SCOPE for civic fact-checking.",
    }
    conclusion = verdict_labels.get(verdict, f"Verdict: {verdict}")
    parts.append(f"Conclusion: {conclusion}")

    return "\n".join(parts)


def _analysis_source_ref(*, claim: str, input_type: str = "text", source_ref: str = "") -> tuple[str, str]:
    stable_source = (source_ref or "").strip() or claim
    analysis_key = build_analysis_key(claim=claim, input_type=input_type, source_ref=stable_source)
    return analysis_key, stable_source


def _extract_confidence(output) -> Optional[float]:
    values: list[float] = []
    if isinstance(output, list):
        for item in output:
            if isinstance(item, dict) and "confidence" in item:
                values.append(_clamp_score(item.get("confidence")))
    elif isinstance(output, dict):
        posts = output.get("posts")
        if isinstance(posts, list):
            for item in posts:
                if isinstance(item, dict) and "confidence" in item:
                    values.append(_clamp_score(item.get("confidence")))
    return min(values) if values else None


def _has_hallucination_flags(output) -> bool:
    if isinstance(output, list):
        for item in output:
            if isinstance(item, dict):
                flags = item.get("flags") or {}
                if flags.get("hallucinated_stats") is True or item.get("hallucinated_stats") is True:
                    return True
    elif isinstance(output, dict):
        posts = output.get("posts")
        if isinstance(posts, list):
            return _has_hallucination_flags(posts)
        items = output.get("items")
        if isinstance(items, list):
            return _has_hallucination_flags(items)
    return False


def _is_output_complete(output) -> bool:
    if output is None:
        return False
    if isinstance(output, list):
        return len(output) > 0
    if isinstance(output, dict):
        if "posts" in output and isinstance(output["posts"], list):
            return len(output["posts"]) > 0
        if "items" in output and isinstance(output["items"], list):
            return len(output["items"]) > 0
        return len(output.keys()) > 0
    return True


def _truncate_for_log(value, max_chars: int = 4000) -> str:
    try:
        text = json.dumps(value, ensure_ascii=True)
    except Exception:
        text = str(value)
    return text[:max_chars] + "..." if len(text) > max_chars else text


async def _monitor_review(agent_name: str, input_payload, output_payload, checks: dict, *, request_id: str | None = None) -> str:
    crew_instance = MonitoringCrew()
    fallback_instance = MonitoringCrew(llm_provider="together")
    inputs = {
        "agent_name": agent_name,
        "checks_json": json.dumps(checks, ensure_ascii=True),
        "error": checks.get("error") or "",
        "output_preview": _truncate_for_log(output_payload, _MONITOR_PREVIEW_CHARS),
    }
    result = await _kickoff_with_retry(crew_instance.crew, inputs, fallback_factory=fallback_instance.crew, request_id=request_id, stage=f"monitor_{agent_name}")
    raw_text: str = result.raw if hasattr(result, "raw") else str(result)
    clean_text = re.sub(r"```(?:json)?\s*", "", raw_text).strip().rstrip("`")
    try:
        payload = json.loads(clean_text)
        status = (payload.get("status") or "").upper()
        if status in {"PASS", "FAIL"}:
            return status
    except Exception:
        pass
    return "PASS" if checks.get("pass") else "FAIL"


def _default_validation_flags() -> ValidationFlags:
    return ValidationFlags(
        contradicts_pib_fact=False,
        invalid_source_url=False,
        trust_score_mismatch=False,
        missing_hindi=False,
        hallucinated_stats=False,
        overly_hedged_language=False,
    )


def _build_validation_payload(counter_posts: list[CounterInfoPost]) -> dict[str, list[dict]]:
    items: list[dict] = []
    for post in counter_posts[:_MAX_POSTS_PER_RUN]:
        flags = _default_validation_flags()
        verdict = post.verdict_hint or (
            "MISLEADING" if post.misleading_reason else "SUPPORTED"
        )
        if post.verdict_hint in {_SUPPORTED_VERDICT, _REFUTED_VERDICT, _MISLEADING_VERDICT, _UNVERIFIED_VERDICT, _INSUFFICIENT_EVIDENCE_VERDICT}:
            verdict = post.verdict_hint
        if is_overly_hedged(post.correction_en):
            flags = flags.model_copy(update={"overly_hedged_language": True})
        items.append(
            {
                "link": post.link,
                "verdict": verdict,
                "flags": flags.model_dump(mode="json"),
            }
        )
    return {"items": items}


def _text_exit_post(
    *,
    claim: str,
    verdict: str,
    explanation: str,
    content_category: str,
    analysis_route: str,
    source_ref: str = "",
) -> ValidatedPost:
    analysis_key, stable_source_ref = _analysis_source_ref(
        claim=claim,
        input_type="text",
        source_ref=source_ref or claim,
    )
    return ValidatedPost(
        claim=claim,
        analysis_key=analysis_key,
        source_ref=stable_source_ref,
        verdict=verdict,
        trust_score=55.0 if verdict == "SATIRE" else 50.0,
        counter_english=explanation,
        counter_hindi=_translate_en_to_hi(explanation),
        sources=[],
        flags=_default_validation_flags(),
        llm_confidence=0.0,
        source_match=0.0,
        source_found=0.0,
        deepfake_score=0.0,
        crowd_reports=0.0,
        input_type="text",
        content_summary=f"Text input analyzed: {claim[:100]}",
        content_category=content_category,
        analysis_route=analysis_route,
        pipeline_status="short_circuit",
        detailed_explanation=_build_detailed_explanation(
            claim=claim,
            verdict=verdict,
            verdict_reason=explanation,
            counter_english=explanation,
            misleading_reason="",
            matches=[],
            content_summary=f"Text input analyzed: {claim[:100]}",
            source_weight_summary="",
        ),
        source_references=_build_source_references([]),
    )


def _enrich_verified_posts(verified_posts: list[VerifiedPost], *, input_type: str = "text", content_summary: str = "") -> list[VerifiedPost]:
    enriched: list[VerifiedPost] = []
    for post in verified_posts:
        misleading = assess_misleading(
            claim=post.title,
            matches=post.matches,
            content_summary=content_summary or post.description,
            input_type=input_type,
        )
        verdict = assess_verdict(
            claim=post.title,
            verification_label=post.verification_label,
            matches=post.matches,
            misleading=misleading,
            input_type=input_type,
        )
        enriched.append(
            post.model_copy(
                update={
                    "misleading_reason": misleading.misleading_reason,
                    "source_weight_score": verdict.source_weight_score,
                    "countercheck_note": verdict.countercheck_note,
                    "verdict_hint": verdict.verdict,
                }
            )
        )
    return enriched


async def _log_monitor_decision(agent_name: str, input_payload, output_payload, status: str, retries: int, checks: dict) -> None:
    await save_monitor_log(
        {
            "agent_name": agent_name,
            "input": _truncate_for_log(input_payload),
            "output": _truncate_for_log(output_payload),
            "status": status,
            "retries": retries,
            "checks": checks,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )


async def _run_with_monitor(agent_name: str, input_payload, runner, *, request_id: str | None = None):
    retries = 0
    while True:
        output_payload = None
        error_message = ""
        try:
            output_payload = await runner()
        except Exception as exc:
            error_message = str(exc)
        confidence = _extract_confidence(output_payload)
        confidence_ok = True if confidence is None else confidence >= 0.75
        checks = {
            "complete": _is_output_complete(output_payload),
            "confidence_ok": confidence_ok,
            "hallucination_flags": _has_hallucination_flags(output_payload),
            "error": error_message,
        }
        checks["pass"] = checks["complete"] and checks["confidence_ok"] and not checks["hallucination_flags"] and not checks["error"]
        status = await _monitor_review(agent_name, input_payload, output_payload, checks, request_id=request_id)
        await _log_monitor_decision(agent_name, input_payload, output_payload, status, retries, checks)
        if status == "PASS" and checks["pass"]:
            return output_payload
        if retries >= _MONITOR_MAX_RETRIES:
            raise HTTPException(status_code=502, detail=f"Monitoring failed for {agent_name} after retries.")
        retries += 1


async def health_check_payload(*, request_id: str | None = None) -> dict:
    started = stage_start()
    db_ok = await ping_db()
    payload = {
        "service": "TruthMates API",
        "status": "running",
        "database": "connected" if db_ok else "unreachable",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    log_event(logger, "stage_complete", request_id=request_id, stage="health_check", duration_ms=stage_duration_ms(started))
    return payload


async def monitor_logs_payload(*, request_id: str | None = None) -> MonitorLogsResponse:
    started = stage_start()
    logs = await get_monitor_logs(limit=200)
    clean_logs = []
    for log in logs:
        log["id"] = str(log.pop("_id"))
        clean_logs.append(log)
    log_event(logger, "stage_complete", request_id=request_id, stage="monitor_logs", duration_ms=stage_duration_ms(started), count=len(clean_logs))
    return MonitorLogsResponse(status="success", count=len(clean_logs), logs=[MonitorLog(**log) for log in clean_logs])


async def monitor_status_payload(*, request_id: str | None = None) -> dict:
    started = stage_start()
    logs = await get_monitor_logs(limit=200)
    last_by_agent: dict[str, str] = {}
    for log in logs:
        name = log.get("agent_name")
        if name and name not in last_by_agent:
            last_by_agent[name] = log.get("status", "UNKNOWN")
    overall = "healthy" if all(v == "PASS" for v in last_by_agent.values()) else "degraded"
    log_event(logger, "stage_complete", request_id=request_id, stage="monitor_status", duration_ms=stage_duration_ms(started), overall=overall)
    return {"status": overall, "agents": last_by_agent, "timestamp": datetime.now(timezone.utc).isoformat()}


async def monitor_summary_payload(*, request_id: str | None = None) -> MonitorSummaryResponse:
    started = stage_start()
    logs = await get_monitor_logs(limit=500)
    validated_posts = await get_validated_posts(limit=500)
    total_validated = await count_validated_posts()

    verdict_counts: dict[str, int] = {}
    trust_scores: list[float] = []
    timeline_buckets: dict[str, dict] = {}
    for post in validated_posts:
        verdict = (post.get("verdict") or "UNKNOWN").upper()
        verdict_counts[verdict] = verdict_counts.get(verdict, 0) + 1
        try:
            trust_scores.append(float(post.get("trust_score") or 0.0))
        except (TypeError, ValueError):
            pass
        validated_at = str(post.get("validated_at") or "")[:10]
        if validated_at:
            bucket = timeline_buckets.setdefault(validated_at, {"date": validated_at, "count": 0})
            bucket["count"] += 1

    monitor_status_counts: dict[str, int] = {}
    for log in logs:
        status = (log.get("status") or "UNKNOWN").upper()
        monitor_status_counts[status] = monitor_status_counts.get(status, 0) + 1

    timeline = sorted(timeline_buckets.values(), key=lambda item: item["date"])[-7:]
    average_trust_score = round(sum(trust_scores) / len(trust_scores), 2) if trust_scores else 0.0
    response = MonitorSummaryResponse(
        status="success",
        total_validated=total_validated,
        verdict_counts=verdict_counts,
        monitor_status_counts=monitor_status_counts,
        average_trust_score=average_trust_score,
        timeline=timeline,
    )
    log_event(
        logger,
        "stage_complete",
        request_id=request_id,
        stage="monitor_summary",
        duration_ms=stage_duration_ms(started),
        total_validated=total_validated,
    )
    return response


async def analyze_claim(
    claim: str,
    *,
    request_id: str | None = None,
    source_ref: str = "",
) -> ValidateResponse:
    claim_text = (claim or "").strip()
    if not claim_text:
        raise HTTPException(status_code=422, detail="Claim text is required.")

    source_reference = (source_ref or "").strip()

    # Observability trace context — wraps each stage
    _trace = TraceContext(claim_text)

    started = stage_start()
    _span_classify = _trace.begin_span("content_classifier", {"claim": claim_text, "input_type": "text"})
    classification, provider = await asyncio.to_thread(
        classify_media_content,
        claim_text,
        title=claim_text,
        input_type="text",
    )
    _trace.end_span(
        _span_classify,
        {"content_category": classification.content_category, "analysis_route": classification.analysis_route, "provider": provider},
        status="pass",
    )
    log_event(
        logger,
        "stage_complete",
        request_id=request_id,
        stage="text_content_classification",
        duration_ms=stage_duration_ms(started),
        provider=provider,
        content_category=classification.content_category,
        analysis_route=classification.analysis_route,
    )

    if classification.analysis_route == MEDIA_ANALYSIS_ROUTE_SATIRE_EXIT:
        post = _text_exit_post(
            claim=claim_text,
            verdict="SATIRE",
            explanation="This text reads like satire or parody, so it is not being treated as a literal civic misinformation claim.",
            content_category=classification.content_category,
            analysis_route=classification.analysis_route,
            source_ref=source_reference,
        )
        await save_validated_posts([post.model_dump()])
        _trace.final_verdict = "SATIRE"
        _trace.trust_score = float(post.trust_score or 0.0)
        await flush_trace(_trace)
        return ValidateResponse(status="success", count=1, posts=[post])

    if classification.analysis_route == MEDIA_ANALYSIS_ROUTE_OUT_OF_SCOPE_EXIT:
        post = _text_exit_post(
            claim=claim_text,
            verdict="OUT_OF_SCOPE",
            explanation="This text is outside the civic and government fact-checking scope, so the verification pipeline stopped before evidence retrieval.",
            content_category=classification.content_category,
            analysis_route=classification.analysis_route,
            source_ref=source_reference,
        )
        await save_validated_posts([post.model_dump()])
        _trace.final_verdict = "OUT_OF_SCOPE"
        _trace.trust_score = float(post.trust_score or 0.0)
        await flush_trace(_trace)
        return ValidateResponse(status="success", count=1, posts=[post])

    now = datetime.now(timezone.utc)
    manual_post = CivicPost(
        title=claim_text,
        description=claim_text[:_MAX_DESCRIPTION_CHARS],
        link=source_reference or f"manual://{uuid4()}",
        pub_date=None,
        source="Manual",
        scraped_at=now,
    )
    posts_json = json.dumps([manual_post.model_dump(mode="json")], ensure_ascii=True)

    started = stage_start()
    _span_civic = _trace.begin_span("civic_classifier_tool", {"posts_count": 1})
    classifier_tool = CivicClassifyTool()
    classified_items = _parse_tool_json(classifier_tool._run(posts_json))
    _trace.end_span(_span_civic, {"classified_count": len(classified_items)}, status="pass" if classified_items else "fail")
    log_event(logger, "stage_complete", request_id=request_id, stage="classify_tool", duration_ms=stage_duration_ms(started), provider="local_model")
    if not classified_items:
        _trace.final_verdict = "UNCLASSIFIED"
        await flush_trace(_trace)
        return ValidateResponse(status="success", count=0, posts=[])
    civic_posts = [ClassifiedPost(**item) for item in classified_items if item.get('label') == 'civic']
    await save_classified_posts([p.model_dump() for p in civic_posts])
    if not civic_posts:
        _trace.final_verdict = "NOT_CIVIC"
        await flush_trace(_trace)
        return ValidateResponse(status='success', count=0, posts=[])

    started = stage_start()
    _span_evidence = _trace.begin_span("evidence_retriever_tool", {"civic_posts_count": len(civic_posts)})
    evidence_tool = EvidenceRetrieveTool()
    evidence_payload = json.dumps([p.model_dump(mode="json") for p in civic_posts], ensure_ascii=True)
    verified_items = _parse_tool_json(evidence_tool._run(evidence_payload))
    _trace.end_span(_span_evidence, {"verified_count": len(verified_items)}, status="pass" if verified_items else "fail")
    log_event(logger, "stage_complete", request_id=request_id, stage="evidence_tool", duration_ms=stage_duration_ms(started), provider="pinecone_google_factcheck")

    # If evidence retrieval found no matches, short-circuit with a
    # detailed, claim-specific result instead of running empty data
    # through counter-info + validation (which produces generic text).
    if not verified_items:
        log_event(logger, "evidence_no_matches", request_id=request_id, detail="Short-circuit with detailed unverified result")
        explanation = (
            f"No matching verified facts were found for this claim in official databases (PIB, MyGov) "
            f"or trusted fact-check sources. This claim could not be independently confirmed or denied."
        )
        analysis_key, stable_ref = _analysis_source_ref(
            claim=claim_text, input_type="text", source_ref=source_reference or claim_text,
        )
        verdict_reason_text = f"No verified facts matched this claim in our database. The claim was classified as '{classification.content_category}'."
        post = ValidatedPost(
            claim=claim_text,
            analysis_key=analysis_key,
            source_ref=stable_ref,
            verdict="INSUFFICIENT_EVIDENCE",
            trust_score=45.0,
            counter_english=explanation,
            counter_hindi=_translate_en_to_hi(explanation),
            sources=["https://pib.gov.in/FactCheck.aspx", "https://www.eci.gov.in"],
            flags=_default_validation_flags(),
            llm_confidence=65.0,
            source_match=0.0,
            source_found=0.0,
            deepfake_score=0.0,
            crowd_reports=0.0,
            input_type="text",
            content_summary=classification.summary or f"Text analyzed: {claim_text[:100]}",
            content_category=classification.content_category,
            analysis_route=classification.analysis_route,
            pipeline_status="no_evidence_match",
            verdict_reason=verdict_reason_text,
            detailed_explanation=_build_detailed_explanation(
                claim=claim_text,
                verdict="INSUFFICIENT_EVIDENCE",
                verdict_reason=verdict_reason_text,
                counter_english=explanation,
                misleading_reason="",
                matches=[],
                content_summary=classification.summary or f"Text analyzed: {claim_text[:100]}",
                source_weight_summary="",
            ),
            source_references=_build_source_references([]),
        )
        await save_validated_posts([post.model_dump()])
        _trace.final_verdict = "INSUFFICIENT_EVIDENCE"
        _trace.trust_score = 45.0
        await flush_trace(_trace)
        return ValidateResponse(status="success", count=1, posts=[post])

    verified_posts = [
        VerifiedPost(
            **item,
            content_category=classification.content_category,
            analysis_route=classification.analysis_route,
        )
        for item in verified_items
    ]
    verified_posts = await asyncio.to_thread(
        _enrich_verified_posts,
        verified_posts,
        input_type="text",
        content_summary=classification.summary,
    )
    await save_verified_posts([p.model_dump() for p in verified_posts])
    counter_posts = await run_generate(VerifyResponse(status="manual", count=len(verified_posts), posts=verified_posts), use_monitor=False, request_id=request_id)
    result = await run_validate(counter_posts, use_monitor=False, request_id=request_id)

    # Finalise observability trace with the outcome of the full pipeline
    if result.posts:
        first_post = result.posts[0]
        _trace.final_verdict = getattr(first_post, "verdict", "")
        _trace.trust_score = float(getattr(first_post, "trust_score", 0.0) or 0.0)
        flags_obj = getattr(first_post, "flags", None)
        if flags_obj is not None:
            try:
                _trace.flags = flags_obj.model_dump() if hasattr(flags_obj, "model_dump") else dict(flags_obj)
            except Exception:
                _trace.flags = {}
    await flush_trace(_trace)
    return result


async def scrape_pipeline(*, request_id: str | None = None) -> ValidateResponse:
    started = stage_start()
    crew_instance = TruthMatesCrew()
    fallback_instance = TruthMatesCrew(llm_provider="together")

    async def _run_scraper():
        result = await _kickoff_with_retry(
            crew_instance.crew,
            {"pib_rss_url": PIB_RSS_URL, "mygov_rss_url": MYGOV_RSS_URL},
            fallback_factory=fallback_instance.crew,
            request_id=request_id,
            stage="scrape",
        )
        raw_text = result.raw if hasattr(result, "raw") else str(result)
        return _parse_tool_json(raw_text)

    posts_data = await _run_with_monitor("scraper", {"feeds": [PIB_RSS_URL, MYGOV_RSS_URL]}, _run_scraper, request_id=request_id)
    log_event(logger, "stage_complete", request_id=request_id, stage="scrape", duration_ms=stage_duration_ms(started), provider="crewai")
    posts = [CivicPost(**item) for item in (posts_data or [])[:_MAX_POSTS_PER_RUN]]
    await save_posts([p.model_dump() for p in posts])
    await asyncio.sleep(_PIPELINE_DELAY_SECONDS)
    return await classify_pipeline(ScrapeResponse(status="success", count=len(posts), posts=posts), request_id=request_id)


async def classify_pipeline(scrape_response: ScrapeResponse, *, request_id: str | None = None) -> ValidateResponse:
    started = stage_start()
    crew_instance = CivicClassifierCrew()
    fallback_instance = CivicClassifierCrew(llm_provider="together")
    posts_json = json.dumps([p.model_dump(mode="json") for p in scrape_response.posts[:_MAX_POSTS_PER_RUN]], ensure_ascii=True)

    async def _run_classifier():
        result = await _kickoff_with_retry(crew_instance.crew, {"posts_json": posts_json}, fallback_factory=fallback_instance.crew, request_id=request_id, stage="classify")
        raw_text = result.raw if hasattr(result, "raw") else str(result)
        return _parse_tool_json(raw_text)

    classified_data = await _run_with_monitor("classifier", {"posts_json": posts_json}, _run_classifier, request_id=request_id)
    log_event(logger, "stage_complete", request_id=request_id, stage="classify", duration_ms=stage_duration_ms(started), provider="crewai")
    classified_posts = [ClassifiedPost(**item) for item in classified_data or [] if item.get("label") == "civic"]
    await save_classified_posts([p.model_dump() for p in classified_posts])
    if not classified_posts:
        return ValidateResponse(status="success", count=0, posts=[])
    await asyncio.sleep(_PIPELINE_DELAY_SECONDS)
    return await verify_pipeline(ClassifyResponse(status="success", count=len(classified_posts), posts=classified_posts), request_id=request_id)


async def verify_pipeline(classify_response: ClassifyResponse, *, request_id: str | None = None) -> ValidateResponse:
    started = stage_start()
    crew_instance = EvidenceRetrieverCrew()
    fallback_instance = EvidenceRetrieverCrew(llm_provider="together")
    posts_json = json.dumps([p.model_dump(mode="json") for p in classify_response.posts[:_MAX_POSTS_PER_RUN]], ensure_ascii=True)

    async def _run_verifier():
        result = await _kickoff_with_retry(crew_instance.crew, {"posts_json": posts_json}, fallback_factory=fallback_instance.crew, request_id=request_id, stage="verify")
        raw_text = result.raw if hasattr(result, "raw") else str(result)
        return _parse_tool_json(raw_text)

    verified_data = await _run_with_monitor("verifier", {"posts_json": posts_json}, _run_verifier, request_id=request_id)
    log_event(logger, "stage_complete", request_id=request_id, stage="verify", duration_ms=stage_duration_ms(started), provider="crewai")
    verified_posts = [VerifiedPost(**item) for item in verified_data or []]
    verified_posts = await asyncio.to_thread(_enrich_verified_posts, verified_posts, input_type="text")
    await save_verified_posts([p.model_dump() for p in verified_posts])
    if not verified_posts:
        return ValidateResponse(status="success", count=0, posts=[])
    await asyncio.sleep(_PIPELINE_DELAY_SECONDS)
    counter_posts = await run_generate(VerifyResponse(status="success", count=len(verified_posts), posts=verified_posts), request_id=request_id)
    return await run_validate(counter_posts, request_id=request_id)


async def run_generate(verify_response: VerifyResponse, use_monitor: bool = True, *, request_id: str | None = None) -> list[CounterInfoPost]:
    started = stage_start()
    crew_instance = CounterInfoCrew()
    fallback_instance = CounterInfoCrew(llm_provider="together")
    trimmed_posts: list[dict] = []
    for post in verify_response.posts[:_MAX_POSTS_PER_RUN]:
        data = post.model_dump(mode="json")
        description = (data.get("description") or "").strip()
        if len(description) > _MAX_DESCRIPTION_CHARS:
            data["description"] = description[:_MAX_DESCRIPTION_CHARS].rstrip()
        data["matches"] = (data.get("matches") or [])[:3]
        trimmed_posts.append(data)
    posts_json = json.dumps(trimmed_posts, ensure_ascii=True)

    async def _run_counter_info():
        # 5-second pre-delay to avoid hitting rate limits on an already-busy LLM
        await asyncio.sleep(5)
        inputs = {"posts_json": posts_json}
        # Exponential backoff specific to counter_info: 5s → 10s → 20s → 40s → 80s
        _ci_max_retries = 5
        _ci_base_delay = 5
        retries = 0
        last_exc: Exception | None = None
        while retries <= _ci_max_retries:
            try:
                result = await _kickoff_with_retry(
                    crew_instance.crew,
                    inputs,
                    fallback_factory=fallback_instance.crew,
                    request_id=request_id,
                    stage="generate",
                )
                break  # success
            except Exception as exc:
                last_exc = exc
                if retries < _ci_max_retries and (_is_rate_limit_error(str(exc)) or _is_queue_error(str(exc))):
                    delay = _ci_base_delay * (2 ** retries)  # 5, 10, 20, 40, 80
                    log_event(
                        logger,
                        "counter_info_backoff",
                        request_id=request_id,
                        retry=retries + 1,
                        delay_seconds=delay,
                        error=str(exc),
                    )
                    await asyncio.sleep(delay)
                    retries += 1
                else:
                    raise
        if last_exc and retries > _ci_max_retries:
            raise last_exc

        raw_text = result.raw if hasattr(result, "raw") else str(result)
        clean_text = re.sub(r"```(?:json)?\s*", "", raw_text).strip().rstrip("`")
        try:
            data = json.loads(clean_text)
        except json.JSONDecodeError:
            match = re.search(r"\[.*\]", clean_text, re.DOTALL)
            if match:
                data = json.loads(match.group())
            else:
                raise HTTPException(status_code=502, detail="Generator returned output that could not be parsed as JSON.")
        if not isinstance(data, list):
            raise HTTPException(status_code=502, detail="Generator output is not a JSON array.")
        return data


    fallback_generation = False
    try:
        correction_data = await _run_with_monitor("counter_info", {"posts_json": posts_json}, _run_counter_info, request_id=request_id) if use_monitor else await _run_counter_info()
    except Exception as exc:
        fallback_generation = True
        log_event(
            logger,
            "stage_failed",
            level="warning",
            request_id=request_id,
            stage="generate",
            error=str(exc),
            fallback="deterministic",
        )
        correction_data = []
    corrections_by_link = {(item.get("link") or "").strip(): (item.get("correction_body") or "").strip() for item in correction_data if (item.get("link") or "").strip() and (item.get("correction_body") or "").strip()}
    counter_posts: list[CounterInfoPost] = []
    for post in verify_response.posts[:_MAX_POSTS_PER_RUN]:
        source_url = _select_source_url(post.matches)
        source_text = source_url or "no official source found"
        is_verified = post.verification_label == "verified" and bool(source_url)
        correction_body = corrections_by_link.get(post.link, "").strip()
        if post.misleading_reason:
            correction_body = f"This claim is misleading because {post.misleading_reason}."
        elif post.verdict_hint == _REFUTED_VERDICT:
            correction_body = "Trusted sources contradict this claim."
        elif post.verdict_hint == _INSUFFICIENT_EVIDENCE_VERDICT:
            correction_body = "Trusted sources were unavailable, so this claim could not be verified."
        elif not is_verified:
            correction_body = "No official source found for this claim."
        elif not correction_body:
            correction_body = "Official sources confirm this claim."
        correction_body = _trim_sentences(correction_body, 3)
        correction_en = f"{correction_body} Source: {source_text}"
        correction_hi = f"{_translate_en_to_hi(correction_body)} Source: {source_text}"
        trust_score, trust_label = _compute_trust_score(post)
        counter_posts.append(CounterInfoPost(**post.model_dump(), correction_en=correction_en, correction_hi=correction_hi, trust_score=trust_score, trust_label=trust_label))
    await save_counter_info_posts([p.model_dump() for p in counter_posts])
    log_event(
        logger,
        "stage_complete",
        request_id=request_id,
        stage="generate",
        duration_ms=stage_duration_ms(started),
        provider="deterministic_fallback" if fallback_generation else "crewai",
    )
    return counter_posts


async def generate_pipeline(verify_response: VerifyResponse, *, request_id: str | None = None) -> ValidateResponse:
    counter_posts = await run_generate(verify_response, request_id=request_id)
    return await validate_pipeline(GenerateResponse(status="success", count=len(counter_posts), posts=counter_posts), request_id=request_id)


async def run_validate(counter_posts: list[CounterInfoPost], use_monitor: bool = True, *, request_id: str | None = None) -> ValidateResponse:
    started = stage_start()
    crew_instance = OutputValidatorCrew()
    fallback_instance = OutputValidatorCrew(llm_provider="together")
    posts_json = json.dumps([post.model_dump(mode="json") for post in counter_posts[:_MAX_POSTS_PER_RUN]], ensure_ascii=True)

    async def _run_validator():
        result = await _kickoff_with_retry(crew_instance.crew, {"posts_json": posts_json}, fallback_factory=fallback_instance.crew, request_id=request_id, stage="validate")
        raw_text = result.raw if hasattr(result, "raw") else str(result)
        clean_text = re.sub(r"```(?:json)?\s*", "", raw_text).strip().rstrip("`")
        validated_payload = None
        if hasattr(Guard, "from_pydantic"):
            try:
                guard = Guard.from_pydantic(_ValidationPayload)
                outcome = guard.parse(clean_text)
                validated_payload = outcome.validated_output
            except Exception:
                validated_payload = None
        if validated_payload is None:
            try:
                parsed = _ValidationPayload.model_validate_json(clean_text)
                validated_payload = parsed.model_dump()
            except Exception:
                try:
                    validated_payload = json.loads(clean_text)
                except json.JSONDecodeError as exc:
                    raise HTTPException(status_code=502, detail="Validator returned output that could not be parsed as JSON.") from exc
        if isinstance(validated_payload, dict) and "items" in validated_payload:
            return validated_payload
        raise HTTPException(status_code=502, detail="Validator output is missing items array.")

    fallback_validation = False
    try:
        validated_payload = await _run_with_monitor("validator", {"posts_json": posts_json}, _run_validator, request_id=request_id) if use_monitor else await _run_validator()
    except Exception as exc:
        fallback_validation = True
        log_event(
            logger,
            "stage_failed",
            level="warning",
            request_id=request_id,
            stage="validate",
            error=str(exc),
            fallback="deterministic",
        )
        validated_payload = _build_validation_payload(counter_posts)
    if hasattr(validated_payload, "model_dump"):
        validated_payload = validated_payload.model_dump()
    items = validated_payload["items"] if isinstance(validated_payload, dict) and "items" in validated_payload else validated_payload
    flags_by_link: dict[str, ValidationFlags] = {}
    verdict_by_link: dict[str, str] = {}
    for item in items or []:
        try:
            parsed = _ValidationItem(**item)
            flags_by_link[parsed.link] = parsed.flags
            verdict_by_link[parsed.link] = _normalize_analysis_verdict(parsed.verdict)
        except Exception:
            continue
    validated_posts: list[ValidatedPost] = []
    for post in counter_posts[:_MAX_POSTS_PER_RUN]:
        flags = flags_by_link.get(post.link, _default_validation_flags())
        misleading = assess_misleading(
            claim=post.title,
            matches=post.matches,
            content_summary=post.description,
            correction_text=post.correction_en,
            input_type="text",
        )
        verdict_assessment = assess_verdict(
            claim=post.title,
            verification_label=post.verification_label,
            matches=post.matches,
            misleading=misleading,
            input_type="text",
        )
        if is_overly_hedged(post.correction_en):
            flags = flags.model_copy(update={"overly_hedged_language": True})
        verdict = verdict_by_link.get(post.link, post.verdict_hint or verdict_assessment.verdict)
        sources = _sources_from_matches(post.matches)
        analysis_key, source_ref = _analysis_source_ref(claim=post.title, input_type="text", source_ref=post.link)
        llm_conf = round(_clamp_score(getattr(post, "confidence", 0.0)) * 100, 1)
        best_sim = round(_max_pinecone_similarity(post.matches) * 100, 1)
        has_source = 100.0 if _select_source_url(post.matches) else 0.0
        dfake = round(_clamp_score(getattr(post, "deepfake_score", 0.0)) * 100, 1)
        crowd = round(_clamp_score(getattr(post, "crowdsource_reports", 0.0)) * 100, 1)
        correction_en = f"{_verdict_assessment(verdict)} {post.correction_en}"
        sw_summary = weighted_evidence_summary(post.matches)
        validated_posts.append(
            ValidatedPost(
                claim=post.title,
                analysis_key=analysis_key,
                source_ref=source_ref,
                verdict=verdict,
                trust_score=post.trust_score,
                counter_english=correction_en,
                counter_hindi=post.correction_hi,
                sources=sources,
                flags=flags,
                llm_confidence=llm_conf,
                source_match=best_sim,
                source_found=has_source,
                deepfake_score=dfake,
                crowd_reports=crowd,
                content_summary=f"Text input analyzed: {post.title[:100]}",
                content_category=post.content_category,
                analysis_route=post.analysis_route,
                pipeline_status="complete",
                misleading_reason=misleading.misleading_reason,
                verdict_reason=verdict_assessment.explanation,
                detailed_explanation=_build_detailed_explanation(
                    claim=post.title,
                    verdict=verdict,
                    verdict_reason=verdict_assessment.explanation,
                    counter_english=correction_en,
                    misleading_reason=misleading.misleading_reason or "",
                    matches=post.matches,
                    content_summary=f"Text input analyzed: {post.title[:100]}",
                    source_weight_summary=sw_summary,
                ),
                source_references=_build_source_references(post.matches),
                source_weight_score=verdict_assessment.source_weight_score,
                source_weight_summary=sw_summary,
                countercheck_note=verdict_assessment.countercheck_note,
            )
        )
    await save_validated_posts([p.model_dump() for p in validated_posts])
    log_event(
        logger,
        "stage_complete",
        request_id=request_id,
        stage="validate",
        duration_ms=stage_duration_ms(started),
        provider="deterministic_fallback" if fallback_validation else "crewai",
    )
    return ValidateResponse(status="success", count=len(validated_posts), posts=validated_posts)


async def validate_pipeline(generate_response: GenerateResponse, *, request_id: str | None = None) -> ValidateResponse:
    counter_posts = generate_response.posts
    validation_response = ValidateResponse(status="success", count=0, posts=[])
    for attempt in range(_VALIDATION_MAX_RETRIES + 1):
        validation_response = await run_validate(counter_posts, request_id=request_id)
        flagged_links = {
            post.claim
            for post in validation_response.posts
            if any([
                post.flags.contradicts_pib_fact,
                post.flags.invalid_source_url,
                post.flags.trust_score_mismatch,
                post.flags.missing_hindi,
                post.flags.hallucinated_stats,
                post.flags.overly_hedged_language,
            ])
        }
        if not flagged_links or attempt >= _VALIDATION_MAX_RETRIES:
            return validation_response
        retry_posts = [post for post in generate_response.posts if post.title in flagged_links]
        verify_payload = VerifyResponse(status="retry", count=len(retry_posts), posts=[VerifiedPost(**p.model_dump(exclude={"correction_en", "correction_hi", "trust_score", "trust_label"})) for p in retry_posts])
        counter_posts = await run_generate(verify_payload, request_id=request_id)
    return validation_response


async def analyze_video_url(url: str, *, request_id: str | None = None) -> ValidateResponse:
    from services.media_pipeline_service import analyze_video_url as analyze_media_video_url

    return await analyze_media_video_url(
        url,
        request_id=request_id,
        translate_text=_translate_en_to_hi,
        verdict_assessment=_verdict_assessment,
    )


async def analyze_audio_upload(file: UploadFile, *, request_id: str | None = None) -> ValidateResponse:
    from services.media_pipeline_service import analyze_audio_upload as analyze_media_audio_upload

    return await analyze_media_audio_upload(
        file,
        request_id=request_id,
        translate_text=_translate_en_to_hi,
        verdict_assessment=_verdict_assessment,
    )
