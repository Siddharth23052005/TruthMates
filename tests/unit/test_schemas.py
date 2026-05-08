import pytest
from pydantic import ValidationError

from models.schemas import ValidatedPost, ValidationFlags


def test_validated_post_accepts_new_reasoning_fields():
    post = ValidatedPost(
        claim="Claim",
        analysis_key="key",
        source_ref="manual://1",
        verdict="MISLEADING",
        trust_score=58.0,
        counter_english="This claim is misleading because it omits key context.",
        counter_hindi="This claim is misleading because it omits key context.",
        sources=["https://example.gov.in"],
        flags=ValidationFlags(
            contradicts_pib_fact=False,
            invalid_source_url=False,
            trust_score_mismatch=False,
            missing_hindi=False,
            hallucinated_stats=False,
            overly_hedged_language=False,
        ),
        misleading_reason="It omits the eligibility condition.",
        verdict_reason="The source supports only part of the claim.",
        source_weight_score=77.5,
        source_weight_summary="tier=1; host=example.gov.in",
        countercheck_note="A contrary blog post existed but had weak sourcing.",
    )
    assert post.misleading_reason == "It omits the eligibility condition."
    assert post.verdict_reason == "The source supports only part of the claim."


def test_validated_post_rejects_unknown_verdict():
    with pytest.raises(ValidationError):
        ValidatedPost(
            claim="Claim",
            analysis_key="key",
            source_ref="manual://1",
            verdict="UNKNOWN",
            trust_score=10.0,
            counter_english="x",
            counter_hindi="x",
            sources=[],
            flags=ValidationFlags(
                contradicts_pib_fact=False,
                invalid_source_url=False,
                trust_score_mismatch=False,
                missing_hindi=False,
                hallucinated_stats=False,
                overly_hedged_language=False,
            ),
        )
