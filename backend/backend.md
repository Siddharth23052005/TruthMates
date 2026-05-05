# TruthMates Backend Notes

## Overview
TruthMates backend is a FastAPI service that runs a CrewAI workflow to scrape PIB and MyGov RSS feeds, clean and deduplicate the results, and persist them to MongoDB Atlas. It now also classifies posts as civic or non-civic, retrieves evidence via Pinecone + Google Fact Check API, generates counter-info corrections with trust scores, and validates outputs. The main entrypoint is the `POST /scrape` endpoint, which auto-triggers classification, verification, counter-info, and validation.

## Current Architecture
1. FastAPI `POST /scrape` triggers the CrewAI scraping workflow.
2. RSS fetch agent pulls RSS items from configured URLs.
3. Data cleaner agent strips HTML, normalizes dates, and deduplicates by link.
4. Results are upserted into MongoDB with a `scraped_at` timestamp.
5. Classifier crew runs, labels posts as civic/non-civic, and filters non-civic.
6. Civic classified posts are stored in MongoDB with `classified_at`.
7. Evidence retriever crew matches claims to facts (Pinecone + Google Fact Check).
8. Verification results are stored in MongoDB with `verified_at`.
9. Counter-info generator creates corrections, Hindi translations, and trust scores.
10. Counter-info results are stored in MongoDB with `generated_at`.
11. Output validator checks sources, contradictions, trust-score logic, and Hindi presence.
12. Validated results are stored in MongoDB with `validated_at`.
13. The API returns `{status, count, posts}` with validated outputs.

## Key Files
- `main.py`: FastAPI app, routes, CORS, crew kickoff, JSON parsing, persistence.
- `crew/truthmates_crew.py`: CrewAI wiring (agents, tasks, Groq LLM).
- `crew/classifier_crew.py`: CrewAI classifier crew (CivicClassifyTool).
- `crew/evidence_crew.py`: CrewAI evidence retriever crew (EvidenceRetrieveTool).
- `crew/counter_info_crew.py`: CrewAI counter-info generator crew.
- `crew/output_validator_crew.py`: CrewAI output validator crew.
- `crew/config/agents.yaml`: Agent roles, goals, and backstories.
- `crew/config/tasks.yaml`: Task flow and expected outputs.
- `crew/config/classifier_agents.yaml`: Classifier agent config.
- `crew/config/classifier_tasks.yaml`: Classifier task config.
- `crew/config/counter_agents.yaml`: Counter-info agent config.
- `crew/config/counter_tasks.yaml`: Counter-info task config.
- `crew/config/validator_agents.yaml`: Output validator agent config.
- `crew/config/validator_tasks.yaml`: Output validator task config.
- `crew/tools/rss_tool.py`: RSS fetch tool (requests + BeautifulSoup XML parser).
- `crew/tools/clean_tool.py`: Cleaning + dedup tool (HTML strip, ISO dates).
- `crew/tools/classify_tool.py`: BERT/IndicBERT classifier tool.
- `crew/tools/evidence_tool.py`: Pinecone + Google Fact Check evidence retriever.
- `crew/tools/url_check_tool.py`: URL reachability checker for validation.
- `crew/data/verified_facts.json`: Seed PIB facts (replace placeholders with real facts).
- `db/mongo.py`: Motor async client, upsert by `link`, `scraped_at` timestamp.
- `models/schemas.py`: Pydantic models for posts and API response.
- `.env.example`: Required environment variables and default RSS URLs.

## Environment Variables
- `GROQ_API_KEY`: Groq API key for the CrewAI LLM.
- `MONGODB_URI`: MongoDB Atlas connection string.
- `MONGODB_DB_NAME`: Database name (default: `truthmates`).
- `PIB_RSS_URL`: PIB RSS feed URL.
- `MYGOV_RSS_URL`: MyGov RSS feed URL.
- `PINECONE_API_KEY`: Pinecone API key.
- `PINECONE_CLOUD`: Pinecone cloud provider (default: aws).
- `PINECONE_REGION`: Pinecone region (default: us-east-1).
- `GOOGLE_FACT_CHECK_API_KEY`: Google Fact Check API key.

