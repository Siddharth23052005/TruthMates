from services.misleading_service import assess_misleading
from services.source_weighting_service import aggregate_weight_score, weight_evidence
from services.verdict_service import is_overly_hedged


class Match:
    def __init__(self, fact_text: str, similarity: float, source_url: str, source_type: str) -> None:
        self.fact_text = fact_text
        self.similarity = similarity
        self.source_url = source_url
        self.source_type = source_type


def test_assess_misleading_without_matches_returns_insufficient_evidence():
    result = assess_misleading(claim="Claim", matches=[], input_type="text")
    assert result.insufficient_evidence is True
    assert result.is_misleading is False


def test_source_weighting_prefers_official_sources():
    matches = [
        Match("Official fact", 0.82, "https://uidai.gov.in", "pinecone"),
        Match("News fact", 0.95, "https://reuters.com", "google_fact_check"),
    ]
    weighted = weight_evidence(matches)
    assert weighted[0].source_url == "https://uidai.gov.in"
    assert aggregate_weight_score(matches) > 50


def test_overly_hedged_language_detector_flags_banned_phrases():
    assert is_overly_hedged("It should be noted that this appears to suggest a risk.") is True
    assert is_overly_hedged("Trusted sources contradict this claim.") is False
