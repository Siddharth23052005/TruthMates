from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True)
class WeightedEvidence:
    fact_text: str
    source_url: str
    source_type: str
    similarity: float
    weight_tier: int
    weight_score: float
    rationale: str


_TIER_1_DOMAINS = {
    "pib.gov.in",
    "eci.gov.in",
    "rbi.org.in",
    "uidai.gov.in",
    "mohfw.gov.in",
    "nha.gov.in",
    "sebi.gov.in",
    "who.int",
    "icmr.gov.in",
    "morth.nic.in",
    "gst.gov.in",
    "dicgc.org.in",
}

_TIER_2_DOMAINS = {
    "prsindia.org",
    "data.gov.in",
    "nhm.gov.in",
    "mygov.in",
    "unicef.org",
    "worldbank.org",
    "imf.org",
}

_TIER_3_DOMAINS = {
    "thehindu.com",
    "indianexpress.com",
    "livemint.com",
    "timesofindia.indiatimes.com",
    "reuters.com",
    "apnews.com",
    "bbc.com",
}


def _hostname(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower()
    except Exception:
        return ""


def _tier_for_source(source_url: str, source_type: str) -> tuple[int, float, str]:
    host = _hostname(source_url)
    if source_type == "pinecone" and (host.endswith(".gov.in") or host in _TIER_1_DOMAINS):
        return 1, 1.0, "Official government or regulator source."
    if host in _TIER_1_DOMAINS or host.endswith(".gov.in"):
        return 1, 1.0, "Official government or regulator source."
    if host in _TIER_2_DOMAINS or host.endswith(".org"):
        return 2, 0.85, "Institutional or policy reference source."
    if host in _TIER_3_DOMAINS:
        return 3, 0.65, "Established news reporting source."
    if source_type == "google_fact_check":
        return 3, 0.60, "Fact-check review source."
    return 4, 0.40, "Open-web or lower-authority source."


def weight_evidence(matches: list) -> list[WeightedEvidence]:
    weighted: list[WeightedEvidence] = []
    for match in matches:
        source_url = getattr(match, "source_url", "") or ""
        source_type = getattr(match, "source_type", "") or ""
        fact_text = getattr(match, "fact_text", "") or ""
        similarity = float(getattr(match, "similarity", 0.0) or 0.0)
        tier, weight_score, rationale = _tier_for_source(source_url, source_type)
        weighted.append(
            WeightedEvidence(
                fact_text=fact_text,
                source_url=source_url,
                source_type=source_type,
                similarity=similarity,
                weight_tier=tier,
                weight_score=weight_score,
                rationale=rationale,
            )
        )
    return sorted(weighted, key=lambda item: (item.weight_score * item.similarity), reverse=True)


def aggregate_weight_score(matches: list) -> float:
    weighted = weight_evidence(matches)
    if not weighted:
        return 0.0
    top_scores = [item.weight_score * item.similarity for item in weighted[:3]]
    return round((sum(top_scores) / len(top_scores)) * 100, 2)


def weighted_evidence_summary(matches: list, limit: int = 3) -> str:
    items = []
    for evidence in weight_evidence(matches)[:limit]:
        host = _hostname(evidence.source_url) or "unknown-source"
        items.append(
            f"tier={evidence.weight_tier}; host={host}; similarity={evidence.similarity:.2f}; fact={evidence.fact_text}"
        )
    return " | ".join(items)
