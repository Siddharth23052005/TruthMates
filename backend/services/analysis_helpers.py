from __future__ import annotations

from typing import Optional


SUPPORTED_VERDICT = "SUPPORTED"
REFUTED_VERDICT = "REFUTED"
MISLEADING_VERDICT = "MISLEADING"
UNVERIFIED_VERDICT = "UNVERIFIED"
INSUFFICIENT_EVIDENCE_VERDICT = "INSUFFICIENT_EVIDENCE"


def clamp_score(value: Optional[float]) -> float:
    try:
        num = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, num))


def trust_label(score: float) -> str:
    if score <= 40:
        return "Red"
    if score <= 70:
        return "Yellow"
    return "Green"


def select_source_url(matches: list) -> str:
    for match in matches:
        url = getattr(match, "source_url", "") or ""
        if url:
            return url
    return ""


def max_pinecone_similarity(matches: list) -> float:
    best = 0.0
    for match in matches:
        if getattr(match, "source_type", "") == "pinecone":
            best = max(best, clamp_score(getattr(match, "similarity", 0.0)))
    return best


def compute_trust_score(post) -> tuple[float, str]:
    llm_confidence = clamp_score(getattr(post, "confidence", 0.0))
    pinecone_similarity = max_pinecone_similarity(post.matches)
    source_found = 1.0 if select_source_url(post.matches) else 0.0
    crowdsource_reports = clamp_score(getattr(post, "crowdsource_reports", 0.0))
    deepfake_score = clamp_score(getattr(post, "deepfake_score", 0.0))
    trust_value = (llm_confidence * 0.30) + (pinecone_similarity * 0.30) + (source_found * 0.20) + (crowdsource_reports * 0.10) + (deepfake_score * 0.10)
    trust_score = round(trust_value * 100, 2)
    return trust_score, trust_label(trust_score)


def verdict_assessment(verdict: str) -> str:
    if verdict == SUPPORTED_VERDICT:
        return "AI Assessment: Retrieved sources support this claim."
    if verdict == REFUTED_VERDICT:
        return "AI Assessment: Retrieved sources refute this claim."
    if verdict == MISLEADING_VERDICT:
        return "AI Assessment: Retrieved sources suggest this claim is misleading."
    if verdict == INSUFFICIENT_EVIDENCE_VERDICT:
        return "AI Assessment: We could not verify this claim because trusted sources were unavailable."
    if verdict == "SATIRE":
        return "AI Assessment: This content appears to be satire, not a literal factual claim."
    if verdict == "OUT_OF_SCOPE":
        return "AI Assessment: This content is outside the civic verification scope."
    return "AI Assessment: We could not verify this claim from trusted sources."


def normalize_analysis_verdict(verdict: str) -> str:
    normalized = (verdict or "").strip().upper()
    if normalized == "TRUE":
        return SUPPORTED_VERDICT
    if normalized == "FALSE":
        return REFUTED_VERDICT
    if normalized == "SOURCES UNAVAILABLE":
        return INSUFFICIENT_EVIDENCE_VERDICT
    if normalized == "MISINFORMATION DETECTED":
        return REFUTED_VERDICT
    if normalized in {SUPPORTED_VERDICT, REFUTED_VERDICT, MISLEADING_VERDICT, UNVERIFIED_VERDICT, "SATIRE", "OUT_OF_SCOPE", INSUFFICIENT_EVIDENCE_VERDICT}:
        return normalized
    return UNVERIFIED_VERDICT
