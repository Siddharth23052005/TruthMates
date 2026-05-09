from __future__ import annotations

import asyncio
import os
import shutil
import tempfile
from typing import Callable

from fastapi import HTTPException, UploadFile

from core.constants import (
    MEDIA_ALLOWED_AUDIO_EXTENSIONS,
    MEDIA_ANALYSIS_ROUTE_OUT_OF_SCOPE_EXIT,
    MEDIA_ANALYSIS_ROUTE_SATIRE_EXIT,
    MEDIA_CONTENT_CATEGORY_OUT_OF_SCOPE,
    MEDIA_CONTENT_CATEGORY_SATIRE,
)
from core.logging import get_logger, log_event, stage_duration_ms, stage_start
from db.identity import build_analysis_key
from db.mongo import save_validated_posts
from models.schemas import SourceReference, ValidateResponse, ValidatedPost, ValidationFlags, VideoUnderstanding
from services.classification_service import ContentClassification, classify_media_content
from services.misleading_service import assess_misleading
from services.source_weighting_service import weighted_evidence_summary
from services.video_understanding_service import understand_video
from services.verdict_service import assess_verdict

logger = get_logger("truthmates.media")

_SUPPORTED_VERDICT = "SUPPORTED"
_REFUTED_VERDICT = "REFUTED"
_MISLEADING_VERDICT = "MISLEADING"
_UNVERIFIED_VERDICT = "UNVERIFIED"
_SATIRE_VERDICT = "SATIRE"
_OUT_OF_SCOPE_VERDICT = "OUT_OF_SCOPE"
_INSUFFICIENT_EVIDENCE_VERDICT = "INSUFFICIENT_EVIDENCE"


def _default_translate(text: str) -> str:
    return text


def _default_verdict_assessment(verdict: str) -> str:
    if verdict == _SUPPORTED_VERDICT:
        return "AI Assessment: Retrieved sources support this claim."
    if verdict == _REFUTED_VERDICT:
        return "AI Assessment: Retrieved sources refute this claim."
    if verdict == _MISLEADING_VERDICT:
        return "AI Assessment: Retrieved sources show this claim is misleading."
    if verdict == _INSUFFICIENT_EVIDENCE_VERDICT:
        return "AI Assessment: We could not verify this claim because trusted sources were unavailable."
    if verdict == _SATIRE_VERDICT:
        return "AI Assessment: This content appears to be satire, not a literal factual claim."
    if verdict == _OUT_OF_SCOPE_VERDICT:
        return "AI Assessment: This content is outside the civic verification scope."
    return "AI Assessment: We could not verify this claim from trusted sources."


def _analysis_source_ref(*, claim: str, input_type: str, source_ref: str) -> tuple[str, str]:
    stable_source = (source_ref or "").strip() or claim
    analysis_key = build_analysis_key(claim=claim, input_type=input_type, source_ref=stable_source)
    return analysis_key, stable_source


