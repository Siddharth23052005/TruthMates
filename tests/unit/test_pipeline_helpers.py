from models.schemas import EvidenceMatch, VerifiedPost
from services.analysis_helpers import compute_trust_score, normalize_analysis_verdict


def test_compute_trust_score_uses_similarity_confidence_and_source():
    post = VerifiedPost(
        title="Claim",
        description="Description",
        link="manual://1",
        pub_date=None,
        source="Manual",
        label="civic",
        confidence=0.9,
        language="en",
        needs_review=False,
        verification_label="verified",
        matches=[
            EvidenceMatch(
                fact_text="Fact",
                similarity=0.8,
                source_url="https://example.gov.in/fact",
                source_type="pinecone",
            )
        ],
        crowdsource_reports=0.1,
        deepfake_score=0.0,
    )
    score, label = compute_trust_score(post)
    assert score > 60
    assert label == "Green"


def test_normalize_analysis_verdict_maps_legacy_labels():
    assert normalize_analysis_verdict("TRUE") == "SUPPORTED"
    assert normalize_analysis_verdict("FALSE") == "REFUTED"
    assert normalize_analysis_verdict("SOURCES UNAVAILABLE") == "INSUFFICIENT_EVIDENCE"
    assert normalize_analysis_verdict("MISLEADING") == "MISLEADING"
