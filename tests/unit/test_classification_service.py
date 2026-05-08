from services.classification_service import ContentClassification, _normalize_classification


def test_normalize_classification_forces_satire_exit():
    result = _normalize_classification(
        ContentClassification(
            content_category="satire",
            analysis_route="VERIFY",
            rationale="Parody tone",
            summary="Spoof speech",
        )
    )
    assert result.analysis_route == "SATIRE_EXIT"


def test_normalize_classification_defaults_invalid_values():
    result = _normalize_classification(
        ContentClassification(
            content_category="unknown",
            analysis_route="???",
            rationale="x",
            summary="y",
        )
    )
    assert result.content_category == "government_claim"
    assert result.analysis_route == "VERIFY"
