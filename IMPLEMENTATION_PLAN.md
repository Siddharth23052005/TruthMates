# TruthMates Implementation Plan

## Purpose

This document is a code-level implementation plan for fixing the confirmed issues in TruthMates and upgrading the reasoning model from a mechanical claim pipeline into a more skeptical, human-style fact-checking system.

It is structured in three phases:

- Phase 1: Critical
- Phase 2: Important
- Phase 3: Polish

For each issue, this plan includes:

- exact files to change
- what to change
- why it matters
- pseudocode or code-shape where useful
- effort estimate
- dependencies

## Target End State

After this plan is implemented, the system should:

- never speculate when evidence is missing
- use one verdict taxonomy everywhere
- separate routes from business logic
- have reproducible backend dependencies
- include baseline automated tests
- stop overstating frontend capabilities
- use stable identifiers for persisted validated outputs
- enforce restricted CORS and baseline API protection
- align text and video pipelines around the same retrieval and verdict logic
- emit structured logs with correlation IDs and stage timings
- classify content type before verification
- detect misleading framing, not just factual mismatch
- reason more like a skeptical journalist than a linear bot chain

## Proposed Standard Verdict Taxonomy

Before the phase breakdown, the codebase needs one canonical verdict vocabulary.

Important scope boundary:

- Standardize analysis verdicts only.
- Do not fold monitor/health/system status labels into the same taxonomy.

System labels currently used for monitoring and health:

- `PASS`
- `FAIL`
- `HEALTHY`
- `DEGRADED`
- `UNKNOWN`

Those should remain separate from analysis verdicts.

### Recommended canonical verdicts

- `SUPPORTED`
- `REFUTED`
- `MISLEADING`
- `UNVERIFIED`
- `OUT_OF_SCOPE`
- `SATIRE`
- `INSUFFICIENT_EVIDENCE`

### Why this taxonomy

It fixes the current split between:

- prompt terms: `TRUE`, `FALSE`, `MISLEADING`, `UNVERIFIED`
- API terms: `MISINFORMATION DETECTED`, `SOURCES UNAVAILABLE`, `UNVERIFIED`

It also supports the intelligence upgrade:

- `SATIRE` for satirical content
- `OUT_OF_SCOPE` for non-civic content
- `INSUFFICIENT_EVIDENCE` when retrieval failed or evidence is too weak

It does not replace monitor or health labels.

### Mapping from current values

- `TRUE` -> `SUPPORTED`
- `FALSE` -> `REFUTED`
- `MISINFORMATION DETECTED` -> usually `REFUTED`
- `SOURCES UNAVAILABLE` -> `INSUFFICIENT_EVIDENCE`
- `UNVERIFIED` -> keep `UNVERIFIED`

## Proposed New Pipeline

This plan assumes the backend moves toward the following pipeline for text, RSS, audio, and video:

1. Ingest content
2. Content type classifier
3. Scope gate
4. Claim extraction
5. Source and origin assessment
6. Evidence retrieval
7. Misleading detection
8. Verdict synthesis with counter-check
9. Counter-statement generation
10. Validation
11. Persistence
12. Monitoring and logging

### New gate behavior

- `OUT_OF_SCOPE`: content is unrelated to civic/government topics
- `SATIRE`: content is satire/parody and should not be handled as misinformation
- `OPINION_OR_COMMENTARY`: may still continue if it contains explicit factual claims
- `CIVIC_FACTUAL_CLAIM`: full verification pipeline
- `OFFICIAL_GOVERNMENT_CONTENT`: full verification pipeline with higher source weighting

## Proposed New Backend Module Structure

`backend/main.py` should become a thin app entrypoint plus router registration. Business logic should move to new modules.

### Proposed directories and files

- `backend/main.py`
- `backend/api/__init__.py`
- `backend/api/deps.py`
- `backend/api/middleware.py`
- `backend/api/routes/health.py`
- `backend/api/routes/monitor.py`
- `backend/api/routes/text.py`
- `backend/api/routes/rss.py`
- `backend/api/routes/media.py`
- `backend/services/pipeline_service.py`
- `backend/services/media_pipeline_service.py`
- `backend/services/classification_service.py`
- `backend/services/evidence_service.py`
- `backend/services/misleading_service.py`
- `backend/services/verdict_service.py`
- `backend/services/counter_statement_service.py`
- `backend/services/validation_service.py`
- `backend/services/monitoring_service.py`
- `backend/services/trust_score_service.py`
- `backend/services/translation_service.py`
- `backend/services/logging_service.py`
- `backend/services/security_service.py`
- `backend/core/config.py`
- `backend/core/constants.py`
- `backend/core/verdicts.py`
- `backend/core/context.py`
- `backend/core/llm.py`
- `backend/core/timing.py`

This structure is referenced throughout the plan below.

## Phase 1: Critical

These fixes are required because the system is currently capable of producing misleading behavior, inconsistent output, or unsafe public exposure.

### Sprint 1 pre-checklist

Before deeper Sprint 1 implementation starts, perform these items first:

1. Delete duplicate `_select_source_url` and `_max_pinecone_similarity` definitions from `backend/main.py` in a standalone commit.
2. Standardize analysis verdicts only.
3. Fix the two speculative YAML prompt locations:
   - `backend/crew/config/counter_tasks.yaml`
   - `backend/video/config/tasks.yaml`
4. Update `backend/requirements.txt` with the missing runtime/test/security dependencies already identified.
5. Replace `claim`-based upsert identity in `civic_validated`.
6. Record verified-facts corpus expansion as a hard dependency before misleading-detection work begins.

