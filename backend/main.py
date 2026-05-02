"""
TruthMates Backend — FastAPI Application
==========================================
Exposes a POST /scrape endpoint that:
    1. Kicks off the TruthMates CrewAI crew
  2. Parses the resulting JSON
  3. Persists records to MongoDB Atlas (upsert by link)
  4. Returns the full structured response

Run:
  uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""

import json
import os
import re
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from crew.truthmates_crew import TruthMatesCrew
from crew.classifier_crew import CivicClassifierCrew
from db.mongo import ping_db, save_posts, save_classified_posts
from models.schemas import CivicPost, ScrapeResponse, ClassifiedPost, ClassifyResponse

# ── Feed URLs (configurable via .env) ────────────────────────────────────────

PIB_RSS_URL = os.environ.get(
    "PIB_RSS_URL",
    "https://www.pib.gov.in/ViewRss.aspx?reg=1&lang=1",
)
MYGOV_RSS_URL = os.environ.get(
    "MYGOV_RSS_URL",
    "https://www.mygov.in/rss-feed/",
)


# ── Lifespan (startup / shutdown) ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Verify DB connectivity on startup."""
    ok = await ping_db()
    if ok:
        print("✅  MongoDB Atlas connected successfully.")
    else:
        print("⚠️   MongoDB Atlas connection FAILED — check MONGODB_URI in .env")
    yield
    # Shutdown: nothing to clean up for Motor


# ── App Factory ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="TruthMates API",
    description=(
        "Web scraper agent powered by CrewAI + Groq LLaMA 3.3 70B. "
        "Fetches civic posts from PIB and MyGov RSS feeds."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
async def health_check():
    """Health check — returns service status and DB connectivity."""
    db_ok = await ping_db()
    return {
        "service": "TruthMates API",
        "status": "running",
        "database": "connected" if db_ok else "unreachable",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/scrape", response_model=ClassifyResponse, tags=["Scraper"])
async def scrape():
    """
    Trigger the TruthMates CrewAI agent to scrape PIB and MyGov RSS feeds.

    Steps:
      1. Kick off the crew with the configured RSS URLs.
      2. Parse the JSON output from the data_cleaner agent.
      3. Persist all posts to MongoDB (upsert by link).
      4. Return the structured response.
    """
    try:
        # 1. Run the crew
        crew_instance = TruthMatesCrew()
        result = crew_instance.crew().kickoff(
            inputs={
                "pib_url": PIB_RSS_URL,
                "mygov_url": MYGOV_RSS_URL,
            }
        )

        # 2. Extract raw text from CrewOutput
        raw_text: str = result.raw if hasattr(result, "raw") else str(result)

        # 3. Parse JSON — strip markdown fences the LLM may add
        clean_text = re.sub(r"```(?:json)?\s*", "", raw_text).strip().rstrip("`")
        try:
            posts_data: list[dict] = json.loads(clean_text)
        except json.JSONDecodeError:
            # Attempt to locate a JSON array anywhere in the output
            match = re.search(r"\[.*\]", clean_text, re.DOTALL)
            if match:
                posts_data = json.loads(match.group())
            else:
                raise HTTPException(
                    status_code=502,
                    detail="Crew returned output that could not be parsed as JSON.",
                )

        if not isinstance(posts_data, list):
            raise HTTPException(
                status_code=502,
                detail="Crew output is not a JSON array.",
            )

        # 4. Validate through Pydantic
        now = datetime.now(timezone.utc)
        civic_posts: list[CivicPost] = []
        for item in posts_data:
            try:
                civic_posts.append(
                    CivicPost(
                        title=item.get("title", ""),
                        description=item.get("description", ""),
                        link=item.get("link", ""),
                        pub_date=item.get("pub_date"),
                        source=item.get("source", "Unknown"),
                        scraped_at=now,
                    )
                )
            except Exception:
                continue  # Skip malformed individual items

        # 5. Persist to MongoDB
        await save_posts([p.model_dump() for p in civic_posts])

        # Auto-trigger classifier after scraping
        classify_payload = ScrapeResponse(
            status="success",
            count=len(civic_posts),
            posts=civic_posts,
        )
        return await classify(classify_payload)

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/classify", response_model=ClassifyResponse, tags=["Classifier"])
async def classify(scrape_response: ScrapeResponse):
    """
    Classify scraper output and persist only civic posts.

    Steps:
      1. Run classifier crew on the scraper posts.
      2. Filter out non-civic posts.
      3. Store civic posts in MongoDB.
      4. Return classified civic posts only.
    """
    try:
        crew_instance = CivicClassifierCrew()
        posts_json = json.dumps(
            [p.model_dump(mode="json") for p in scrape_response.posts],
            ensure_ascii=True,
        )

        result = crew_instance.crew().kickoff(inputs={"posts_json": posts_json})
        raw_text: str = result.raw if hasattr(result, "raw") else str(result)

        clean_text = re.sub(r"```(?:json)?\s*", "", raw_text).strip().rstrip("`")
        try:
            classified_data: list[dict] = json.loads(clean_text)
        except json.JSONDecodeError:
            match = re.search(r"\[.*\]", clean_text, re.DOTALL)
            if match:
                classified_data = json.loads(match.group())
            else:
                raise HTTPException(
                    status_code=502,
                    detail="Classifier returned output that could not be parsed as JSON.",
                )

        civic_posts: list[ClassifiedPost] = []
        for item in classified_data:
            if item.get("label") != "civic":
                continue

            civic_posts.append(ClassifiedPost(**item))

        await save_classified_posts([p.model_dump() for p in civic_posts])

        return ClassifyResponse(
            status="success",
            count=len(civic_posts),
            posts=civic_posts,
        )

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
