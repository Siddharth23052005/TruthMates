"""
Video Analysis Crew — CrewAI agents for claim extraction and fact-checking
==========================================================================
Agent 1 (Video Analyst): Summarizes transcript, extracts civic claims.
Agent 2 (Fact Checker): Verifies claims against Pinecone + Google Fact Check.

All agent outputs are Pydantic-validated. Parse failures trigger one
retry with a stricter prompt before raising an error.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Type

import requests
from crewai import Agent, Crew, Process, Task, LLM
from crewai.tools import BaseTool
from dotenv import load_dotenv
from pinecone import Pinecone
from pydantic import BaseModel, Field
# sentence_transformers imported lazily in _get_embedder() to avoid protobuf conflict
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from video.schemas import (
    ExtractedClaim,
    FactCheckMatch,
    VerifiedClaim,
    VideoAnalysisOutput,
)

load_dotenv()

# ── Configuration ────────────────────────────────────────────────────────────

_CONFIG_DIR = Path(__file__).parent / "config"
_EMBED_MODEL = "all-MiniLM-L6-v2"
_TOP_K = 3
_SIMILARITY_FLOOR = 0.70
_PINECONE_NAMESPACE = "facts"


def _get_pinecone_index_name() -> str:
    return os.environ.get("PINECONE_INDEX_NAME", "truthmates-facts")


# ── Shared Helpers ───────────────────────────────────────────────────────────

_embedder = None


def _get_embedder():
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer
        _embedder = SentenceTransformer(_EMBED_MODEL)
    return _embedder


def _embed_text(text: str):
    embedder = _get_embedder()
    return embedder.encode([text], normalize_embeddings=True)[0]


def _cosine_similarity(vec_a, vec_b) -> float:
    dot = float((vec_a * vec_b).sum())
    norm = (float((vec_a * vec_a).sum()) ** 0.5) * (
        float((vec_b * vec_b).sum()) ** 0.5
    )
    if norm == 0.0:
        return 0.0
    return dot / norm


def _strip_markdown_json(text: str) -> str:
    """Strip markdown code fences and extra whitespace from LLM output."""
    text = re.sub(r"```(?:json)?\s*", "", text).strip()
    text = text.rstrip("`").strip()
    return text


def _is_rate_limit_error(exc: Exception) -> bool:
    return "rate_limit" in str(exc).lower() or "rate limit" in str(exc).lower()


# ── Evidence Retrieval Tool ──────────────────────────────────────────────────


class EvidenceInput(BaseModel):
    claims_json: str = Field(
        ...,
        description="JSON array of claim objects with title, description, label fields.",
    )


class EvidenceRetrieveToolForVideo(BaseTool):
    """
    Retrieves evidence from Pinecone and Google Fact Check API.
    Reuses the same Pinecone index and embedding model as the main app.
    """

    name: str = "EvidenceRetrieveTool"
    description: str = (
        "Retrieves evidence from Pinecone facts index and Google Fact Check API. "
        "Input: JSON array of claim objects. Output: JSON array with matches."
    )
    args_schema: Type[BaseModel] = EvidenceInput

    def _run(self, claims_json: str) -> str:
        claims = _safe_parse(claims_json)
        if not isinstance(claims, list):
            return json.dumps([], ensure_ascii=True)

        index = _get_pinecone_index()

        results: list[dict] = []
        for claim in claims:
            claim_text = (
                f"{claim.get('title', '')}. {claim.get('description', '')}"
            ).strip()
            if not claim_text:
                continue

            claim_vector = _embed_text(claim_text)

            matches = []
            # Pinecone search
            matches.extend(_search_pinecone(index, claim_vector))
            # Google Fact Check search
            gfc_matches, gfc_error = _search_google_factcheck(
                claim_text, claim_vector
            )
            matches.extend(gfc_matches)

            # Apply similarity floor
            matches = [m for m in matches if m["similarity"] >= _SIMILARITY_FLOOR]
            matches.sort(key=lambda m: m["similarity"], reverse=True)

            if gfc_error and not matches:
                verification_label = "source_unavailable"
            elif matches:
                verification_label = "verified"
            else:
                verification_label = "unverified"

            results.append(
                {
                    **claim,
                    "verification_label": verification_label,
                    "matches": matches,
                }
            )

        return json.dumps(results, ensure_ascii=True, indent=2)


def _safe_parse(text: str) -> list:
    text = _strip_markdown_json(text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return []


_pinecone_index = None


def _get_pinecone_index():
    global _pinecone_index
    if _pinecone_index is not None:
        return _pinecone_index

    api_key = os.environ.get("PINECONE_API_KEY")
    if not api_key:
        raise EnvironmentError("PINECONE_API_KEY is not set.")

    index_name = _get_pinecone_index_name()
    client = Pinecone(api_key=api_key)

    # Validate index exists
    try:
        index_list = client.list_indexes()
        names = (
            list(index_list.names())
            if hasattr(index_list, "names")
            else [idx["name"] for idx in index_list]
        )
    except Exception:
        names = []

    if index_name not in names:
        raise RuntimeError(
            f"Pinecone index '{index_name}' not found. "
            f"Available indexes: {names}"
        )

    _pinecone_index = client.Index(index_name)
    return _pinecone_index


def _search_pinecone(index, claim_vector) -> list[dict]:
    try:
        query = index.query(
            vector=claim_vector.tolist(),
            top_k=_TOP_K,
            include_metadata=True,
            namespace=_PINECONE_NAMESPACE,
        )
    except Exception:
        return []

    matches: list[dict] = []
    for match in query.get("matches", []) or []:
        metadata = match.get("metadata") or {}
        score = max(0.0, min(1.0, float(match.get("score", 0.0))))
        matches.append(
            {
                "fact_text": metadata.get("text", ""),
                "similarity": round(score, 4),
                "source_url": metadata.get("source_url", ""),
                "source_type": "pinecone",
            }
        )
    return matches


def _search_google_factcheck(
    claim_text: str, claim_vector
) -> tuple[list[dict], str | None]:
    """
    Search Google Fact Check API.
    Returns (matches, error_message_or_None).
    Distinguishes API errors from empty results.
    """
    api_key = os.environ.get("GOOGLE_FACT_CHECK_API_KEY")
    if not api_key:
        return [], "GOOGLE_FACT_CHECK_API_KEY not set"

    try:
        response = requests.get(
            "https://factchecktools.googleapis.com/v1alpha1/claims:search",
            params={"query": claim_text, "key": api_key, "pageSize": 3},
            timeout=20,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        status = getattr(exc.response, "status_code", None) if hasattr(exc, "response") else None
        return [], f"Google Fact Check API error: {status or str(exc)}"

    data = response.json() or {}
    claims = data.get("claims") or []
    if not claims:
        return [], None  # Empty result, not an error

    texts, urls = [], []
    for claim in claims:
        text = (claim.get("text") or "").strip()
        if not text:
            continue
        reviews = claim.get("claimReview") or []
        url = (reviews[0].get("url", "") if reviews else "").strip()
        texts.append(text)
        urls.append(url)

    if not texts:
        return [], None

    vectors = _get_embedder().encode(texts, normalize_embeddings=True)
    matches: list[dict] = []
    for text, url, vector in zip(texts, urls, vectors, strict=False):
        similarity = max(0.0, min(1.0, float(_cosine_similarity(claim_vector, vector))))
        matches.append(
            {
                "fact_text": text,
                "similarity": round(similarity, 4),
                "source_url": url,
                "source_type": "google_fact_check",
            }
        )
    return matches, None


# ── LLM Output Parsing & Validation ─────────────────────────────────────────


def _parse_and_validate_agent_output(
    raw_text: str,
    model_class: type[BaseModel],
    is_list: bool = False,
) -> BaseModel | list[BaseModel]:
    """
    Parse LLM output as JSON, validate against Pydantic model.
    Raises ValueError with details if parsing or validation fails.
    """
    clean = _strip_markdown_json(raw_text)

    # Try direct parse
    try:
        data = json.loads(clean)
    except json.JSONDecodeError:
        # Fallback: find JSON in the text
        if is_list:
            match = re.search(r"\[.*\]", clean, re.DOTALL)
        else:
            match = re.search(r"\{.*\}", clean, re.DOTALL)
        if match:
            data = json.loads(match.group())
        else:
            raise ValueError(f"Could not extract JSON from agent output: {clean[:200]}...")

    # Validate
    if is_list:
        if not isinstance(data, list):
            raise ValueError(f"Expected JSON array, got {type(data).__name__}")
        return [model_class(**item) for item in data]
    else:
        return model_class(**data)


# ── Crew Assembly ────────────────────────────────────────────────────────────


def _get_llm() -> LLM:
    return LLM(
        model="groq/llama-3.1-8b-instant",
        api_key=os.environ["GROQ_API_KEY"],
        temperature=0.0,
    )


def run_video_analysis_crew(
    transcript: str,
) -> tuple[VideoAnalysisOutput, list[VerifiedClaim]]:
    """
    Run the two-agent crew:
      Agent 1: Analyze transcript → VideoAnalysisOutput
      Agent 2: Fact-check claims → list[VerifiedClaim]

    Returns (analysis_output, verified_claims).
    Retries each agent once on parse failure with a stricter prompt.
    """

    # ── Load YAML configs ────────────────────────────────────────────────
    import yaml

    agents_path = _CONFIG_DIR / "agents.yaml"
    tasks_path = _CONFIG_DIR / "tasks.yaml"

    with open(agents_path, "r", encoding="utf-8") as f:
        agents_config = yaml.safe_load(f)
    with open(tasks_path, "r", encoding="utf-8") as f:
        tasks_config = yaml.safe_load(f)

    llm = _get_llm()

    # ── Agent 1: Video Analyst ───────────────────────────────────────────

    analyst_agent = Agent(
        **agents_config["video_analyst"],
        llm=llm,
        tools=[],
    )

    analyst_task = Task(
        description=tasks_config["analyze_video_task"]["description"].format(
            transcript=transcript[:3000]  # Truncate for token limits
        ),
        expected_output=tasks_config["analyze_video_task"]["expected_output"],
        agent=analyst_agent,
    )

    analyst_crew = Crew(
        agents=[analyst_agent],
        tasks=[analyst_task],
        process=Process.sequential,
        verbose=True,
    )

    # Run Agent 1 with retry on parse failure
    analysis_output = _run_agent_with_validation(
        crew=analyst_crew,
        model_class=VideoAnalysisOutput,
        is_list=False,
        agent=analyst_agent,
        original_description=analyst_task.description,
    )

    # ── Agent 2: Fact Checker ────────────────────────────────────────────

    claims_for_tool = []
    for claim in analysis_output.claims:
        claims_for_tool.append(
            {
                "title": claim.claim_text,
                "description": claim.misleading_aspect,
                "label": "civic",
                "link": "",
            }
        )
    claims_json = json.dumps(claims_for_tool, ensure_ascii=True)

    checker_agent = Agent(
        **agents_config["fact_checker"],
        llm=llm,
        tools=[EvidenceRetrieveToolForVideo()],
    )

    checker_task = Task(
        description=tasks_config["fact_check_task"]["description"].format(
            claims_json=claims_json
        ),
        expected_output=tasks_config["fact_check_task"]["expected_output"],
        agent=checker_agent,
    )

    checker_crew = Crew(
        agents=[checker_agent],
        tasks=[checker_task],
        process=Process.sequential,
        verbose=True,
    )

    # Run Agent 2 with retry on parse failure
    verified_claims = _run_agent_with_validation(
        crew=checker_crew,
        model_class=VerifiedClaim,
        is_list=True,
        agent=checker_agent,
        original_description=checker_task.description,
    )

    return analysis_output, verified_claims


def _run_agent_with_validation(
    crew: Crew,
    model_class: type[BaseModel],
    is_list: bool,
    agent: Agent,
    original_description: str,
    max_retries: int = 1,
):
    """
    Run a crew and validate the output. On parse failure, retry once
    with a stricter prompt demanding exact JSON schema compliance.
    """
    for attempt in range(max_retries + 1):
        result = crew.kickoff()
        raw_text = result.raw if hasattr(result, "raw") else str(result)

        try:
            validated = _parse_and_validate_agent_output(
                raw_text, model_class, is_list=is_list
            )
            return validated
        except (ValueError, json.JSONDecodeError, Exception) as exc:
            if attempt < max_retries:
                # Retry with stricter prompt
                schema_hint = json.dumps(
                    model_class.model_json_schema(), indent=2
                )
                strict_suffix = (
                    f"\n\nPREVIOUS ATTEMPT FAILED VALIDATION: {exc}\n"
                    f"You MUST return valid JSON matching this exact schema:\n"
                    f"{schema_hint}\n"
                    f"No markdown fences. No commentary. ONLY the JSON."
                )
                # Rebuild the crew with stricter task
                strict_task = Task(
                    description=original_description + strict_suffix,
                    expected_output=f"Valid JSON matching schema: {model_class.__name__}",
                    agent=agent,
                )
                crew = Crew(
                    agents=[agent],
                    tasks=[strict_task],
                    process=Process.sequential,
                    verbose=True,
                )
                continue
            raise RuntimeError(
                f"Agent output failed validation after {max_retries + 1} attempts: {exc}"
            )