---

## Issue 1. Speculative reasoning in prompts

### Problem

The current prompts instruct the system to reason from general knowledge when evidence is missing. That is unsafe for a fact-checking product.

### Files to change

- `backend/crew/config/counter_tasks.yaml`
- `backend/video/config/tasks.yaml`
- `backend/crew/config/validator_tasks.yaml`
- `backend/crew/config/evidence_tasks.yaml`
- `backend/crew/config/evidence_agents.yaml`
- `backend/video/analyzer.py`

### What to change

Replace all prompt instructions that say:

- reason from general knowledge
- provide a smart tackle answer
- explain why the claim might be true or logically flawed without evidence

with strict uncertainty rules:

- if evidence is missing, say that clearly
- do not infer factual truth from plausibility
- do not invent context, statistics, or official positions
- if content is out of scope or satire, classify it as such rather than fact-checking it as a normal misinformation claim

### Why

This is the single highest-risk behavior in the current system. A misinformation product that fills evidence gaps with plausible-sounding reasoning will create confident falsehoods.

### Prompt shape to implement

```yaml
If evidence is weak, missing, or unavailable:
  - state that the claim could not be verified from trusted sources
  - do not guess whether it is true or false
  - do not use general knowledge to fill gaps
  - describe what evidence would be needed to verify it
```

### Video fact-check prompt replacement

Replace the current fallback with:

```yaml
- If no evidence is found, set verdict_candidate to INSUFFICIENT_EVIDENCE or UNVERIFIED.
- correction must explain the uncertainty in plain language.
- Do NOT provide a factual conclusion that is unsupported by retrieved evidence.
```

### Effort

Small

### Dependencies

- Depends on Issue 2 because the prompts should emit the canonical verdict labels.

---

## Issue 2. Inconsistent verdict labels

### Problem

The codebase uses different verdict terms in prompts, backend output, persistence, and frontend display.

### Files to change

- `backend/models/schemas.py`
- `backend/video/schemas.py`
- `backend/main.py`
- `backend/crew/config/validator_tasks.yaml`
- `backend/video/config/tasks.yaml`
- `backend/backend.md`
- `frontend/src/components/TrustScoreBadge.jsx`
- `frontend/src/pages/Analyze.jsx`
- `frontend/src/pages/Home.jsx`
- `frontend/src/pages/Dashboard.jsx`
- `frontend/src/pages/RumorHeatmap.jsx`
- `frontend/src/pages/WhatsAppBot.jsx`
- `frontend/src/pages/PropagationGraph.jsx` if verdict labels are displayed there
- `frontend/src/lib/api.js` if client-side normalization is added
- new file: `backend/core/verdicts.py`
- new file: `frontend/src/lib/verdicts.js`

### What to change

Introduce one backend enum-like source of truth.

### Backend pseudocode

```python
# backend/core/verdicts.py
from typing import Literal

Verdict = Literal[
    "SUPPORTED",
    "REFUTED",
    "MISLEADING",
    "UNVERIFIED",
    "OUT_OF_SCOPE",
    "SATIRE",
    "INSUFFICIENT_EVIDENCE",
]

TRUST_LABEL_BY_VERDICT = {
    "SUPPORTED": "GREEN",
    "REFUTED": "RED",
    "MISLEADING": "YELLOW",
    "UNVERIFIED": "YELLOW",
    "INSUFFICIENT_EVIDENCE": "YELLOW",
    "OUT_OF_SCOPE": "GREEN",
    "SATIRE": "GREEN",
}
```

### Schema changes

Update `ValidatedPost.verdict` and `VerifiedClaim.verification_label` to use strict allowed values.

Add fields:

- `verdict_reason`
- `misleading_reason`
- `content_category`
- `analysis_route`

### Frontend changes

Update badge colors and labels to support the new taxonomy.

Example mapping:

```js
export const verdictStyles = {
  SUPPORTED: "...green...",
  REFUTED: "...red...",
  MISLEADING: "...yellow...",
  UNVERIFIED: "...yellow...",
  INSUFFICIENT_EVIDENCE: "...yellow...",
  SATIRE: "...blue or neutral...",
  OUT_OF_SCOPE: "...neutral..."
}
```

### Why

Without this, every other plan item stays brittle. Prompts, validators, UI, and persistence all need one vocabulary.

### Effort

Medium

### Dependencies

- Blocks Issues 1, 6, 9, 12, and 13.

### Audit adjustment

Do not apply this standardization to monitor/health labels such as:

- `PASS`
- `FAIL`
- `HEALTHY`
- `DEGRADED`
- `UNKNOWN`

Only analysis verdicts should be migrated under this issue.

---

## Issue 3. Overloaded `backend/main.py`

### Problem

`backend/main.py` currently mixes routing, orchestration, scoring, monitoring, translation, media adaptation, and persistence glue.

### Files to change

- `backend/main.py`
- create `backend/api/routes/*.py`
- create `backend/services/*.py`
- create `backend/core/*.py`

### What to change

Break `main.py` into:

- app factory and middleware only
- route handlers only
- services for business logic
- core utilities for shared constants and helpers

### Proposed extraction plan

#### Move to `backend/api/routes/text.py`

- `/analyze`

#### Move to `backend/api/routes/rss.py`

- `/scrape`
- `/classify`
- `/verify`
- `/generate`
- `/validate`

#### Move to `backend/api/routes/media.py`

- `/analyze-video`
- `/analyze-audio`

#### Move to `backend/api/routes/monitor.py`

- `/monitor/logs`
- `/monitor/status`