def _sources_from_matches(matches: list) -> tuple[list[str], float]:
    sources: list[str] = []
    best_similarity = 0.0
    for match in matches:
        source_url = getattr(match, "source_url", "") or ""
        similarity = float(getattr(match, "similarity", 0.0) or 0.0)
        if source_url and source_url not in sources:
            sources.append(source_url)
        best_similarity = max(best_similarity, similarity)
    return sources, best_similarity


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
    parts.append(f'Claim Analyzed: "{claim[:200]}"')
    parts.append("")
    if verdict_reason:
        parts.append(f"Finding: {verdict_reason}")
    elif counter_english:
        explanation = counter_english
        if explanation.startswith("AI Assessment:"):
            explanation = explanation[len("AI Assessment:"):].strip()
        parts.append(f"Finding: {explanation}")
    parts.append("")
    if misleading_reason:
        parts.append(f"Why it may be misleading: {misleading_reason}")
        parts.append("")
    evidence_found = []
    for match in (matches or []):
        fact = getattr(match, "fact_text", "") or ""
        sim = float(getattr(match, "similarity", 0.0) or 0.0)
        src_url = getattr(match, "source_url", "") or ""
        src_type = getattr(match, "source_type", "") or ""
        if fact:
            type_label = "Government DB" if src_type == "pinecone" else "Fact Check" if src_type == "google_fact_check" else "Web"
            evidence_found.append(f"\u2022 [{type_label}] {fact[:150]} (similarity: {sim:.0%}, source: {src_url})")
    if evidence_found:
        parts.append("Evidence Found:")
        parts.extend(evidence_found)
        parts.append("")
    else:
        parts.append("Evidence: No matching verified facts were found in official databases or trusted fact-check sources.")
        parts.append("")
    if source_weight_summary:
        parts.append(f"Source Analysis: {source_weight_summary}")
        parts.append("")
    verdict_labels = {
        "SUPPORTED": "This claim is SUPPORTED by official sources and verified evidence.",
        "REFUTED": "This claim is REFUTED \u2014 trusted sources contradict it.",
        "MISLEADING": "This claim is MISLEADING \u2014 while it may contain partial truths, it distorts the overall picture.",
        "UNVERIFIED": "This claim is UNVERIFIED \u2014 we could not find enough evidence to confirm or deny it.",
        "INSUFFICIENT_EVIDENCE": "INSUFFICIENT EVIDENCE \u2014 trusted sources did not provide enough data to verify this claim.",
        "SATIRE": "This content is identified as SATIRE and is not a literal factual claim.",
        "OUT_OF_SCOPE": "This content is OUT OF SCOPE for civic fact-checking.",
    }
    conclusion = verdict_labels.get(verdict, f"Verdict: {verdict}")
    parts.append(f"Conclusion: {conclusion}")
    return "\n".join(parts)


def _base_flags() -> ValidationFlags:
    return ValidationFlags(
        contradicts_pib_fact=False,
        invalid_source_url=False,
        trust_score_mismatch=False,
        missing_hindi=False,
        hallucinated_stats=False,
        overly_hedged_language=False,
    )


def _exit_post(
    *,
    claim: str,
    verdict: str,
    explanation: str,
    input_type: str,
    source_ref: str,
    summary: str,
    content_category: str,
    analysis_route: str,
    title: str | None = None,
    video_url: str | None = None,
    video_understanding: VideoUnderstanding | None = None,
    translate_text: Callable[[str], str],
) -> ValidatedPost:
    analysis_key, stable_source_ref = _analysis_source_ref(
        claim=claim,
        input_type=input_type,
        source_ref=source_ref,
    )
    return ValidatedPost(
        claim=claim,
        analysis_key=analysis_key,
        source_ref=stable_source_ref,
        verdict=verdict,
        trust_score=55.0 if verdict == _SATIRE_VERDICT else 50.0,
        counter_english=explanation,
        counter_hindi=translate_text(explanation),
        sources=[],
        flags=_base_flags(),
        llm_confidence=0.0,
        source_match=0.0,
        source_found=0.0,
        deepfake_score=0.0,
        crowd_reports=0.0,
        input_type=input_type,
        content_summary=summary,
        video_title=title,
        video_url=video_url,
        content_category=content_category,
        analysis_route=analysis_route,
        pipeline_status="short_circuit",
        video_understanding=video_understanding,
        detailed_explanation=_build_detailed_explanation(
            claim=claim,
            verdict=verdict,
            verdict_reason=explanation,
            counter_english=explanation,
            misleading_reason="",
            matches=[],
            content_summary=summary,
            source_weight_summary="",
        ),
        source_references=_build_source_references([]),
    )