## Endpoints
- `GET /`: Health check and DB connectivity status.
- `POST /scrape`: Runs scrape + clean + classify + verify + generate + validate.
- `POST /classify`: Classifies a provided scraper output and triggers verify + generate + validate.
- `POST /verify`: Retrieves evidence and triggers generate + validate.
- `POST /generate`: Generates counter-info and triggers validation.
- `POST /validate`: Validates counter-info outputs and returns final verdicts.

## Data Contract (Scrape Output)
Each post has:
- `title`: headline text
- `description`: cleaned text with HTML removed
- `link`: canonical URL
- `pub_date`: ISO 8601 string or null
- `source`: feed name (PIB or MyGov)
- `scraped_at`: UTC timestamp added during persistence

Classification adds:
- `label`: civic | non-civic
- `confidence`: 0-1 confidence score
- `language`: detected language code
- `needs_review`: true if confidence < 0.75

Verification adds:
- `verification_label`: verified | unverified
- `matches`: list of evidence matches with:
	- `fact_text`
	- `similarity`
	- `source_url`
	- `source_type` (pinecone | google_fact_check)

Counter-info adds:
- `correction_en`: plain language correction with source citation
- `correction_hi`: Hindi translation (IndicTrans2)
- `trust_score`: 0-100 score
- `trust_label`: Red | Yellow | Green

Validation adds:
- `verdict`: TRUE | FALSE | MISLEADING | UNVERIFIED
- `flags`: contradiction, invalid URL, trust mismatch, missing Hindi, hallucinated stats

## MongoDB Details
- Collection: `civic_posts`
- Upsert key: `link`
- Each scrape overwrites existing data for the same link and updates `scraped_at`.

- Collection: `civic_classified`
- Upsert key: `link`
- Each classification overwrites existing data for the same link and updates `classified_at`.

- Collection: `civic_verified`
- Upsert key: `link`
- Each verification overwrites existing data for the same link and updates `verified_at`.

- Collection: `civic_counter_info`
- Upsert key: `link`
- Each generation overwrites existing data for the same link and updates `generated_at`.

- Collection: `civic_validated`
- Upsert key: `claim`
- Each validation overwrites existing data for the same claim and updates `validated_at`.

## Notes on Feed Handling
- PIB and MyGov RSS URLs are configurable via `.env`.
- Fetch failures are handled gracefully, returning an empty list for that feed.

## Run Locally
1. `pip install -r requirements.txt`
2. Configure `.env` with Groq and MongoDB values.
3. `uvicorn main:app --reload --host 0.0.0.0 --port 8000`
4. `curl -X POST http://localhost:8000/scrape`

## Environment
- Virtual environment manager: uv
- uv version: 0.11.8

## Progress Log (2026-05-02)
- Added Civic Classifier Crew (Groq LLaMA 3.3 70B + CivicClassifyTool).
- Implemented BERT/IndicBERT embedding-based classification with confidence threshold.
- Added /classify endpoint and auto-triggered classification after /scrape.
- Stored classified civic posts in MongoDB (civic_classified).
- Updated schemas and dependencies.
- Added Evidence Retriever Crew (Groq LLaMA 3.3 70B + EvidenceRetrieveTool).
- Integrated Pinecone index truthmates-facts with seed facts placeholders.
- Added /verify endpoint and auto-triggered verification after /classify.
- Stored verification results in MongoDB (civic_verified).
- Replaced placeholder facts with 30 PIB-verified facts and added source_tag metadata.
- Added exponential backoff retry for Groq rate limits and switched to llama-3.1-8b-instant for testing.
- Reinforced no-external-tools instructions to prevent rogue tool calls.
- Added limits: truncate descriptions to 300 chars, cap 10 posts per run, and insert 3s delays between pipeline stages.
- Added Counter-Info Generator Crew and /generate endpoint with trust score and Hindi translation.
- Added Output Validator Crew and /validate endpoint with retry logic.
- Updated validator verdict rules and trust-score alignment.