#### Move to service modules

- `_kickoff_with_retry` -> `backend/core/llm.py`
- `_compute_trust_score` -> `backend/services/trust_score_service.py`
- `_run_with_monitor` -> `backend/services/monitoring_service.py`
- `_run_generate` -> `backend/services/counter_statement_service.py`
- `_run_validate` -> `backend/services/validation_service.py`
- `_video_claims_to_validated_posts` -> `backend/services/media_pipeline_service.py`
- translation helpers -> `backend/services/translation_service.py`

### Why

This refactor is necessary before the intelligence upgrade. The new content classification and misleading analysis layers will add more branching and metadata. Keeping that in `main.py` will make the codebase much harder to evolve.

### Audit adjustment

Before the refactor begins, remove the duplicated helper definitions in `backend/main.py` as a separate commit. Do not carry those duplicates into the new module structure.

### Pseudocode shape

```python
# backend/main.py
app = create_app()

# backend/api/routes/text.py
@router.post("/analyze")
async def analyze(payload: AnalyzeRequest, svc: PipelineService = Depends(...)):
    return await svc.analyze_text_claim(payload)
```

### Effort

Large

### Dependencies

- Should begin after Issue 2 taxonomy is settled.
- Blocks Issues 8, 10, 11, 12, and 13 from becoming clean implementations.

---

## Issue 7. Risky upsert key in MongoDB

### Problem

Validated outputs are upserted by raw `claim`, which can collide across different input types, sources, or reruns.

### Files to change

- `backend/db/mongo.py`
- `backend/models/schemas.py`
- `backend/video/schemas.py`
- `backend/main.py` or new persistence service after refactor
- new file: `backend/core/identity.py`

### What to change

Introduce a stable composite key for validated outputs.

### Recommended fields

- `analysis_id`
- `content_fingerprint`
- `input_type`
- `source_link` or `video_url`
- `claim_hash`

### Recommended persistence key

Use `analysis_key`, where:

```python
analysis_key = sha256(
    f"{input_type}|{source_link_or_video_url}|{claim_text_normalized}"
).hexdigest()
```

If `source_link` is missing, include:

- transcript title for media
- manual claim UUID for user-submitted text

### Schema changes

Add to `ValidatedPost`:

- `analysis_id: str`
- `analysis_key: str`
- `source_ref: Optional[str]`

### Mongo change

Replace:

```python
filter={"claim": claim}
```

with:

```python
filter={"analysis_key": analysis_key}
```

### Migration strategy

This is a breaking persistence change and needs an explicit rollout plan.

#### Recommended rollout

1. Add `analysis_key` and `analysis_id` support first without removing `claim`.
2. Backfill existing `civic_validated` documents with generated `analysis_key` values where possible.
3. Add a one-time migration script:
   - `backend/scripts/backfill_analysis_keys.py`
4. During a transition window, read by:
   - `analysis_key` first
   - fallback to legacy `claim` only for old records
5. After backfill verification, remove legacy upsert-by-claim behavior.

#### Migration edge cases

- old text claims with no stable `source_ref` should receive a deterministic fallback hash
- duplicate legacy records with the same `claim` but different sources should be exported for manual inspection before deduplication
- dashboards and reports should tolerate mixed old/new documents during migration

#### Suggested migration pseudocode

```python
for doc in civic_validated.find({"analysis_key": {"$exists": False}}):
    key = build_analysis_key(
        input_type=doc.get("input_type", "text"),
        source_ref=doc.get("video_url") or doc.get("source_ref") or doc.get("claim"),
        claim=doc.get("claim", ""),
    )
    collection.update_one({"_id": doc["_id"]}, {"$set": {"analysis_key": key}})
```

### Why

This is a real data integrity bug. It can silently overwrite results.

### Effort

Medium

### Dependencies

- Should be implemented alongside Issue 3 refactor and before tests in Issue 5 are finalized.

---

## Issue 8. Open CORS and no auth

### Problem

The API currently allows all origins and has no authentication or rate limiting.

### Files to change

- `backend/main.py`
- new `backend/api/middleware.py`
- new `backend/api/deps.py`
- new `backend/services/security_service.py`
- new `backend/core/config.py`
- `frontend/.env` or deployment config documentation
- `README.md`
- `backend/backend.md`

### What to change

#### CORS

Move to environment-driven allowlist:

```python
ALLOWED_ORIGINS=http://localhost:5173,https://truthmates.example.com
```

#### Authentication

Add API key auth first, with room for JWT later.

Recommended first step:

- admin/staff API key for monitor endpoints and scrape endpoints
- optional public API key for analyze endpoints

#### Rate limiting

Add baseline rate limiting per client IP and endpoint class.

Recommended implementation options:

- `slowapi`
- custom lightweight middleware if external dependency is not desired

### Suggested route protection

- `/monitor/*`: require admin key
- `/scrape`, `/classify`, `/verify`, `/generate`, `/validate`: require admin key
- `/analyze`, `/analyze-video`, `/analyze-audio`: public tier but rate limited

### Why

Open CORS plus media upload plus expensive model calls is an abuse vector.

### Effort

Medium

### Dependencies

- Easier after Issue 3 route split.

---

## Issue 10. No structured logging

### Problem

The codebase uses `print()` for important events and has no request correlation or stage timings.

### Files to change

- `backend/main.py`
- `backend/crew/tools/evidence_tool.py`
- `backend/crew/tools/rss_tool.py`
- `backend/video/analyzer.py`
- `backend/video/extractor.py`
- new `backend/services/logging_service.py`
- new `backend/core/context.py`
- new `backend/core/timing.py`