def _partial_failure_post(
    *,
    claim: str,
    input_type: str,
    source_ref: str,
    summary: str,
    error_message: str,
    content_category: str,
    analysis_route: str,
    title: str | None = None,
    video_url: str | None = None,
    video_understanding: VideoUnderstanding | None = None,
    translate_text: Callable[[str], str],
) -> ValidatedPost:
    # Build a meaningful English-only explanation
    claim_short = (claim or "this content")[:120]
    explanation = (
        f"No matching verified facts were found for this claim in official databases (PIB, MyGov) "
        f"or trusted fact-check sources. This claim could not be independently confirmed or denied."
    )
    analysis_key, stable_source_ref = _analysis_source_ref(
        claim=claim,
        input_type=input_type,
        source_ref=source_ref,
    )
    return ValidatedPost(
        claim=claim,
        analysis_key=analysis_key,
        source_ref=stable_source_ref,
        verdict=_INSUFFICIENT_EVIDENCE_VERDICT,
        trust_score=45.0,
        counter_english=explanation,
        counter_hindi=translate_text(explanation),
        sources=["https://pib.gov.in/FactCheck.aspx"],
        flags=_base_flags(),
        llm_confidence=65.0,
        source_match=0.0,
        source_found=0.0,
        deepfake_score=0.0,
        crowd_reports=0.0,
        input_type=input_type,
        content_summary=summary,
        video_title=title,
        video_url=video_url,
        content_category=content_category,
        analysis_route=analysis_route,
        pipeline_status="partial_failure",
        pipeline_error=error_message,
        video_understanding=video_understanding,
        detailed_explanation=_build_detailed_explanation(
            claim=claim,
            verdict=_INSUFFICIENT_EVIDENCE_VERDICT,
            verdict_reason=explanation,
            counter_english=explanation,
            misleading_reason="",
            matches=[],
            content_summary=summary,
            source_weight_summary="",
        ),
        source_references=_build_source_references([]),
    )


def _video_claims_to_validated_posts(
    analysis_output,
    verified_claims: list,
    *,
    classification: ContentClassification,
    input_type: str = "video",
    video_title: str | None = None,
    video_url: str | None = None,
    video_understanding: VideoUnderstanding | None = None,
    translate_text: Callable[[str], str] | None = None,
    verdict_assessment: Callable[[str], str] | None = None,
) -> list[ValidatedPost]:
    translate_text = translate_text or _default_translate
    verdict_assessment = verdict_assessment or _default_verdict_assessment

    posts: list[ValidatedPost] = []
    for claim in verified_claims:
        sources, best_similarity = _sources_from_matches(claim.matches)
        has_source = 100.0 if sources else 0.0
        similarity_pct = round(best_similarity * 100, 1)
        misleading = assess_misleading(
            claim=claim.claim_text,
            matches=claim.matches,
            content_summary=getattr(analysis_output, "summary", classification.summary),
            correction_text=claim.correction,
            input_type=input_type,
        )
        verdict_details = assess_verdict(
            claim=claim.claim_text,
            verification_label=claim.verification_label,
            matches=claim.matches,
            misleading=misleading,
            input_type=input_type,
        )
        verdict = verdict_details.verdict
        if verdict == _SUPPORTED_VERDICT:
            trust_score = round(max(60, similarity_pct), 1)
        elif verdict == _INSUFFICIENT_EVIDENCE_VERDICT:
            trust_score = 45.0
        elif verdict == _MISLEADING_VERDICT:
            trust_score = 55.0
        elif verdict == _REFUTED_VERDICT:
            trust_score = 55.0
        else:
            trust_score = 50.0

        source_text = sources[0] if sources else "no official source found"
        correction_body = (claim.correction or "").strip()
        if correction_body:
            correction_en = f"{verdict_assessment(verdict)} {correction_body} Source: {source_text}"
        else:
            correction_en = f"{verdict_assessment(verdict)} Source: {source_text}"

        translated_body = translate_text(correction_body) if correction_body else ""
        correction_hi = f"{translated_body} Source: {source_text}".strip()
        analysis_key, source_ref = _analysis_source_ref(
            claim=claim.claim_text,
            input_type=input_type,
            source_ref=video_url or video_title or claim.claim_text,
        )

        sw_summary = weighted_evidence_summary(claim.matches)
        posts.append(
            ValidatedPost(
                claim=claim.claim_text,
                analysis_key=analysis_key,
                source_ref=source_ref,
                verdict=verdict,
                trust_score=trust_score,
                counter_english=correction_en,
                counter_hindi=correction_hi,
                sources=sources,
                flags=ValidationFlags(
                    contradicts_pib_fact=claim.verification_label == "verified",
                    invalid_source_url=False,
                    trust_score_mismatch=False,
                    missing_hindi=False,
                    hallucinated_stats=False,
                ),
                llm_confidence=round(similarity_pct * 0.8, 1),
                source_match=similarity_pct,
                source_found=has_source,
                deepfake_score=0.0,
                crowd_reports=0.0,
                input_type=input_type,
                content_summary=getattr(analysis_output, "summary", classification.summary),
                video_title=video_title,
                video_url=video_url,
                content_category=classification.content_category,
                analysis_route=classification.analysis_route,
                pipeline_status="complete",
                misleading_reason=misleading.misleading_reason,
                verdict_reason=verdict_details.explanation,
                detailed_explanation=_build_detailed_explanation(
                    claim=claim.claim_text,
                    verdict=verdict,
                    verdict_reason=verdict_details.explanation,
                    counter_english=correction_en,
                    misleading_reason=misleading.misleading_reason or "",
                    matches=claim.matches,
                    content_summary=getattr(analysis_output, "summary", classification.summary),
                    source_weight_summary=sw_summary,
                ),
                source_references=_build_source_references(claim.matches),
                source_weight_score=verdict_details.source_weight_score,
                source_weight_summary=sw_summary,
                countercheck_note=verdict_details.countercheck_note,
                video_understanding=video_understanding,
            )
        )
    return posts


