from services.verdict_service import VerdictAssessment


def test_verdict_hint_is_intermediate_signal_not_final_response_field(sample_validated_post):
    hint = VerdictAssessment(
        verdict="MISLEADING",
        explanation="The claim leaves out the eligibility limit.",
        countercheck_note="No stronger contrary source outweighed the official guidance.",
        source_weight_score=74.0,
        confidence=0.8,
    )
    assert hint.verdict == "MISLEADING"
    assert "verdict_hint" not in sample_validated_post