### What to change

Add structured JSON logging with:

- `request_id`
- `analysis_id`
- `route`
- `stage`
- `duration_ms`
- `status`
- `error_type`
- `provider`
- `model`

### Middleware pseudocode

```python
@app.middleware("http")
async def request_context_middleware(request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    request.state.request_id = request_id
    start = perf_counter()
    response = await call_next(request)
    duration_ms = int((perf_counter() - start) * 1000)
    logger.info("request_complete", extra={
        "request_id": request_id,
        "path": request.url.path,
        "method": request.method,
        "duration_ms": duration_ms,
        "status_code": response.status_code,
    })
    response.headers["X-Request-ID"] = request_id
    return response
```

### Stage timing instrumentation

Wrap pipeline stages:

- classification
- retrieval
- misleading analysis
- generation
- validation
- persistence
- media download
- transcription

### Why

This is required for debugging correctness, latency, and provider failures.

### Effort

Medium

### Dependencies

- Easier after Issue 3 service extraction.

---

## Critical cross-cutting addition. Partial pipeline failure handling

### Problem

The current plan added logging and retries, but not a canonical response strategy when one pipeline stage fails partially. Retrieval failure, Pinecone timeouts, provider fallback exhaustion, and validator parse errors need consistent user-facing behavior.

### Files to change

- `backend/models/schemas.py`
- `backend/video/schemas.py`
- `backend/main.py` or new service modules after refactor
- `backend/services/pipeline_service.py`
- `backend/services/media_pipeline_service.py`
- `backend/services/evidence_service.py`
- `backend/services/validation_service.py`
- `frontend/src/pages/Analyze.jsx`
- `frontend/src/lib/api.js`

### What to change

Add structured failure metadata to responses instead of crashing or returning ambiguous output.

### New response fields

- `pipeline_status: "complete" | "partial" | "failed"`
- `pipeline_errors: list[PipelineError]`
- `stage_results: dict[str, str]`

### New schema

```python
class PipelineError(BaseModel):
    stage: str
    error_code: str
    message: str
    retryable: bool = False
```

### Behavior rules

- If evidence retrieval fails completely:
  - return `INSUFFICIENT_EVIDENCE`
  - set `pipeline_status="partial"`
  - populate `pipeline_errors` with stage=`evidence_retrieval`
- If validation fails but a prior result exists:
  - return provisional result with `pipeline_status="partial"`
  - set a validator error flag
- If input classification yields `SATIRE` or `OUT_OF_SCOPE`:
  - return `pipeline_status="complete"` because this is a valid terminal route
- Only return HTTP 5xx when no meaningful structured result can be produced at all

### Frontend behavior

`Analyze.jsx` should surface:

- a warning ribbon for partial pipeline results
- a plain explanation such as:
  - "We analyzed this, but evidence retrieval was unavailable, so the result is limited."

### Why

This prevents silent garbage responses and gives the frontend a principled fallback path.

### Effort

Medium

### Dependencies

- Depends on Issue 2 verdict taxonomy and Issue 3 refactor.

---

## Issue 11. Content type awareness

### Problem

The system currently focuses on whether a claim is civic, but not what kind of content it is or how it should be analyzed.

### Files to change

- `backend/models/schemas.py`
- `backend/video/schemas.py`
- `backend/crew/config/classifier_tasks.yaml`
- `backend/crew/config/classifier_agents.yaml`
- `backend/crew/tools/classify_tool.py`
- `backend/video/config/tasks.yaml`
- `backend/video/analyzer.py`
- new `backend/services/classification_service.py`
- new `backend/core/constants.py`
- `frontend/src/pages/Analyze.jsx`

### What to change

Add a first-pass content classification gate before fact-checking.

### New schema fields

For text and media:

- `content_category`
- `content_subtype`
- `analysis_route`
- `is_civic_relevant`
- `contains_verifiable_claim`

### Recommended categories

- `OFFICIAL_GOVERNMENT_COMMUNICATION`
- `POLITICAL_CLAIM`
- `NEWS_REPORT`
- `OPINION_OR_COMMENTARY`
- `SATIRE_OR_PARODY`
- `PERSONAL_ANECDOTE`
- `ENTERTAINMENT`
- `NON_CIVIC`

### Analysis routes

- `FULL_VERIFICATION`
- `MISLEADING_REVIEW_ONLY`
- `SATIRE_EXIT`
- `OUT_OF_SCOPE_EXIT`
- `COMMENTARY_CLAIM_EXTRACTION`

### Pipeline placement

#### Text

- after ingestion
- before evidence retrieval

#### Video/audio

- after transcript extraction
- before claim extraction / fact checking

### Decision logic

```python
if content_category in {"SATIRE_OR_PARODY"}:
    verdict = "SATIRE"
    stop pipeline
elif content_category in {"ENTERTAINMENT", "NON_CIVIC"}:
    verdict = "OUT_OF_SCOPE"
    stop pipeline
elif contains_verifiable_claim:
    continue to evidence retrieval
else:
    route to misleading/context review only
```

### Why

A satirical clip should not be labeled as misinformation in the same way as a fabricated policy claim. This gate is required for human-like analysis.

### Effort

Large

### Dependencies

- Depends on Issue 2 verdict taxonomy and Issue 3 refactor.
- Supports Issues 12 and 13.

---

## Issue 12. Real misleading detection

### Problem

The current system is mostly checking for factual mismatch, not contextual misdirection.

### Files to change