def _log_understanding_complete(
    *,
    request_id: str | None,
    pipeline_status: str,
    video_understanding: VideoUnderstanding | None,
) -> None:
    if video_understanding is None:
        return
    log_event(
        logger,
        "stage_complete",
        request_id=request_id,
        stage="video_understanding_complete",
        understanding_source=video_understanding.understanding_source,
        confidence=video_understanding.confidence,
        pipeline_status=pipeline_status,
    )


def _video_pipeline_failure(
    *,
    claim: str,
    source_ref: str,
    summary: str,
    error_message: str,
    content_category: str,
    analysis_route: str,
    title: str | None,
    video_url: str | None,
    video_understanding: VideoUnderstanding | None,
    translate_text: Callable[[str], str],
    request_id: str | None,
) -> ValidateResponse:
    post = _partial_failure_post(
        claim=claim,
        input_type="video",
        source_ref=source_ref,
        summary=summary,
        error_message=error_message,
        content_category=content_category,
        analysis_route=analysis_route,
        title=title,
        video_url=video_url,
        video_understanding=video_understanding,
        translate_text=translate_text,
    )
    _log_understanding_complete(
        request_id=request_id,
        pipeline_status=post.pipeline_status or "partial_failure",
        video_understanding=video_understanding,
    )
    return ValidateResponse(status="partial_failure", count=1, posts=[post])


