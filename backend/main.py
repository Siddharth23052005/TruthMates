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
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

load_dotenv()

from crew.truthmates_crew import TruthMatesCrew
from crew.classifier_crew import CivicClassifierCrew
from crew.evidence_crew import EvidenceRetrieverCrew
from crew.counter_info_crew import CounterInfoCrew
from db.mongo import (
    ping_db,
    save_posts,
    save_classified_posts,
    save_verified_posts,
    save_counter_info_posts,
)
from models.schemas import (
    CivicPost,
    ScrapeResponse,
    ClassifiedPost,
    ClassifyResponse,
    VerifiedPost,
    VerifyResponse,
    CounterInfoPost,
    GenerateResponse,
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
_TRANSLATION_MODEL = "ai4bharat/indictrans2-en-hi"
_MAX_TRANSLATION_TOKENS = 256


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


_translation_tokenizer: Optional[AutoTokenizer] = None
_translation_model: Optional[AutoModelForSeq2SeqLM] = None


def _get_translator() -> tuple[AutoTokenizer, AutoModelForSeq2SeqLM]:
    global _translation_tokenizer, _translation_model
    if _translation_tokenizer is None or _translation_model is None:
        _translation_tokenizer = AutoTokenizer.from_pretrained(_TRANSLATION_MODEL)
        _translation_model = AutoModelForSeq2SeqLM.from_pretrained(_TRANSLATION_MODEL)
    return _translation_tokenizer, _translation_model


def _translate_en_to_hi(text: str) -> str:
    if not text:
        return text
    try:
        tokenizer, model = _get_translator()
        inputs = tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=_MAX_TRANSLATION_TOKENS,
        )
        outputs = model.generate(**inputs, max_length=_MAX_TRANSLATION_TOKENS)
        return tokenizer.decode(outputs[0], skip_special_tokens=True)
    except Exception:
        return text


def _trim_sentences(text: str, max_sentences: int = 3) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return text
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return " ".join(sentences[:max_sentences]).strip()


def _clamp_score(value: Optional[float]) -> float:
    try:
        num = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, num))


def _trust_label(score: float) -> str:
    if score <= 40:
        return "Red"
    if score <= 70:
        return "Yellow"
    return "Green"


def _select_source_url(matches: list) -> str:
    for match in matches:
        url = getattr(match, "source_url", "") or ""
        if url:
            return url
    return ""


def _max_pinecone_similarity(matches: list) -> float:
    best = 0.0
    for match in matches:
        if getattr(match, "source_type", "") == "pinecone":
            best = max(best, _clamp_score(getattr(match, "similarity", 0.0)))
    return best


def _compute_trust_score(post: VerifiedPost) -> tuple[float, str]:
    llm_confidence = _clamp_score(getattr(post, "confidence", 0.0))
    pinecone_similarity = _max_pinecone_similarity(post.matches)
    source_found = 1.0 if _select_source_url(post.matches) else 0.0
    crowdsource_reports = _clamp_score(getattr(post, "crowdsource_reports", 0.0))
    deepfake_score = _clamp_score(getattr(post, "deepfake_score", 0.0))

    trust_value = (
        (llm_confidence * 0.30)
        + (pinecone_similarity * 0.30)
        + (source_found * 0.20)
        + (crowdsource_reports * 0.10)
        + (deepfake_score * 0.10)
    )
    trust_score = round(trust_value * 100, 2)
    return trust_score, _trust_label(trust_score)


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


@app.post("/scrape", response_model=GenerateResponse, tags=["Scraper"])
async def scrape():
    """
    Trigger the TruthMates CrewAI agent to scrape PIB and MyGov RSS feeds.

    Steps:
      1. Kick off the crew with the configured RSS URLs.
      2. Parse the JSON output from the data_cleaner agent.
      3. Persist all posts to MongoDB (upsert by link).
    4. Auto-trigger classification, evidence retrieval, and counter-info.
    5. Return counter-info results.
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


@app.post("/classify", response_model=GenerateResponse, tags=["Classifier"])
async def classify(scrape_response: ScrapeResponse):
    """
    Classify scraper output and persist only civic posts.

    Steps:
      1. Run classifier crew on the scraper posts.
      2. Filter out non-civic posts.
      3. Store civic posts in MongoDB.
    4. Auto-trigger evidence retrieval and counter-info.
    5. Return counter-info results.
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