- `backend/models/schemas.py`
- `backend/video/schemas.py`
- `backend/crew/config/evidence_tasks.yaml`
- `backend/crew/config/validator_tasks.yaml`
- `backend/crew/config/counter_tasks.yaml`
- `backend/video/config/tasks.yaml`
- new `backend/services/misleading_service.py`
- new `backend/services/verdict_service.py`
- optionally new `backend/crew/misleading_crew.py`
- optionally new `backend/crew/config/misleading_agents.yaml`
- optionally new `backend/crew/config/misleading_tasks.yaml`
- `frontend/src/pages/Analyze.jsx`

### What to change

Introduce a dedicated misleading-analysis layer after evidence retrieval and before final verdict synthesis.

### New schema fields

- `misleading_reason: Optional[str]`
- `missing_context: list[str]`
- `framing_risk: Optional[str]`
- `source_weight_summary: Optional[str]`
- `counter_evidence_found: bool`

### Human-style misleading checks

The service should explicitly evaluate:

- true but missing crucial context
- outdated data used as current
- real statistic applied to wrong geography or population
- selective quoting
- misleading framing designed to induce the wrong conclusion
- real media paired with false caption or title

### Suggested output structure

```python
class MisleadingAssessment(BaseModel):
    verdict_candidate: Verdict
    misleading_reason: str | None
    missing_context: list[str] = []
    framing_risk: str | None = None
    confidence: float
```

### Concrete misleading-detection prompt skeleton

```yaml
misleading_detection_task:
  description: >
    Review the claim, retrieved evidence, source metadata, and presentation context.

    Determine whether the content is misleading even if parts of it are technically true.

    Misleading detection checklist:
    1. Is the claim technically true but missing context that changes its meaning?
    2. Is the statistic real but from a different time period, geography, or sample?
    3. Is an official source being selectively quoted while omitting contradictory context?
    4. Does the visual/audio media fail to match what the title, caption, or framing implies?
    5. Is the framing likely to lead a reasonable viewer to a false conclusion?
    6. Is the claim using a real event or quote in a way that exaggerates or distorts its significance?

    Output rules:
    - If the content is misleading, set verdict_candidate to MISLEADING.
    - misleading_reason must explain exactly how it misleads in one specific paragraph.
    - If it is not misleading, misleading_reason must be null.
    - Do not guess missing facts. Only use retrieved evidence and provided context.

  expected_output: >
    JSON object with:
    - verdict_candidate
    - misleading_reason
    - missing_context
    - framing_risk
    - confidence
```

### Reasoning prompt shape

```yaml
Evaluate not only whether the claim is factually wrong, but whether it creates a false impression through omission, framing, outdated context, selective quoting, or media-caption mismatch.
Return a specific misleading_reason when applicable.
```

### Why

This is the difference between a keyword verifier and an actual fact-checking system.

### Effort

Large

### Dependencies

- Depends on Issue 11 content classification gate.
- Depends on Issue 2 taxonomy and Issue 3 refactor.

---

## Issue 13. Human-style thinking in review

### Problem

The current pipeline is mechanical. It needs skeptical, source-aware, contradiction-seeking reasoning.

### Files to change

- `backend/crew/config/classifier_agents.yaml`
- `backend/crew/config/evidence_agents.yaml`
- `backend/crew/config/counter_agents.yaml`
- `backend/crew/config/validator_agents.yaml`
- `backend/crew/config/classifier_tasks.yaml`
- `backend/crew/config/evidence_tasks.yaml`
- `backend/crew/config/counter_tasks.yaml`
- `backend/crew/config/validator_tasks.yaml`
- `backend/video/config/agents.yaml`
- `backend/video/config/tasks.yaml`
- new `backend/services/verdict_service.py`
- new `backend/services/source_weighting_service.py` or fold into `verdict_service.py`

### What to change

Embed the following reasoning steps into prompts and services:

1. Plausibility check
2. Origin/source instinct
3. Evidence weighting
4. Counter-check against current verdict
5. Plain-language explanation

### Service logic

#### Evidence weighting

Introduce source tiers:

- Tier 1: official government release, official document, court filing
- Tier 2: reputable fact-check or peer-reviewed study
- Tier 3: mainstream reporting
- Tier 4: user-generated or unattributed social content

### Source weighting implementation path

Tier assignment should not be left implicit in prompts. It needs a deterministic backend path.

#### New service

- `backend/services/source_weighting_service.py`

#### Inputs

- `EvidenceMatch`
- source URL
- source type
- optional domain allowlist / official-source registry

#### Outputs

```python
class WeightedEvidence(BaseModel):
    match: EvidenceMatch
    source_tier: int
    source_label: str
    weight: float
    rationale: str
```

#### Tier assignment rules

- Tier 1:
  - `pib.gov.in`
  - `mygov.in`
  - other configured `.gov.in` or official ministry domains
- Tier 2:
  - vetted fact-check partners
  - peer-reviewed or institutional research
- Tier 3:
  - mainstream reporting
- Tier 4:
  - generic web claims, unattributed content, weak-origin references

#### Where it runs

1. `evidence_service.py` retrieves raw matches
2. `source_weighting_service.py` enriches matches with tier/weight
3. `verdict_service.py` uses weighted evidence in synthesis
4. prompts receive the weighted summary, not just raw URLs

#### Pseudocode

```python
weighted = [weight_match(m) for m in matches]
verdict = synthesize_verdict(weighted_evidence=weighted, misleading=assessment)
```

#### Counter-check

After a provisional verdict is formed, the system should actively ask:

- what is the strongest evidence against this verdict?
- if found, does it reduce confidence or change verdict?

### Pseudocode

