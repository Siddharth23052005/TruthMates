"""
TruthMates Backend — FastAPI Application
========================================
Exposes endpoints that:
    1. Kick off the TruthMates CrewAI workflow.
    2. Parse the resulting JSON.
    3. Persist records to MongoDB Atlas (upsert by link).
    4. Return structured responses.
    5. Analyze raw claims via /analyze.

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
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from guardrails import Guard
from pydantic import BaseModel
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

load_dotenv()

from crew.truthmates_crew import TruthMatesCrew
from crew.classifier_crew import CivicClassifierCrew
from crew.evidence_crew import EvidenceRetrieverCrew
from crew.counter_info_crew import CounterInfoCrew
from crew.output_validator_crew import OutputValidatorCrew
from crew.monitoring_crew import MonitoringCrew
from crew.tools.classify_tool import CivicClassifyTool
from crew.tools.evidence_tool import EvidenceRetrieveTool
from db.mongo import (
    ping_db,
    save_posts,
    save_classified_posts,
    save_verified_posts,
    save_counter_info_posts,
    save_validated_posts,
    save_monitor_log,
    get_monitor_logs,
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
    ValidateResponse,
    ValidatedPost,
    ValidationFlags,
    MonitorLogsResponse,
    MonitorLog,
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
_VALIDATION_MAX_RETRIES = 2
_MONITOR_MAX_RETRIES = 2
_MONITOR_PREVIEW_CHARS = 1200


class AnalyzeRequest(BaseModel):
    claim: str


def _is_rate_limit_error(message: str) -> bool:
    lowered = message.lower()
    return (
        "rate limit" in lowered
        or "rate_limit" in lowered
        or "rate_limit_exceeded" in lowered
    )


def _parse_tool_json(text: str) -> list[dict]:
    clean_text = re.sub(r"```(?:json)?\s*", "", text).strip().rstrip("`")
    try:
        parsed = json.loads(clean_text)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


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


def _sources_from_matches(matches: list) -> list[str]:
    sources: list[str] = []
    for match in matches:
        url = getattr(match, "source_url", "") or ""
        if url and url not in sources:
            sources.append(url)
    return sources


def _extract_confidence(output) -> Optional[float]:
    values: list[float] = []
    if isinstance(output, list):
        for item in output:
            if isinstance(item, dict) and "confidence" in item:
                values.append(_clamp_score(item.get("confidence")))
    elif isinstance(output, dict):
        posts = output.get("posts")
        if isinstance(posts, list):
            for item in posts:
                if isinstance(item, dict) and "confidence" in item:
                    values.append(_clamp_score(item.get("confidence")))
    if not values:
        return None
    return min(values)


def _has_hallucination_flags(output) -> bool:
    if isinstance(output, list):
        for item in output:
            if isinstance(item, dict):
                flags = item.get("flags") or {}
                if flags.get("hallucinated_stats") is True:
                    return True
                if item.get("hallucinated_stats") is True:
                    return True
    elif isinstance(output, dict):
        posts = output.get("posts")
        if isinstance(posts, list):
            return _has_hallucination_flags(posts)
        items = output.get("items")
        if isinstance(items, list):
            return _has_hallucination_flags(items)
    return False


def _is_output_complete(output) -> bool:
    if output is None:
        return False
    if isinstance(output, list):
        return len(output) > 0
    if isinstance(output, dict):
        if "posts" in output and isinstance(output["posts"], list):
            return len(output["posts"]) > 0
        if "items" in output and isinstance(output["items"], list):
            return len(output["items"]) > 0
        return len(output.keys()) > 0
    return True


def _truncate_for_log(value, max_chars: int = 4000) -> str:
    try:
        text = json.dumps(value, ensure_ascii=True)
    except Exception:
        text = str(value)
    if len(text) > max_chars:
        return text[:max_chars] + "..."
    return text


async def _monitor_review(agent_name: str, input_payload, output_payload, checks: dict) -> str:
    crew_instance = MonitoringCrew()
    output_preview = _truncate_for_log(output_payload, _MONITOR_PREVIEW_CHARS)
    inputs = {
        "agent_name": agent_name,
        "checks_json": json.dumps(checks, ensure_ascii=True),
        "error": checks.get("error") or "",
        "output_preview": output_preview,
    }

    result = await _kickoff_with_retry(crew_instance.crew(), inputs)
    raw_text: str = result.raw if hasattr(result, "raw") else str(result)
    clean_text = re.sub(r"```(?:json)?\s*", "", raw_text).strip().rstrip("`")

    try:
        payload = json.loads(clean_text)
        status = (payload.get("status") or "").upper()
        if status in {"PASS", "FAIL"}:
            return status
    except Exception:
        pass

    return "PASS" if checks.get("pass") else "FAIL"


async def _log_monitor_decision(
    agent_name: str,
    input_payload,
    output_payload,
    status: str,
    retries: int,
    checks: dict,
) -> None:
    await save_monitor_log(
        {
            "agent_name": agent_name,
            "input": _truncate_for_log(input_payload),
            "output": _truncate_for_log(output_payload),
            "status": status,
            "retries": retries,
            "checks": checks,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )


async def _run_with_monitor(
    agent_name: str,
    input_payload,
    runner,
):
    retries = 0
    while True:
        output_payload = None
        error_message = ""
        try:
            output_payload = await runner()
        except Exception as exc:
            error_message = str(exc)

        confidence = _extract_confidence(output_payload)
        confidence_ok = True if confidence is None else confidence >= 0.75
        checks = {
            "complete": _is_output_complete(output_payload),
            "confidence_ok": confidence_ok,
            "hallucination_flags": _has_hallucination_flags(output_payload),
            "error": error_message,
        }
        checks["pass"] = (
            checks["complete"]
            and checks["confidence_ok"]
            and not checks["hallucination_flags"]
            and not checks["error"]
        )

        status = await _monitor_review(agent_name, input_payload, output_payload, checks)
        await _log_monitor_decision(
            agent_name,
            input_payload,
            output_payload,
            status,
            retries,
            checks,
        )

        if status == "PASS" and checks["pass"]:
            return output_payload

        if retries >= _MONITOR_MAX_RETRIES:
            raise HTTPException(
                status_code=502,
                detail=f"Monitoring failed for {agent_name} after retries.",
            )

        retries += 1


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


@app.get("/monitor/logs", response_model=MonitorLogsResponse, tags=["Monitor"])
async def monitor_logs():
    logs = await get_monitor_logs(limit=200)
    clean_logs = []
    for log in logs:
        log["id"] = str(log.pop("_id"))
        clean_logs.append(log)

    return MonitorLogsResponse(
        status="success",
        count=len(clean_logs),
        logs=[MonitorLog(**log) for log in clean_logs],
    )


@app.get("/monitor/status", tags=["Monitor"])
async def monitor_status():
    logs = await get_monitor_logs(limit=200)
    last_by_agent: dict[str, str] = {}
    for log in logs:
        name = log.get("agent_name")
        if name and name not in last_by_agent:
            last_by_agent[name] = log.get("status", "UNKNOWN")

    overall = "healthy" if all(v == "PASS" for v in last_by_agent.values()) else "degraded"
    return {
        "status": overall,
        "agents": last_by_agent,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/analyze", response_model=ValidateResponse, tags=["Analyzer"])
async def analyze(payload: AnalyzeRequest):
    """
    Analyze a raw claim directly without RSS scraping.

    Steps:
      1. Wrap claim into a single CivicPost.
      2. Run classifier -> evidence -> generator -> validator.
      3. Return validated outputs.
    """
    claim_text = (payload.claim or "").strip()
    if not claim_text:
        raise HTTPException(status_code=422, detail="Claim text is required.")

    now = datetime.now(timezone.utc)
    manual_post = CivicPost(
        title=claim_text,
        description=claim_text[:_MAX_DESCRIPTION_CHARS],
        link=f"manual://{uuid4()}",
        pub_date=None,
        source="Manual",
        scraped_at=now,
    )

    posts_json = json.dumps([manual_post.model_dump(mode="json")], ensure_ascii=True)

    classifier_tool = CivicClassifyTool()
    classified_raw = classifier_tool._run(posts_json)
    classified_items = _parse_tool_json(classified_raw)
    if not classified_items:
        return ValidateResponse(status="success", count=0, posts=[])

    civic_posts: list[ClassifiedPost] = []
    for item in classified_items:
        if item.get("label") != "civic":
            continue
        civic_posts.append(ClassifiedPost(**item))

    await save_classified_posts([p.model_dump() for p in civic_posts])
    if not civic_posts:
        return ValidateResponse(status="success", count=0, posts=[])

    evidence_tool = EvidenceRetrieveTool()
    evidence_payload = json.dumps(
        [p.model_dump(mode="json") for p in civic_posts],
        ensure_ascii=True,
    )
    verified_raw = evidence_tool._run(evidence_payload)
    verified_items = _parse_tool_json(verified_raw)
    if not verified_items:
        return ValidateResponse(status="success", count=0, posts=[])

    verified_posts: list[VerifiedPost] = []
    for item in verified_items:
        verified_posts.append(VerifiedPost(**item))

    await save_verified_posts([p.model_dump() for p in verified_posts])

    counter_posts = await _run_generate(
        VerifyResponse(
            status="manual",
            count=len(verified_posts),
            posts=verified_posts,
        ),
        use_monitor=False,
    )
    return await _run_validate(counter_posts, use_monitor=False)


@app.post("/scrape", response_model=ValidateResponse, tags=["Scraper"])
async def scrape():
    """
    Trigger the TruthMates CrewAI agent to scrape PIB and MyGov RSS feeds.

    Steps:
      1. Kick off the crew with the configured RSS URLs.
      2. Parse the JSON output from the data_cleaner agent.
      3. Persist all posts to MongoDB (upsert by link).
    4. Auto-trigger classification, evidence retrieval, counter-info, and validation.
    5. Return validated outputs.
    """
    try:
        # 1. Run the crew and parse output
        crew_instance = TruthMatesCrew()

        async def _run_scraper():
            result = await _kickoff_with_retry(
                crew_instance.crew(),
                {
                    "pib_url": PIB_RSS_URL,
                    "mygov_url": MYGOV_RSS_URL,
                },
            )
            raw_text: str = result.raw if hasattr(result, "raw") else str(result)
            clean_text = re.sub(r"```(?:json)?\s*", "", raw_text).strip().rstrip("`")
            try:
                data = json.loads(clean_text)
            except json.JSONDecodeError:
                match = re.search(r"\[.*\]", clean_text, re.DOTALL)
                if match:
                    data = json.loads(match.group())
                else:
                    raise HTTPException(
                        status_code=502,
                        detail="Crew returned output that could not be parsed as JSON.",
                    )
            if not isinstance(data, list):
                raise HTTPException(
                    status_code=502,
                    detail="Crew output is not a JSON array.",
                )
            return data

        posts_data = await _run_with_monitor(
            "scraper",
            {"pib_url": PIB_RSS_URL, "mygov_url": MYGOV_RSS_URL},
            _run_scraper,
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


@app.post("/classify", response_model=ValidateResponse, tags=["Classifier"])
async def classify(scrape_response: ScrapeResponse):
    """
    Classify scraper output and persist only civic posts.

    Steps:
      1. Run classifier crew on the scraper posts.
      2. Filter out non-civic posts.
      3. Store civic posts in MongoDB.
    4. Auto-trigger evidence retrieval, counter-info, and validation.
    5. Return validated outputs.
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

        async def _run_classifier():
            result = await _kickoff_with_retry(
                crew_instance.crew(),
                {"posts_json": posts_json},
            )
            raw_text: str = result.raw if hasattr(result, "raw") else str(result)
            clean_text = re.sub(r"```(?:json)?\s*", "", raw_text).strip().rstrip("`")
            try:
                data = json.loads(clean_text)
            except json.JSONDecodeError:
                match = re.search(r"\[.*\]", clean_text, re.DOTALL)
                if match:
                    data = json.loads(match.group())
                else:
                    raise HTTPException(
                        status_code=502,
                        detail="Classifier returned output that could not be parsed as JSON.",
                    )
            if not isinstance(data, list):
                raise HTTPException(
                    status_code=502,
                    detail="Classifier output is not a JSON array.",
                )
            return data

        classified_data = await _run_with_monitor(
            "classifier",
            {"posts_json": posts_json},
            _run_classifier,
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


@app.post("/verify", response_model=ValidateResponse, tags=["Verifier"])
async def verify(classify_response: ClassifyResponse):
    """
    Retrieve evidence for classified civic posts.

    Steps:
      1. Run evidence retriever crew on classified posts.
      2. Label posts as verified/unverified based on matches.
      3. Store verification results in MongoDB.
    4. Auto-trigger counter-info generation and validation.
    5. Return validated outputs.
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

        async def _run_evidence():
            result = await _kickoff_with_retry(
                crew_instance.crew(),
                {"posts_json": posts_json},
            )
            raw_text: str = result.raw if hasattr(result, "raw") else str(result)
            clean_text = re.sub(r"```(?:json)?\s*", "", raw_text).strip().rstrip("`")
            try:
                data = json.loads(clean_text)
            except json.JSONDecodeError:
                match = re.search(r"\[.*\]", clean_text, re.DOTALL)
                if match:
                    data = json.loads(match.group())
                else:
                    raise HTTPException(
                        status_code=502,
                        detail="Verifier returned output that could not be parsed as JSON.",
                    )
            if not isinstance(data, list):
                raise HTTPException(
                    status_code=502,
                    detail="Verifier output is not a JSON array.",
                )
            return data

        verified_data = await _run_with_monitor(
            "evidence",
            {"posts_json": posts_json},
            _run_evidence,
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


async def _run_generate(verify_response: VerifyResponse, use_monitor: bool = True) -> list[CounterInfoPost]:
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

    async def _run_counter_info():
        result = await _kickoff_with_retry(
            crew_instance.crew(),
            {"posts_json": posts_json},
        )
        raw_text: str = result.raw if hasattr(result, "raw") else str(result)
        clean_text = re.sub(r"```(?:json)?\s*", "", raw_text).strip().rstrip("`")
        try:
            data = json.loads(clean_text)
        except json.JSONDecodeError:
            match = re.search(r"\[.*\]", clean_text, re.DOTALL)
            if match:
                data = json.loads(match.group())
            else:
                raise HTTPException(
                    status_code=502,
                    detail="Generator returned output that could not be parsed as JSON.",
                )
        if not isinstance(data, list):
            raise HTTPException(
                status_code=502,
                detail="Generator output is not a JSON array.",
            )
        return data

    if use_monitor:
        correction_data = await _run_with_monitor(
            "counter_info",
            {"posts_json": posts_json},
            _run_counter_info,
        )
    else:
        correction_data = await _run_counter_info()

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
    return counter_posts


class _ValidationItem(BaseModel):
    link: str
    verdict: str
    flags: ValidationFlags


class _ValidationPayload(BaseModel):
    items: list[_ValidationItem]


async def _run_validate(
    counter_posts: list[CounterInfoPost],
    use_monitor: bool = True,
) -> ValidateResponse:
    crew_instance = OutputValidatorCrew()

    payload_items = []
    for post in counter_posts[:_MAX_POSTS_PER_RUN]:
        payload_items.append(post.model_dump(mode="json"))

    posts_json = json.dumps(payload_items, ensure_ascii=True)

    async def _run_validator():
        result = await _kickoff_with_retry(
            crew_instance.crew(),
            {"posts_json": posts_json},
        )
        raw_text: str = result.raw if hasattr(result, "raw") else str(result)
        clean_text = re.sub(r"```(?:json)?\s*", "", raw_text).strip().rstrip("`")

        validated_payload = None
        if hasattr(Guard, "from_pydantic"):
            try:
                guard = Guard.from_pydantic(_ValidationPayload)
                outcome = guard.parse(clean_text)
                validated_payload = outcome.validated_output
            except Exception:
                validated_payload = None

        if validated_payload is None:
            try:
                parsed = _ValidationPayload.model_validate_json(clean_text)
                validated_payload = parsed.model_dump()
            except Exception:
                try:
                    validated_payload = json.loads(clean_text)
                except json.JSONDecodeError as exc:
                    raise HTTPException(
                        status_code=502,
                        detail="Validator returned output that could not be parsed as JSON.",
                    ) from exc

        if isinstance(validated_payload, dict) and "items" in validated_payload:
            return validated_payload
        raise HTTPException(
            status_code=502,
            detail="Validator output is missing items array.",
        )

    if use_monitor:
        validated_payload = await _run_with_monitor(
            "validator",
            {"posts_json": posts_json},
            _run_validator,
        )
    else:
        validated_payload = await _run_validator()

    if hasattr(validated_payload, "model_dump"):
        validated_payload = validated_payload.model_dump()

    if isinstance(validated_payload, dict) and "items" in validated_payload:
        items = validated_payload["items"]
    else:
        items = validated_payload

    flags_by_link: dict[str, ValidationFlags] = {}
    verdict_by_link: dict[str, str] = {}
    for item in items or []:
        try:
            parsed = _ValidationItem(**item)
            flags_by_link[parsed.link] = parsed.flags
            verdict_by_link[parsed.link] = parsed.verdict
        except Exception:
            continue

    validated_posts: list[ValidatedPost] = []
    for post in counter_posts[:_MAX_POSTS_PER_RUN]:
        flags = flags_by_link.get(
            post.link,
            ValidationFlags(
                contradicts_pib_fact=False,
                invalid_source_url=False,
                trust_score_mismatch=False,
                missing_hindi=False,
                hallucinated_stats=False,
            ),
        )
        verdict = verdict_by_link.get(post.link, "UNVERIFIED")
        sources = _sources_from_matches(post.matches)

        validated_posts.append(
            ValidatedPost(
                claim=post.title,
                verdict=verdict,
                trust_score=post.trust_score,
                counter_english=post.correction_en,
                counter_hindi=post.correction_hi,
                sources=sources,
                flags=flags,
            )
        )

    await save_validated_posts([p.model_dump() for p in validated_posts])

    return ValidateResponse(
        status="success",
        count=len(validated_posts),
        posts=validated_posts,
    )


@app.post("/generate", response_model=ValidateResponse, tags=["CounterInfo"])
async def generate(verify_response: VerifyResponse):
    """
    Generate counter-info corrections for verified posts.

    Steps:
      1. Run counter-info crew on verified posts.
      2. Translate corrections to Hindi using IndicTrans2.
      3. Compute trust score and label.
      4. Store counter-info results in MongoDB.
      5. Auto-trigger validation.
    """
    try:
        counter_posts = await _run_generate(verify_response)
        return await validate(GenerateResponse(status="success", count=len(counter_posts), posts=counter_posts))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/validate", response_model=ValidateResponse, tags=["Validator"])
async def validate(generate_response: GenerateResponse):
    """
    Validate counter-info outputs and retry generation if needed.

    Steps:
      1. Run output validator crew.
      2. If any flags triggered, retry counter-info generation (max 2 retries).
      3. Store validated outputs in MongoDB.
    """
    try:
        counter_posts = generate_response.posts

        for attempt in range(_VALIDATION_MAX_RETRIES + 1):
            validation_response = await _run_validate(counter_posts)
            flagged_links = {
                post.claim
                for post in validation_response.posts
                if any(
                    [
                        post.flags.contradicts_pib_fact,
                        post.flags.invalid_source_url,
                        post.flags.trust_score_mismatch,
                        post.flags.missing_hindi,
                        post.flags.hallucinated_stats,
                    ]
                )
            }

            if not flagged_links or attempt >= _VALIDATION_MAX_RETRIES:
                return validation_response

            # Retry counter-info generation for flagged posts only
            retry_posts = [
                post for post in generate_response.posts if post.title in flagged_links
            ]
            verify_payload = VerifyResponse(
                status="retry",
                count=len(retry_posts),
                posts=[
                    VerifiedPost(
                        **p.model_dump(
                            exclude={
                                "correction_en",
                                "correction_hi",
                                "trust_score",
                                "trust_label",
                            }
                        )
                    )
                    for p in retry_posts
                ],
            )
            counter_posts = await _run_generate(verify_payload)

        return validation_response

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
