# TruthMates
Civic misinformation analysis platform with React/Vite frontend and FastAPI backend supporting text, video, and audio inputs.

## Current Build Status
Working: End-to-end analysis pipeline for text/video/audio, schema-driven API contracts, custom retrieval/classification tools, MongoDB persistence, Pinecone evidence search.
Not working: Operational readiness incomplete, no automated tests, UI overstates some capabilities, prompts encourage unsupported reasoning.

## API Endpoints
GET /
POST /analyze
POST /analyze-video
POST /analyze-audio
POST /scrape
POST /classify
POST /verify
POST /generate
POST /validate
GET /monitor/logs
GET /monitor/status
GET /monitor/summary
POST /social/crawl
GET /social/crawl-status
GET /social/entries
GET /social/entries/{entry_id}
POST /social/entries/{entry_id}/review
GET /social/stats
GET /api/trending
GET /api/heatmap
GET /api/trending-claims
POST /whatsapp/webhook

## Agents
TruthMatesCrew: Scrapes PIB and MyGov RSS feeds, cleans results, returns structured JSON list of civic posts.
CivicClassifierCrew: Classifies scraped posts for civic relevance.
EvidenceRetrieverCrew: Retrieves evidence for claims from Pinecone and Google Fact Check.
CounterInfoCrew: Generates counter-information corrections.
OutputValidatorCrew: Validates counter-information outputs.
MonitoringCrew: Reviews and monitors agent outputs.

## Tech Stack
crewai, fastapi, uvicorn, motor, pymongo, beautifulsoup4, lxml, requests, python-dotenv, pydantic, tenacity, pyyaml, transformers, torch, langdetect, sentencepiece, static-ffmpeg, sentence-transformers, pinecone, numpy, yt-dlp, guardrails-ai, pytest, pytest-asyncio, httpx, slowapi, groq, litellm, react, vite, tailwindcss, axios, framer-motion, lucide-react, react-router-dom.

## Environment Variables
CEREBRAS_API_KEY
TOGETHER_API_KEY
MONGODB_URI
MONGODB_DB_NAME
PIB_RSS_URL
MYGOV_RSS_URL
PINECONE_API_KEY
PINECONE_CLOUD
PINECONE_REGION
GOOGLE_FACT_CHECK_API_KEY
TRUTHMATES_PUBLIC_API_KEY
TRUTHMATES_ADMIN_API_KEY
ALLOWED_ORIGINS
PUBLIC_RATE_LIMIT
ADMIN_RATE_LIMIT
TWILIO_ACCOUNT_SID
TWILIO_AUTH_TOKEN
TWILIO_WHATSAPP_NUMBER
VITE_API_BASE_URL

## Frontend Pages and Routes
/ (Home)
/analyze (Analyze)
/trending (Trending)
/citizen-reporter (CitizenReporter)
/social-monitor (SocialMonitor)
/about (About)

## Known Issues
Speculative reasoning in prompts when evidence missing.
Inconsistent verdict labels across codebase.
Backend orchestration over-concentrated in main.py.
Duplicate helper definitions in main.py.
Upsert identity for validated outputs uses claim only.
No automated test coverage.
UI overstates implemented capabilities.

## What is Left to Build
Phase 1: Fix speculative prompts, standardize verdicts, separate routes from business logic, add baseline tests, fix upsert identity, enforce CORS/API protection.
Phase 2: Upgrade pipeline to skeptical journalist reasoning, detect misleading framing, align text/video pipelines, add structured logging with correlation IDs.
Phase 3: Implement new backend module structure, add content type classifier, scope gate, claim extraction, source assessment, misleading detection, counter-check, validation.