```python
provisional = synthesize_verdict(evidence, misleading_assessment)
counter = find_strongest_counter_evidence(evidence, provisional)
final = revise_if_needed(provisional, counter)
```

### Output style change

The final counter-statement should be:

- short
- direct
- plain spoken
- honest about uncertainty

Not:

- legalistic
- repetitive
- over-hedged
- fake-authoritative when evidence is weak

### Plain-language enforcement mechanism

This requirement should be enforced both in prompting and validation.

#### Prompt constraints

Update `backend/crew/config/counter_tasks.yaml` to require:

- maximum 3 sentences
- active voice
- no legalistic filler
- no phrases like:
  - "it should be noted"
  - "based on the available information"
  - "it appears that"
  - "the claim in question"

#### Validator addition

Add a new validation flag:

- `overly_hedged_language: bool`

#### Validator rule

Flag outputs that:

- exceed 3 sentences
- contain repeated hedging phrases
- avoid giving a direct plain-language explanation when evidence is sufficient

#### Example prompt shape

```yaml
Write like a careful human explaining the result to a friend.
- Max 3 sentences.
- Prefer short active sentences.
- Avoid legal or bureaucratic phrases.
- Be direct when evidence is strong.
- Be honest and brief when evidence is weak.
```

### Why

This is the core intelligence upgrade. Without it, the system remains a narrow pipeline rather than a thoughtful fact-check assistant.

### Effort

Large

### Dependencies

- Depends on Issues 1, 2, 11, and 12.

## Phase 2: Important

These fixes are not as immediately dangerous as Phase 1, but the system remains inconsistent, harder to maintain, and weaker than it should be without them.

---

## Issue 4. Missing runtime dependencies

### Problem

`backend/requirements.txt` is missing runtime packages already referenced in the code.

### Files to change

- `backend/requirements.txt`
- `README.md`
- `backend/backend.md`

### What to change

Add:

- `tenacity`
- `yt-dlp`
- `PyYAML`
- `static-ffmpeg`

### Recommended entries

```txt
tenacity>=9.0.0
yt-dlp>=2025.1.0
PyYAML>=6.0.2
static-ffmpeg>=2.8
```

### Why

Fresh installs will otherwise fail in the media path.

### Effort

Small

### Dependencies

- None

---

## Issue 5. Zero test coverage

### Problem

The project currently has no unit or integration tests.

### Files to add

- `backend/tests/conftest.py`
- `backend/tests/unit/test_schemas.py`
- `backend/tests/unit/test_trust_score_service.py`
- `backend/tests/unit/test_verdict_service.py`
- `backend/tests/unit/test_identity.py`
- `backend/tests/unit/test_mongo_repository.py`
- `backend/tests/unit/test_classification_service.py`
- `backend/tests/unit/test_misleading_service.py`
- `backend/tests/integration/test_analyze_endpoint.py`
- `backend/tests/integration/test_media_endpoints.py`
- `backend/tests/integration/test_monitor_endpoints.py`
- `backend/tests/fixtures/*.json`
- optionally `frontend/src/**/*.test.jsx` later

### Files to change

- `backend/requirements.txt`
- `README.md`

### What to change

Add a backend test stack, preferably:

- `pytest`
- `pytest-asyncio`
- `httpx`
- `respx` or `responses` for HTTP mocks
- `mongomock` or repository-level mocking

### Conftest and mock-boundary strategy

This issue is large because the codebase mixes:

- async FastAPI routes
- Motor persistence
- CrewAI orchestration
- external HTTP providers
- Pinecone

The tests need hard boundaries around those integrations.

#### `conftest.py` skeleton

```python
import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

from main import app

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
async def async_client():
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.fixture
def fake_monitor_repo(monkeypatch):
    logs = []
    async def _save(entry):
        logs.append(entry)
    async def _get(limit=100):
        return logs[:limit]
    monkeypatch.setattr("db.mongo.save_monitor_log", _save)
    monkeypatch.setattr("db.mongo.get_monitor_logs", _get)
    return logs
```

#### CrewAI mock strategy

Do not mock deep inside CrewAI internals. Mock at the project-owned boundaries:

- `CivicClassifyTool._run`
- `EvidenceRetrieveTool._run`
- `CounterInfoCrew().crew`
- `OutputValidatorCrew().crew`
- `run_video_analysis_crew`
- `extract_transcript`
- `_kickoff_with_retry`

Recommended rule:

- unit tests mock tools/services
- route integration tests mock service layer
- no test should depend on live LLM providers or live CrewAI execution

#### Async Mongo test strategy

Preferred approach:

- repository tests patch `collection.update_one`, `find`, and `insert_one`
- service tests mock repository functions, not Motor itself

This avoids the complexity of a real async Mongo test container in the first phase.

#### Pinecone and facts fixture strategy

Add fixtures for:

- `verified_facts.json`
- Pinecone query responses
- Google Fact Check API responses

Example fixture files:

- `backend/tests/fixtures/verified_facts_minimal.json`
- `backend/tests/fixtures/pinecone_match_response.json`
- `backend/tests/fixtures/google_factcheck_empty.json`
- `backend/tests/fixtures/google_factcheck_supported.json`

#### Suggested monkeypatch boundaries for retrieval tests

```python
monkeypatch.setattr("crew.tools.evidence_tool._load_facts", lambda: fixture_facts)
monkeypatch.setattr("crew.tools.evidence_tool._get_pinecone_index", lambda: fake_index)
monkeypatch.setattr("crew.tools.evidence_tool._search_google_factcheck", fake_gfc)
```

