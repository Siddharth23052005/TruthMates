# TruthMates Backend Notes

## Overview
TruthMates backend is a FastAPI service that runs a CrewAI workflow to scrape PIB and MyGov RSS feeds, clean and deduplicate the results, and persist them to MongoDB Atlas. The main entrypoint is the `POST /scrape` endpoint.

## Current Architecture
1. FastAPI `POST /scrape` triggers the CrewAI workflow.
2. RSS fetch agent pulls RSS items from configured URLs.
3. Data cleaner agent strips HTML, normalizes dates, and deduplicates by link.
4. Results are upserted into MongoDB with a `scraped_at` timestamp.
5. The API returns `{status, count, posts}` with the cleaned list.

## Key Files
- `main.py`: FastAPI app, routes, CORS, crew kickoff, JSON parsing, persistence.
- `crew/truthmates_crew.py`: CrewAI wiring (agents, tasks, Groq LLM).
- `crew/config/agents.yaml`: Agent roles, goals, and backstories.
- `crew/config/tasks.yaml`: Task flow and expected outputs.
- `crew/tools/rss_tool.py`: RSS fetch tool (requests + BeautifulSoup XML parser).
- `crew/tools/clean_tool.py`: Cleaning + dedup tool (HTML strip, ISO dates).
- `db/mongo.py`: Motor async client, upsert by `link`, `scraped_at` timestamp.
- `models/schemas.py`: Pydantic models for posts and API response.
- `.env.example`: Required environment variables and default RSS URLs.

## Environment Variables
- `GROQ_API_KEY`: Groq API key for the CrewAI LLM.
- `MONGODB_URI`: MongoDB Atlas connection string.
- `MONGODB_DB_NAME`: Database name (default: `truthmates`).
- `PIB_RSS_URL`: PIB RSS feed URL.
- `MYGOV_RSS_URL`: MyGov RSS feed URL.

## Endpoints
- `GET /`: Health check and DB connectivity status.
- `POST /scrape`: Runs the CrewAI pipeline, stores posts, returns the result.

## Data Contract (Scrape Output)
Each post has:
- `title`: headline text
- `description`: cleaned text with HTML removed
- `link`: canonical URL
- `pub_date`: ISO 8601 string or null
- `source`: feed name (PIB or MyGov)
- `scraped_at`: UTC timestamp added during persistence

## MongoDB Details
- Collection: `civic_posts`
- Upsert key: `link`
- Each scrape overwrites existing data for the same link and updates `scraped_at`.

## Notes on Feed Handling
- PIB and MyGov RSS URLs are configurable via `.env`.
- Fetch failures are handled gracefully, returning an empty list for that feed.

## Run Locally
1. `pip install -r requirements.txt`
2. Configure `.env` with Groq and MongoDB values.
3. `uvicorn main:app --reload --host 0.0.0.0 --port 8000`
4. `curl -X POST http://localhost:8000/scrape`
