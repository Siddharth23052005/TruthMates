from db.identity import build_analysis_key, normalize_claim_text


def test_normalize_claim_text_collapses_case_and_whitespace():
    assert normalize_claim_text("  PM   Kisan  Benefit  ") == "pm kisan benefit"


def test_build_analysis_key_is_stable_for_equivalent_claims():
    key_a = build_analysis_key(claim="  Hello   World ", input_type="TEXT", source_ref="Manual://1")
    key_b = build_analysis_key(claim="hello world", input_type="text", source_ref="manual://1")
    assert key_a == key_b


def test_build_analysis_key_changes_with_source_ref():
    key_a = build_analysis_key(claim="Same claim", input_type="text", source_ref="manual://1")
    key_b = build_analysis_key(claim="Same claim", input_type="text", source_ref="manual://2")
    assert key_a != key_b