### Priority test targets

#### Deterministic unit tests

- schema validation for new verdicts and content categories
- trust-score calculation
- verdict mapping
- `analysis_key` generation
- upsert filter behavior
- content routing gate logic
- misleading detection post-processing

#### Integration tests with mocks

- `/analyze` with mocked classifier/evidence/generator/validator
- `/analyze-video` with mocked transcript and evidence services
- `/monitor/status` aggregation
- error mapping for missing evidence vs retrieval failure

### Pseudocode example

```python
async def test_save_validated_posts_uses_analysis_key(mongo_repo):
    post = {"analysis_key": "abc", "claim": "same text"}
    await mongo_repo.save_validated_posts([post])
    collection.update_one.assert_called_with(
        {"analysis_key": "abc"},
        ANY,
        upsert=True,
    )
```

### Why

The proposed refactor and intelligence upgrade will be too risky without tests on the deterministic pieces.

### Effort

Large

### Dependencies

- Best started after Issue 3 and Issue 7 begin, so tests target the new boundaries.

---

## Issue 6. Frontend overstates capabilities

### Problem

The home page and dashboard currently present fake stats, invented agents, and mixed demo/live data.

### Files to change

- `frontend/src/pages/Home.jsx`
- `frontend/src/pages/Dashboard.jsx`
- `frontend/src/components/TrustScoreBadge.jsx`
- `frontend/src/lib/api.js`
- `frontend/src/pages/WhatsAppBot.jsx`
- `frontend/src/pages/RumorHeatmap.jsx`
- optionally add `frontend/src/lib/dashboard.js`
- optionally add new backend endpoint for dashboard summary:
  - `backend/api/routes/monitor.py`
  - `backend/services/monitoring_service.py`

### What to change

#### Home page

Replace fake stats and non-existent agents with either:

- real backend-powered summary data
- or static wording that describes actual implemented modules

#### Replace current cards with actual capabilities

- Civic Content Classifier
- Evidence Retriever
- Misleading Context Analyzer
- Counter-Statement Generator
- Output Validator
- Media Transcript Processor

#### Replace fake stat pills

Examples:

- `Text, audio, and video claim analysis`
- `Evidence-backed civic verification`
- `Bilingual counter-statements`

#### Homepage live feed

The audit confirmed that the homepage live feed is also hardcoded demo data and not connected to any backend source.

Scope for this issue must include:

- remove the live feed entirely, or
- wire it to `/monitor/logs`

Do not leave fake civic claims and fake verdicts on the homepage.

#### Dashboard

Either:

1. build a real dashboard summary endpoint, or
2. explicitly label all placeholder values as demo-only

Preferred approach:

- add `/monitor/summary`
- compute:
  - total analyzed
  - verdict distribution
- average trust score
- recent failure rate

#### WhatsApp bot and heatmap review pass

These pages already embed legacy verdict vocabulary and demo framing and need explicit cleanup, not just taxonomy replacement.

Review and update:

- `frontend/src/pages/WhatsAppBot.jsx`
  - remove or relabel `FALSE / PANIC INDUCING`
  - align verdict chips and explanatory copy with canonical verdicts
- `frontend/src/pages/RumorHeatmap.jsx`
  - replace hardcoded `TRUE/FALSE` legend items
  - either mark demo map data clearly or wire it to real backend summaries

If verdict labels are visualized in other pages, give all of them a single shared verdict helper from `frontend/src/lib/verdicts.js`.

### Why

Credibility matters more in this product than in a generic SaaS dashboard. Overstatement directly undermines trust.

### Effort

Medium

### Dependencies

- Depends on Issue 2 taxonomy.
- Improved further by Issue 10 structured logs and Phase 3 monitoring metrics.

---

## Issue 9. Video pipeline inconsistency

### Problem

The video pipeline uses a separate Groq text-analysis path and its own evidence retrieval threshold instead of sharing the main pipeline behavior.

### Files to change

- `backend/video/analyzer.py`
- `backend/video/schemas.py`
- `backend/video/config/tasks.yaml`
- `backend/video/config/agents.yaml`
- `backend/crew/tools/evidence_tool.py`
- `backend/crew/evidence_crew.py`
- `backend/main.py` or new `backend/services/media_pipeline_service.py`
- new `backend/core/llm.py`
- new shared constants in `backend/core/constants.py`

### What to change

#### LLM alignment

Move provider selection into one shared LLM factory:

- primary: Cerebras
- fallback: Together
- media-specific exceptions only for Whisper transcription, which can remain Groq if desired

Important distinction:

- speech-to-text can stay on Groq Whisper
- claim analysis and fact-check reasoning should align with the main text pipeline

#### Retrieval alignment

Remove the custom video-specific retrieval threshold and use the same shared threshold constant as the main evidence path.

Example:

```python
EVIDENCE_MATCH_THRESHOLD = 0.50
```

#### Shared retrieval service

Replace the local `EvidenceRetrieveToolForVideo` logic with a shared service or reusable tool wrapper.

#### Failure-mode alignment

The media pipeline should adopt the same partial-failure contract as the text pipeline:

- retrieval failure -> `INSUFFICIENT_EVIDENCE`
- parser failure with prior transcript success -> `pipeline_status="partial"`
- provider fallback exhaustion -> structured stage error, not silent crash

### Why

Two pipelines with different thresholds and provider behavior will drift in verdict quality and be much harder to debug.

### Effort

Medium

### Dependencies

- Depends on Issue 2 taxonomy and Issue 3 refactor.

## Phase 3: Polish

