# TruthMates Backend Notes

## Architecture
The backend is now split into:
- `main.py`: FastAPI app wiring, CORS, rate limiting, request IDs, logging
- `api/routes/`: route modules for health, monitor, pipeline, and media
- `services/pipeline_service.py`: text pipeline orchestration and shared text helpers
- `services/media_pipeline_service.py`: video/audio pipeline orchestration
- `services/classification_service.py`: pre-verification routing gate
- `services/misleading_service.py`: misleadingness assessment
- `services/source_weighting_service.py`: source tiering and weighted evidence summaries
- `services/verdict_service.py`: final verdict synthesis and counter-check logic
- `core/config.py`, `core/constants.py`, `core/llm.py`, `core/logging.py`: shared configuration and infrastructure

## Reasoning Flow
### Text
1. `POST /analyze` receives a raw claim.
2. Content routing decides `VERIFY`, `SATIRE_EXIT`, or `OUT_OF_SCOPE_EXIT`.
3. In-scope claims continue through civic classification, evidence retrieval, misleading assessment, verdict hinting, counter generation, and final validation.

### Media
1. Transcript extraction runs first.
2. Content routing decides `VERIFY`, `SATIRE_EXIT`, or `OUT_OF_SCOPE_EXIT`.
3. In-scope media continues through claim extraction, shared evidence retrieval, misleading assessment, verdict synthesis, and final formatting.
4. Partial downstream failures return `pipeline_status="partial_failure"` with `pipeline_error`.

## Verdict Model
Analysis verdicts:
- `SUPPORTED`
- `REFUTED`
- `MISLEADING`
- `UNVERIFIED`
- `INSUFFICIENT_EVIDENCE`
- `SATIRE`
- `OUT_OF_SCOPE`

Monitor/system labels remain separate:
- `PASS`
- `FAIL`
- `healthy`
- `degraded`

`verdict_hint` exists only on `VerifiedPost` as an intermediate signal before final validation. The final API payload uses `ValidatedPost.verdict`.

## Storage Model
- `civic_posts`, `civic_classified`, `civic_verified`, `civic_counter_info`: upsert by `link`
- `civic_validated`: upsert by `analysis_key`
- `agent_monitor_logs`: append-only monitor entries

## Security and Access
- `ALLOWED_ORIGINS` controls CORS origins
- `TRUTHMATES_PUBLIC_API_KEY` protects public analysis routes
- `TRUTHMATES_ADMIN_API_KEY` protects monitor/admin routes
- `slowapi` provides request rate limiting

## Monitoring
- `GET /monitor/logs`: raw monitor decisions
- `GET /monitor/status`: current pipeline health
- `GET /monitor/summary`: aggregate validated-count, verdict-count, trust, and timeline data for the dashboard

## Corpus
`crew/data/verified_facts.json` is a curated seed corpus used to bootstrap Pinecone. It now includes PIB plus multiple official source tags, but it is still a maintained local corpus rather than a live federated evidence index.

## Test Surface
Pytest coverage lives under `../tests/` and currently covers:
- schema validation
- identity generation
- trust score and verdict normalization helpers
- content routing normalization
- misleading/service post-processing
- Mongo validated upserts
- mocked route contracts for analyze/media/monitor endpoints
