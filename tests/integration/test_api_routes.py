import pytest


@pytest.mark.asyncio
async def test_analyze_endpoint_returns_mocked_contract(app_client, public_headers, monkeypatch):
    from api.routes import pipeline as pipeline_routes
    from models.schemas import ValidateResponse, ValidationFlags, ValidatedPost

    async def fake_analyze_claim(claim: str, *, request_id: str | None = None):
        return ValidateResponse(
            status="success",
            count=1,
            posts=[
                ValidatedPost(
                    claim=claim,
                    analysis_key="key-1",
                    source_ref="manual://1",
                    verdict="SUPPORTED",
                    trust_score=88.0,
                    counter_english="Trusted sources support this claim.",
                    counter_hindi="Trusted sources support this claim.",
                    sources=["https://example.gov.in/fact"],
                    flags=ValidationFlags(
                        contradicts_pib_fact=False,
                        invalid_source_url=False,
                        trust_score_mismatch=False,
                        missing_hindi=False,
                        hallucinated_stats=False,
                        overly_hedged_language=False,
                    ),
                    content_category="government_claim",
                    analysis_route="VERIFY",
                    verdict_reason="Official evidence supports the claim.",
                    source_weight_score=82.5,
                    source_weight_summary="tier=1; host=example.gov.in",
                )
            ],
        )

    monkeypatch.setattr(pipeline_routes, "analyze_claim", fake_analyze_claim)
    response = await app_client.post("/analyze", headers=public_headers, json={"claim": "Claim X"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["posts"][0]["analysis_route"] == "VERIFY"
    assert payload["posts"][0]["verdict_reason"] == "Official evidence supports the claim."


@pytest.mark.asyncio
async def test_analyze_video_endpoint_returns_mocked_contract(app_client, public_headers, monkeypatch):
    from api.routes import media as media_routes
    from models.schemas import ValidateResponse, ValidationFlags, ValidatedPost

    async def fake_analyze_video(url: str, *, request_id: str | None = None):
        return ValidateResponse(
            status="partial_failure",
            count=1,
            posts=[
                ValidatedPost(
                    claim="Video claim",
                    analysis_key="video-key",
                    source_ref=url,
                    verdict="INSUFFICIENT_EVIDENCE",
                    trust_score=45.0,
                    counter_english="Evidence retrieval failed before verification finished.",
                    counter_hindi="Evidence retrieval failed before verification finished.",
                    sources=[],
                    flags=ValidationFlags(
                        contradicts_pib_fact=False,
                        invalid_source_url=False,
                        trust_score_mismatch=False,
                        missing_hindi=False,
                        hallucinated_stats=False,
                        overly_hedged_language=False,
                    ),
                    content_category="government_claim",
                    analysis_route="VERIFY",
                    pipeline_status="partial_failure",
                    pipeline_error="retrieval timeout",
                )
            ],
        )

    monkeypatch.setattr(media_routes, "analyze_video_url", fake_analyze_video)
    response = await app_client.post("/analyze-video", headers=public_headers, json={"url": "https://youtu.be/demo"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "partial_failure"
    assert payload["posts"][0]["pipeline_error"] == "retrieval timeout"


@pytest.mark.asyncio
async def test_monitor_status_endpoint_returns_mocked_payload(app_client, admin_headers, monkeypatch):
    from api.routes import monitor as monitor_routes

    async def fake_monitor_status(*, request_id: str | None = None):
        return {"status": "healthy", "agents": {"classifier": "PASS"}, "timestamp": "2026-05-08T00:00:00Z"}

    monkeypatch.setattr(monitor_routes, "monitor_status_payload", fake_monitor_status)
    response = await app_client.get("/monitor/status", headers=admin_headers)

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_monitor_summary_endpoint_returns_mocked_payload(app_client, admin_headers, monkeypatch):
    from api.routes import monitor as monitor_routes
    from models.schemas import MonitorSummaryResponse

    async def fake_monitor_summary(*, request_id: str | None = None):
        return MonitorSummaryResponse(
            status="success",
            total_validated=12,
            verdict_counts={"SUPPORTED": 5, "REFUTED": 4, "MISLEADING": 3},
            monitor_status_counts={"PASS": 10, "FAIL": 2},
            average_trust_score=61.5,
            timeline=[{"date": "2026-05-08", "count": 12}],
        )

    monkeypatch.setattr(monitor_routes, "monitor_summary_payload", fake_monitor_summary)
    response = await app_client.get("/monitor/summary", headers=admin_headers)

    assert response.status_code == 200
    assert response.json()["total_validated"] == 12
