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

import asyncio
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
from crew.evidence_crew import EvidenceRetrieverCrew
from db.mongo import ping_db, save_posts, save_classified_posts, save_verified_posts
from models.schemas import (
    CivicPost,
    ScrapeResponse,
    ClassifiedPost,
    ClassifyResponse,
    VerifiedPost,
    VerifyResponse,
)

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


# ── Retry helpers (Groq rate limits) ─────────────────────────────────────────

_RETRY_BASE_DELAY_SECONDS = 2
_MAX_RETRIES = 3
_PIPELINE_DELAY_SECONDS = 3
_MAX_POSTS_PER_RUN = 10
_MAX_DESCRIPTION_CHARS = 300


def _is_rate_limit_error(message: str) -> bool:
    lowered = message.lower()
    return (
        "rate limit" in lowered
        or "rate_limit" in lowered
        or "rate_limit_exceeded" in lowered
    )


async def _kickoff_with_retry(crew_instance, inputs: dict):
    retries = 0
    while True:
        try:
            return crew_instance.kickoff(inputs=inputs)
        except Exception as exc:
            if _is_rate_limit_error(str(exc)) and retries < _MAX_RETRIES:
                delay = _RETRY_BASE_DELAY_SECONDS * (2 ** retries)
                retries += 1
                await asyncio.sleep(delay)
                continue
            raise


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


@app.post("/scrape", response_model=VerifyResponse, tags=["Scraper"])
async def scrape():
    """
    Trigger the TruthMates CrewAI agent to scrape PIB and MyGov RSS feeds.

    Steps:
      1. Kick off the crew with the configured RSS URLs.
      2. Parse the JSON output from the data_cleaner agent.
      3. Persist all posts to MongoDB (upsert by link).
    4. Auto-trigger classification and evidence retrieval.
    5. Return verified civic posts only.
    """
    try:
        # 1. Run the crew
        crew_instance = TruthMatesCrew()
        result = await _kickoff_with_retry(
            crew_instance.crew(),
            {
                "pib_url": PIB_RSS_URL,
                "mygov_url": MYGOV_RSS_URL,
            },
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
                description = (item.get("description", "") or "").strip()
                if len(description) > _MAX_DESCRIPTION_CHARS:
                    description = description[:_MAX_DESCRIPTION_CHARS].rstrip()

                civic_posts.append(
                    CivicPost(
                        title=item.get("title", ""),
                        description=description,
                        link=item.get("link", ""),
                        pub_date=item.get("pub_date"),
                        source=item.get("source", "Unknown"),
                        scraped_at=now,
                    )
                )
            except Exception:
                continue  # Skip malformed individual items

        civic_posts = civic_posts[:_MAX_POSTS_PER_RUN]

        # 5. Persist to MongoDB
        await save_posts([p.model_dump() for p in civic_posts])

        # Auto-trigger classifier after scraping
        await asyncio.sleep(_PIPELINE_DELAY_SECONDS)
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


@app.post("/classify", response_model=VerifyResponse, tags=["Classifier"])
async def classify(scrape_response: ScrapeResponse):
    """
    Classify scraper output and persist only civic posts.

    Steps:
      1. Run classifier crew on the scraper posts.
      2. Filter out non-civic posts.
      3. Store civic posts in MongoDB.
    4. Auto-trigger evidence retrieval.
    5. Return verified civic posts only.
    """
    try:
        crew_instance = CivicClassifierCrew()
        trimmed_posts: list[dict] = []
        for post in scrape_response.posts[:_MAX_POSTS_PER_RUN]:
            data = post.model_dump(mode="json")
            description = (data.get("description") or "").strip()
            if len(description) > _MAX_DESCRIPTION_CHARS:
                data["description"] = description[:_MAX_DESCRIPTION_CHARS].rstrip()
            trimmed_posts.append(data)

        posts_json = json.dumps(trimmed_posts, ensure_ascii=True)

        result = await _kickoff_with_retry(
            crew_instance.crew(),
            {"posts_json": posts_json},
        )
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

        await asyncio.sleep(_PIPELINE_DELAY_SECONDS)
        verify_payload = ClassifyResponse(
            status="success",
            count=len(civic_posts),
            posts=civic_posts,
        )
        return await verify(verify_payload)

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/verify", response_model=VerifyResponse, tags=["Verifier"])
async def verify(classify_response: ClassifyResponse):
    """
    Retrieve evidence for classified civic posts.

    Steps:
      1. Run evidence retriever crew on classified posts.
      2. Label posts as verified/unverified based on matches.
      3. Store verification results in MongoDB.
      4. Return verified posts only.
    """
    try:
        crew_instance = EvidenceRetrieverCrew()
        trimmed_posts: list[dict] = []
        for post in classify_response.posts[:_MAX_POSTS_PER_RUN]:
            data = post.model_dump(mode="json")
            description = (data.get("description") or "").strip()
            if len(description) > _MAX_DESCRIPTION_CHARS:
                data["description"] = description[:_MAX_DESCRIPTION_CHARS].rstrip()
            trimmed_posts.append(data)

        posts_json = json.dumps(trimmed_posts, ensure_ascii=True)

        result = await _kickoff_with_retry(
            crew_instance.crew(),
            {"posts_json": posts_json},
        )
        raw_text: str = result.raw if hasattr(result, "raw") else str(result)

        clean_text = re.sub(r"```(?:json)?\s*", "", raw_text).strip().rstrip("`")
        try:
            verified_data: list[dict] = json.loads(clean_text)
        except json.JSONDecodeError:
            match = re.search(r"\[.*\]", clean_text, re.DOTALL)
            if match:
                verified_data = json.loads(match.group())
            else:
                raise HTTPException(
                    status_code=502,
                    detail="Verifier returned output that could not be parsed as JSON.",
                )

        verified_posts: list[VerifiedPost] = []
        for item in verified_data:
            verified_posts.append(VerifiedPost(**item))

        await save_verified_posts([p.model_dump() for p in verified_posts])

        return VerifyResponse(
            status="success",
            count=len(verified_posts),
            posts=verified_posts,
        )

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