async def analyze_video_url(
    url: str,
    *,
    request_id: str | None = None,
    translate_text: Callable[[str], str] | None = None,
    verdict_assessment: Callable[[str], str] | None = None,
) -> ValidateResponse:
    translate_text = translate_text or _default_translate
    verdict_assessment = verdict_assessment or _default_verdict_assessment

    video_url = (url or "").strip()
    if not video_url:
        raise HTTPException(status_code=422, detail="Video URL is required.")

    from video.extractor import cleanup_artifacts, extract_video_artifacts, validate_url

    try:
        validated_url = validate_url(video_url)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    extraction = None
    try:
        started = stage_start()
        extraction = await asyncio.to_thread(
            extract_video_artifacts,
            validated_url,
            validate=False,
        )
        log_event(
            logger,
            "stage_complete",
            request_id=request_id,
            stage="media_extract_transcript",
            duration_ms=stage_duration_ms(started),
            provider="groq_whisper",
        )

        title = extraction["title"]
        transcript = extraction["transcript"]
        duration_seconds = float(extraction.get("duration_seconds") or 0.0)
        claim_label = title or "Video content"

        video_understanding = await understand_video(
            video_path=extraction["video_path"],
            partial_transcript=transcript,
            duration_seconds=duration_seconds,
            filename=title or "video",
            request_id=request_id or "",
        )

        if extraction.get("transcript_error"):
            error_message = "Could not extract visual or speech content from this video."
            if video_understanding.understanding_source not in {"vision_only", "metadata_only"}:
                error_message = "Could not extract speech content from this video."
            response = _video_pipeline_failure(
                claim=claim_label,
                source_ref=video_url,
                summary=video_understanding.description,
                error_message=error_message,
                content_category=MEDIA_CONTENT_CATEGORY_OUT_OF_SCOPE,
                analysis_route=MEDIA_ANALYSIS_ROUTE_OUT_OF_SCOPE_EXIT,
                title=title,
                video_url=video_url,
                video_understanding=video_understanding,
                translate_text=translate_text,
                request_id=request_id,
            )
            await save_validated_posts([post.model_dump() for post in response.posts])
            return response

        if not extraction.get("transcript_valid"):
            response = _video_pipeline_failure(
                claim=claim_label,
                source_ref=video_url,
                summary=video_understanding.description,
                error_message="Not enough speech to verify claims. Minimum 30 words required.",
                content_category=MEDIA_CONTENT_CATEGORY_OUT_OF_SCOPE,
                analysis_route=MEDIA_ANALYSIS_ROUTE_OUT_OF_SCOPE_EXIT,
                title=title,
                video_url=video_url,
                video_understanding=video_understanding,
                translate_text=translate_text,
                request_id=request_id,
            )
            await save_validated_posts([post.model_dump() for post in response.posts])
            return response

        started = stage_start()
        classification, provider = await asyncio.to_thread(
            classify_media_content,
            transcript,
            title=title,
            input_type="video",
        )
        log_event(
            logger,
            "stage_complete",
            request_id=request_id,
            stage="media_content_classification",
            duration_ms=stage_duration_ms(started),
            provider=provider,
            content_category=classification.content_category,
            analysis_route=classification.analysis_route,
        )

        if classification.analysis_route == MEDIA_ANALYSIS_ROUTE_SATIRE_EXIT:
            post = _exit_post(
                claim=claim_label,
                verdict=_SATIRE_VERDICT,
                explanation="This content appears to be satire or parody, so TruthMates is not treating it as a literal civic misinformation claim.",
                input_type="video",
                source_ref=video_url,
                summary=classification.summary,
                content_category=classification.content_category,
                analysis_route=classification.analysis_route,
                title=title,
                video_url=video_url,
                video_understanding=video_understanding,
                translate_text=translate_text,
            )
            _log_understanding_complete(
                request_id=request_id,
                pipeline_status=post.pipeline_status or "short_circuit",
                video_understanding=video_understanding,
            )
            await save_validated_posts([post.model_dump()])
            return ValidateResponse(status="success", count=1, posts=[post])

        if classification.analysis_route == MEDIA_ANALYSIS_ROUTE_OUT_OF_SCOPE_EXIT:
            post = _exit_post(
                claim=claim_label,
                verdict=_OUT_OF_SCOPE_VERDICT,
                explanation="This content is outside the civic and government fact-checking scope, so the verification pipeline stopped before evidence retrieval.",
                input_type="video",
                source_ref=video_url,
                summary=classification.summary,
                content_category=classification.content_category,
                analysis_route=classification.analysis_route,
                title=title,
                video_url=video_url,
                video_understanding=video_understanding,
                translate_text=translate_text,
            )
            _log_understanding_complete(
                request_id=request_id,
                pipeline_status=post.pipeline_status or "short_circuit",
                video_understanding=video_understanding,
            )
            await save_validated_posts([post.model_dump()])
            return ValidateResponse(status="success", count=1, posts=[post])

        try:
            from video.analyzer import run_video_analysis_crew

            started = stage_start()
            analysis_output, verified_claims, provider = await asyncio.to_thread(
                run_video_analysis_crew,
                transcript,
            )
            log_event(
                logger,
                "stage_complete",
                request_id=request_id,
                stage="media_claim_analysis",
                duration_ms=stage_duration_ms(started),
                provider=provider,
            )
        except Exception as exc:
            log_event(
                logger,
                "stage_failed",
                level="warning",
                request_id=request_id,
                stage="media_claim_analysis",
                error=str(exc),
            )
            response = _video_pipeline_failure(
                claim=claim_label,
                source_ref=video_url,
                summary=classification.summary,
                error_message=str(exc),
                content_category=classification.content_category,
                analysis_route=classification.analysis_route,
                title=title,
                video_url=video_url,
                video_understanding=video_understanding,
                translate_text=translate_text,
                request_id=request_id,
            )
            await save_validated_posts([post.model_dump() for post in response.posts])
            return response

        validated_posts = _video_claims_to_validated_posts(
            analysis_output,
            verified_claims,
            classification=classification,
            input_type="video",
            video_title=title,
            video_url=video_url,
            video_understanding=video_understanding,
            translate_text=translate_text,
            verdict_assessment=verdict_assessment,
        )
        _log_understanding_complete(
            request_id=request_id,
            pipeline_status="complete",
            video_understanding=video_understanding,
        )
        await save_validated_posts([post.model_dump() for post in validated_posts])
        return ValidateResponse(status="success", count=len(validated_posts), posts=validated_posts)
    except (RuntimeError, ValueError) as exc:
        log_event(
            logger,
            "stage_failed",
            level="warning",
            request_id=request_id,
            stage="media_extract_transcript",
            error=str(exc),
        )
        fallback_understanding = VideoUnderstanding(
            description="Video metadata was available, but visual frames and speech could not be extracted.",
            detected_language="unknown",
            estimated_content_type="UNKNOWN",
            confidence=0.0,
            understanding_source="metadata_only",
        )
        response = _video_pipeline_failure(
            claim="Video content",
            source_ref=video_url,
            summary=fallback_understanding.description,
            error_message="Could not extract visual or speech content from this video.",
            content_category=MEDIA_CONTENT_CATEGORY_OUT_OF_SCOPE,
            analysis_route=MEDIA_ANALYSIS_ROUTE_OUT_OF_SCOPE_EXIT,
            title=None,
            video_url=video_url,
            video_understanding=fallback_understanding,
            translate_text=translate_text,
            request_id=request_id,
        )
        await save_validated_posts([post.model_dump() for post in response.posts])
        return response
    finally:
        if extraction:
            await asyncio.to_thread(cleanup_artifacts, extraction.get("temp_dir"))


