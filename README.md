# TruthMates

TruthMates is a civic misinformation analysis platform with a React/Vite frontend and a FastAPI backend. It supports text claims, video URLs, and audio uploads, then routes each input through classification, evidence retrieval, verdict synthesis, and output validation.

## Current Capabilities
- Text, video, and audio analysis paths
- Pre-verification routing for `VERIFY`, `SATIRE_EXIT`, and `OUT_OF_SCOPE_EXIT`
- Evidence retrieval through Pinecone plus Google Fact Check
- Human-style verdict synthesis with misleading detection and source weighting
- MongoDB persistence with stable `analysis_key` identities
- Structured monitoring endpoints and request-level correlation IDs

## Backend
From `backend/`:

```bash
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Required configuration is listed in [.env.example](./.env.example).

### Main Endpoints
- `GET /`
- `POST /analyze`
- `POST /analyze-video`
- `POST /analyze-audio`
- `POST /scrape`
- `POST /classify`
- `POST /verify`
- `POST /generate`
- `POST /validate`
- `GET /monitor/logs`
- `GET /monitor/status`
- `GET /monitor/summary`

### API Keys
- Public routes read `X-API-Key` against `TRUTHMATES_PUBLIC_API_KEY`
- Admin monitor/pipeline routes read `X-API-Key` against `TRUTHMATES_ADMIN_API_KEY`

## Frontend
From `frontend/`:

```bash
npm install
npm run dev
```

Frontend env vars:
- `VITE_API_BASE_URL`
- `VITE_PUBLIC_API_KEY`
- `VITE_ADMIN_API_KEY`

## Test Suite
The repo now includes pytest-based backend coverage under `tests/`.

```bash
pytest tests -q
```

Coverage targets include:
- schema validation
- `analysis_key` generation
- verdict normalization and trust scoring helpers
- content routing normalization
- misleading/source-weight post-processing
- Mongo upsert identity behavior
- `/analyze`, `/analyze-video`, `/monitor/status`, and `/monitor/summary` route contracts with mocked services

## Notes
- Groq remains in use only for Whisper transcription in the media intake layer.
- Cerebras is the primary LLM provider for reasoning tasks, with Together as fallback.
- `backend/crew/data/verified_facts.json` is now a broader official-source seed corpus, but it is still a curated local corpus and should continue to be maintained.