@app.post("/verify", response_model=GenerateResponse, tags=["Verifier"])
async def verify(classify_response: ClassifyResponse):
    """
    Retrieve evidence for classified civic posts.

    Steps:
      1. Run evidence retriever crew on classified posts.
      2. Label posts as verified/unverified based on matches.
      3. Store verification results in MongoDB.
    4. Auto-trigger counter-info generation.
    5. Return counter-info results.
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

        await asyncio.sleep(_PIPELINE_DELAY_SECONDS)
        generate_payload = VerifyResponse(
            status="success",
            count=len(verified_posts),
            posts=verified_posts,
        )
        return await generate(generate_payload)

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/generate", response_model=GenerateResponse, tags=["CounterInfo"])
async def generate(verify_response: VerifyResponse):
    """
    Generate counter-info corrections for verified posts.

    Steps:
      1. Run counter-info crew on verified posts.
      2. Translate corrections to Hindi using IndicTrans2.
      3. Compute trust score and label.
      4. Store counter-info results in MongoDB.
    """
    try:
        crew_instance = CounterInfoCrew()
        trimmed_posts: list[dict] = []
        for post in verify_response.posts[:_MAX_POSTS_PER_RUN]:
            data = post.model_dump(mode="json")
            description = (data.get("description") or "").strip()
            if len(description) > _MAX_DESCRIPTION_CHARS:
                data["description"] = description[:_MAX_DESCRIPTION_CHARS].rstrip()
            data["matches"] = (data.get("matches") or [])[:3]
            trimmed_posts.append(data)

        posts_json = json.dumps(trimmed_posts, ensure_ascii=True)

        result = await _kickoff_with_retry(
            crew_instance.crew(),
            {"posts_json": posts_json},
        )
        raw_text: str = result.raw if hasattr(result, "raw") else str(result)

        clean_text = re.sub(r"```(?:json)?\s*", "", raw_text).strip().rstrip("`")
        try:
            correction_data: list[dict] = json.loads(clean_text)
        except json.JSONDecodeError:
            match = re.search(r"\[.*\]", clean_text, re.DOTALL)
            if match:
                correction_data = json.loads(match.group())
            else:
                raise HTTPException(
                    status_code=502,
                    detail="Generator returned output that could not be parsed as JSON.",
                )

        corrections_by_link: dict[str, str] = {}
        for item in correction_data:
            link = (item.get("link") or "").strip()
            body = (item.get("correction_body") or "").strip()
            if link and body:
                corrections_by_link[link] = body

        counter_posts: list[CounterInfoPost] = []
        for post in verify_response.posts[:_MAX_POSTS_PER_RUN]:
            source_url = _select_source_url(post.matches)
            source_text = source_url or "no official source found"

            is_verified = post.verification_label == "verified" and bool(source_url)
            correction_body = corrections_by_link.get(post.link, "").strip()

            if not is_verified:
                correction_body = "No official source found for this claim."
            elif not correction_body:
                correction_body = "Official sources confirm this claim."

            correction_body = _trim_sentences(correction_body, 3)

            correction_en = f"{correction_body} Source: {source_text}"
            correction_hi_body = _translate_en_to_hi(correction_body)
            correction_hi = f"{correction_hi_body} Source: {source_text}"

            trust_score, trust_label = _compute_trust_score(post)

            counter_posts.append(
                CounterInfoPost(
                    **post.model_dump(),
                    correction_en=correction_en,
                    correction_hi=correction_hi,
                    trust_score=trust_score,
                    trust_label=trust_label,
                )
            )

        await save_counter_info_posts([p.model_dump() for p in counter_posts])

        return GenerateResponse(
            status="success",
            count=len(counter_posts),
            posts=counter_posts,
        )

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