These changes make the system stronger, clearer, and more maintainable, but the application can still function without them once Phases 1 and 2 are complete.

---

## Additional refinement A. Canonical config and environment cleanup

### Files to change

- `backend/core/config.py`
- `README.md`
- `backend/backend.md`
- add `.env.example` if missing

### What to change

Centralize settings for:

- CORS origins
- model providers
- rate limits
- evidence threshold
- allowed input domains
- feature flags for satire gate and misleading analysis

### Effort

Medium

### Dependencies

- Benefits from Issue 3.

---

## Additional refinement D. Verified facts corpus strategy

### Problem

`backend/crew/data/verified_facts.json` is a major hidden quality bottleneck. Retrieval quality depends on this corpus, and the current plan should treat it as a first-class system dependency.

### Files to change

- `backend/crew/data/verified_facts.json`
- `backend/crew/tools/evidence_tool.py`
- new `backend/scripts/rebuild_verified_facts_index.py`
- new `backend/services/facts_corpus_service.py`
- `README.md`
- `backend/backend.md`

### What to change

Define a corpus maintenance strategy instead of treating the JSON file as static seed data.

#### Recommended stages

1. Short term:
   - keep `verified_facts.json`
   - version it
   - document its source and refresh cadence
2. Medium term:
   - create a rebuild/index script that:
     - validates schema
     - deduplicates
     - re-embeds
     - upserts into Pinecone
3. Long term:
   - supplement static facts with live official feeds and curated fact sources

### Audit adjustment

Corpus expansion is not just a long-term enhancement. It is a hard dependency before meaningful misleading-detection work begins.

Before Issue 12 implementation starts, expand the corpus with at least 3-5 additional source tags beyond the current single-source PIB dataset, for example:

- WHO
- Election Commission
- RBI
- Ministry of Health
- PIB state bulletins

Without that expansion, misleading detection and human-style reasoning will be operating on an evidence base that is too narrow.

#### Add metadata fields to facts

- `updated_at`
- `jurisdiction`
- `topic`
- `source_tier`
- `valid_from`
- `valid_to`

#### Why this matters

Without a maintained corpus, the retrieval system will decay even if prompts and reasoning improve.

### Effort

Medium

### Dependencies

- Connects directly to Issues 9, 12, and 13.

---

## Additional refinement B. Frontend result model upgrade

### Files to change

- `frontend/src/pages/Analyze.jsx`
- `frontend/src/components/TrustScoreBadge.jsx`
- `frontend/src/lib/verdicts.js`

### What to change

Expose the richer backend reasoning fields:

- `content_category`
- `misleading_reason`
- `verdict_reason`
- `source_weight_summary`
- `analysis_route`

This lets the UI explain not just the verdict, but why the system chose that route.

### Effort

Medium

### Dependencies

- Depends on Issues 11, 12, and 13.

---

## Additional refinement C. Monitoring and analytics upgrades

### Files to change

- `backend/services/monitoring_service.py`
- `backend/api/routes/monitor.py`
- `frontend/src/pages/Dashboard.jsx`

### What to change

Add summary metrics that are derived from real stored outputs and logs:

- counts by verdict
- counts by content category
- content routed to satire/out-of-scope
- evidence retrieval failure rate
- average latency by stage
- provider fallback frequency

### Effort

Medium

### Dependencies

- Depends on Issues 10, 11, and 12.

## Cross-Issue Dependency Graph

### Foundational

1. Issue 2 verdict taxonomy
2. Issue 3 backend refactor

### Safety-critical

3. Issue 1 prompt de-speculation
4. Issue 8 CORS/auth/rate limiting
5. Issue 7 stable persistence key

### Intelligence upgrade

6. Issue 11 content type awareness
7. Issue 12 misleading detection
8. Issue 13 human-style reasoning

### Consistency and reliability

9. Issue 9 video pipeline alignment
10. Issue 10 structured logging
11. Issue 5 test suite
12. Issue 6 frontend credibility cleanup
13. Issue 4 dependency fixes

## Suggested Execution Order

### Sprint 1

- remove duplicate helper definitions in `backend/main.py`
- Issue 2 verdict taxonomy
- Issue 1 prompt de-speculation
- Issue 4 dependencies
- Issue 7 stable persistence key

### Sprint 2

- Issue 3 backend refactor
- Issue 8 security baseline
- Issue 10 structured logging

### Sprint 3

- Issue 11 content type gate
- Issue 9 video pipeline alignment

### Sprint 4

- verified facts corpus expansion prerequisite
- Issue 12 misleading detection
- Issue 13 human-style reasoning
- Issue 6 frontend credibility cleanup

### Sprint 5

- Issue 5 test suite expansion
- dashboard analytics polish
- docs cleanup

## Effort Summary

- Issue 1: Small
- Issue 2: Medium
- Issue 3: Large
- Issue 4: Small
- Issue 5: Large
- Issue 6: Medium
- Issue 7: Medium
- Issue 8: Medium
- Issue 9: Large
- Issue 10: Medium
- Issue 11: Large
- Issue 12: Large
- Issue 13: Large

## Final Recommendation

Do not implement the intelligence upgrade on top of the current structure without first completing three foundational changes:

1. standardize verdicts
2. split `backend/main.py`
3. eliminate speculative fallback prompts

If those three are not done first, the new reasoning layers will amplify inconsistency instead of improving quality.

Once the foundation is fixed, the highest-value product improvement is:

- content-type gating
- misleading detection
- contradiction-seeking verdict synthesis

That combination will move TruthMates from a narrow evidence lookup tool toward a genuinely useful civic fact-checking system.