async def analyze_audio_upload(
    file: UploadFile,
    *,
    request_id: str | None = None,
    translate_text: Callable[[str], str] | None = None,
    verdict_assessment: Callable[[str], str] | None = None,
) -> ValidateResponse:
    translate_text = translate_text or _default_translate
    verdict_assessment = verdict_assessment or _default_verdict_assessment

    filename = file.filename or "upload.wav"
    ext = os.path.splitext(filename)[1].lower()
    if ext not in MEDIA_ALLOWED_AUDIO_EXTENSIONS:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported audio format '{ext}'. Allowed: {', '.join(sorted(MEDIA_ALLOWED_AUDIO_EXTENSIONS))}",
        )

    from video.analyzer import run_video_analysis_crew
    from video.extractor import transcribe_audio_file

    tmp_dir = None
    try:
        tmp_dir = tempfile.mkdtemp(prefix="truthmates_audio_")
        tmp_path = os.path.join(tmp_dir, filename)
        with open(tmp_path, "wb") as handle:
            content = await file.read()
            handle.write(content)

        try:
            started = stage_start()
            extraction = await asyncio.to_thread(transcribe_audio_file, tmp_path)
            log_event(
                logger,
                "stage_complete",
                request_id=request_id,
                stage="audio_transcribe",
                duration_ms=stage_duration_ms(started),
                provider="groq_whisper",
            )
        except ValueError as exc:
            log_event(
                logger,
                "stage_failed",
                level="warning",
                request_id=request_id,
                stage="audio_transcribe",
                error=str(exc),
            )
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except RuntimeError as exc:
            log_event(
                logger,
                "stage_failed",
                level="warning",
                request_id=request_id,
                stage="audio_transcribe",
                error=str(exc),
            )
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        transcript = extraction["transcript"]

        started = stage_start()
        classification, provider = await asyncio.to_thread(
            classify_media_content,
            transcript,
            title=filename,
            input_type="audio",
        )
        log_event(
            logger,
            "stage_complete",
            request_id=request_id,
            stage="audio_content_classification",
            duration_ms=stage_duration_ms(started),
            provider=provider,
            content_category=classification.content_category,
            analysis_route=classification.analysis_route,
        )

        if classification.analysis_route == MEDIA_ANALYSIS_ROUTE_SATIRE_EXIT:
            post = _exit_post(
                claim=filename,
                verdict=_SATIRE_VERDICT,
                explanation="This audio appears to be satire or parody, so TruthMates is not treating it as a literal civic misinformation claim.",
                input_type="audio",
                source_ref=filename,
                summary=classification.summary,
                content_category=classification.content_category,
                analysis_route=classification.analysis_route,
                title=filename,
                translate_text=translate_text,
            )
            await save_validated_posts([post.model_dump()])
            return ValidateResponse(status="success", count=1, posts=[post])

        if classification.analysis_route == MEDIA_ANALYSIS_ROUTE_OUT_OF_SCOPE_EXIT:
            post = _exit_post(
                claim=filename,
                verdict=_OUT_OF_SCOPE_VERDICT,
                explanation="This audio is outside the civic and government fact-checking scope, so the verification pipeline stopped before evidence retrieval.",
                input_type="audio",
                source_ref=filename,
                summary=classification.summary,
                content_category=classification.content_category,
                analysis_route=classification.analysis_route,
                title=filename,
                translate_text=translate_text,
            )
            await save_validated_posts([post.model_dump()])
            return ValidateResponse(status="success", count=1, posts=[post])

        try:
            started = stage_start()
            analysis_output, verified_claims, provider = await asyncio.to_thread(
                run_video_analysis_crew,
                transcript,
            )
            log_event(
                logger,
                "stage_complete",
                request_id=request_id,
                stage="audio_claim_analysis",
                duration_ms=stage_duration_ms(started),
                provider=provider,
            )
        except Exception as exc:
            log_event(
                logger,
                "stage_failed",
                level="warning",
                request_id=request_id,
                stage="audio_claim_analysis",
                error=str(exc),
            )
            post = _partial_failure_post(
                claim=filename,
                input_type="audio",
                source_ref=filename,
                summary=classification.summary,
                error_message=str(exc),
                content_category=classification.content_category,
                analysis_route=classification.analysis_route,
                title=filename,
                translate_text=translate_text,
            )
            await save_validated_posts([post.model_dump()])
            return ValidateResponse(status="partial_failure", count=1, posts=[post])

        validated_posts = _video_claims_to_validated_posts(
            analysis_output,
            verified_claims,
            classification=classification,
            input_type="audio",
            video_title=filename,
            translate_text=translate_text,
            verdict_assessment=verdict_assessment,
        )
        await save_validated_posts([post.model_dump() for post in validated_posts])
        return ValidateResponse(status="success", count=len(validated_posts), posts=validated_posts)
    finally:
        if tmp_dir and os.path.isdir(tmp_dir):
            shutil.rmtree(tmp_dir, ignore_errors=True)
