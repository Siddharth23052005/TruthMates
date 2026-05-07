# TruthMates (CivicShield)

Multi-agent AI platform that detects, verifies, and counters civic misinformation from text or URLs, with evidence retrieval, trust scoring, and validation.

## What It Does
- Scrapes PIB and MyGov RSS feeds for civic updates.
- Classifies content as civic or non-civic.
- Retrieves evidence with Pinecone and Google Fact Check.
- Generates counter-info statements in English and Hindi with trust scores.
- Validates outputs for contradictions, source reachability, and trust-score logic.
- Provides monitoring logs for pipeline health.

## Repo Structure
- backend: FastAPI + CrewAI orchestration, MongoDB persistence, Pinecone retrieval.
- frontend: React + Vite + Tailwind UI.

## Quickstart

### Backend
1) Install dependencies:
```bash
cd backend
pip install -r requirements.txt
```

2) Create a .env file with required keys:
```
CEREBRAS_API_KEY=...
MONGODB_URI=...
MONGODB_DB_NAME=truthmates
PIB_RSS_URL=https://www.pib.gov.in/ViewRss.aspx?reg=1&lang=1
MYGOV_RSS_URL=https://www.mygov.in/rss-feed/
PINECONE_API_KEY=...
PINECONE_CLOUD=aws
PINECONE_REGION=us-east-1
GOOGLE_FACT_CHECK_API_KEY=...
```

3) Run the API:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## API Endpoints
- GET / : Health check.
- POST /scrape : Scrape RSS and run full pipeline.
- POST /classify : Classify posts and run downstream steps.
- POST /verify : Evidence retrieval, then generate + validate.
- POST /generate : Counter-info generation, then validate.
- POST /validate : Output validation.
- POST /analyze : Analyze a raw claim (no RSS scraping).
- GET /monitor/logs : Monitoring decisions.
- GET /monitor/status : Pipeline health.

## Example Requests

### Analyze a raw claim
```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"claim":"PM Surya Ghar Muft Bijli Yojana provides 300 units free electricity via rooftop solar"}'
```

### Scrape RSS feeds
```bash
curl -X POST http://localhost:8000/scrape
```

## LLM Provider
- Current LLM: Cerebras (model llama3.1-8b, base URL https://api.cerebras.ai/v1).

## Notes
- /analyze bypasses RSS and uses CivicClassifyTool + EvidenceRetrieveTool directly.
- Monitoring is skipped during /analyze for counter-info generation and validation.
- Pinecone retrieval logs index stats, query text, and similarity scores for debugging.

## Troubleshooting
- Cerebras 429 queue errors mean high traffic. Retry after a short wait.
- If Pinecone returns no matches, confirm facts are indexed and API key is valid.

## License
MIT (update if different)
