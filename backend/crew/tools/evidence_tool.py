"""
EvidenceRetrieveTool — CrewAI tool for evidence retrieval using Pinecone
and Google Fact Check API.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Type

import requests
from crewai.tools import BaseTool
from pinecone import Pinecone, ServerlessSpec
from pydantic import BaseModel, Field
from sentence_transformers import SentenceTransformer


# ── Constants ───────────────────────────────────────────────────────────────

_INDEX_NAME = "truthmates-facts"
_NAMESPACE = "facts"
_EMBED_MODEL = "all-MiniLM-L6-v2"
_TOP_K = 3
_MATCH_THRESHOLD = 0.5

_FACTS_PATH = Path(__file__).resolve().parents[1] / "data" / "verified_facts.json"


# ── Input schema ────────────────────────────────────────────────────────────

class EvidenceRetrieveInput(BaseModel):
    """Input schema for EvidenceRetrieveTool."""

    posts_json: str = Field(
        ...,
        description=(
            "JSON string containing a list of classified civic posts with fields: "
            "title, description, link, pub_date, source, label, confidence, language."
        ),
    )


# ── Tool implementation ─────────────────────────────────────────────────────

class EvidenceRetrieveTool(BaseTool):
    """
    Retrieves evidence for classified civic posts.

    Adds: matches, verification_label.
    """

    name: str = "EvidenceRetrieveTool"
    description: str = (
        "Retrieves evidence from Pinecone facts index and Google Fact Check API. "
        "Input: JSON list of classified posts. Output: JSON list with matches "
        "and verification_label."
    )
    args_schema: Type[BaseModel] = EvidenceRetrieveInput

    def _run(self, posts_json: str) -> str:
        posts = _safe_parse(posts_json)
        if not isinstance(posts, list):
            return json.dumps([], ensure_ascii=True)

        index = _get_pinecone_index()
        _ensure_indexed_facts(index)

        results: list[dict] = []
        for post in posts:
            if post.get("label") != "civic":
                continue

            claim_text = _normalize_text(
                f"{post.get('title', '')}. {post.get('description', '')}"
            )
            if not claim_text:
                continue

            print(
                "[EvidenceRetrieveTool] Pinecone query text:",
                claim_text[:500],
            )

            claim_vector = _embed_text(claim_text)

            matches = []
            matches.extend(_search_pinecone(index, claim_vector))
            matches.extend(_search_google_factcheck(claim_text, claim_vector))

            matches = [m for m in matches if m["similarity"] >= _MATCH_THRESHOLD]
            matches = sorted(matches, key=lambda m: m["similarity"], reverse=True)

            verification_label = "verified" if matches else "unverified"

            results.append(
                {
                    **post,
                    "verification_label": verification_label,
                    "matches": matches,
                }
            )

        return json.dumps(results, ensure_ascii=True, indent=2)


# ── Helpers ─────────────────────────────────────────────────────────────────

_embedder: SentenceTransformer | None = None
_pinecone_client: Pinecone | None = None
_pinecone_index = None


def _safe_parse(text: str) -> list:
    text = re.sub(r"```(?:json)?\s*", "", text).strip()
    text = text.rstrip("`").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return []


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _get_embedder() -> SentenceTransformer:
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer(_EMBED_MODEL)
    return _embedder


def _embed_text(text: str):
    embedder = _get_embedder()
    vector = embedder.encode([text], normalize_embeddings=True)[0]
    return vector


def _get_pinecone_index():
    global _pinecone_client, _pinecone_index

    if _pinecone_index is not None:
        return _pinecone_index

    api_key = os.environ.get("PINECONE_API_KEY")
    if not api_key:
        raise EnvironmentError("PINECONE_API_KEY is not set.")

    cloud = os.environ.get("PINECONE_CLOUD", "aws")
    region = os.environ.get("PINECONE_REGION", "us-east-1")

    _pinecone_client = Pinecone(api_key=api_key)
    index_names = _list_index_names(_pinecone_client)
    if _INDEX_NAME not in index_names:
        _pinecone_client.create_index(
            name=_INDEX_NAME,
            dimension=384,
            metric="cosine",
            spec=ServerlessSpec(cloud=cloud, region=region),
        )

    _pinecone_index = _pinecone_client.Index(_INDEX_NAME)
    return _pinecone_index


def _list_index_names(client: Pinecone) -> list[str]:
    indexes = client.list_indexes()
    if hasattr(indexes, "names"):
        return list(indexes.names())
    return [index["name"] for index in indexes]


def _ensure_indexed_facts(index) -> None:
    facts = _load_facts()
    if not facts:
        return

    stats = _describe_index(index)
    total_vectors = _extract_total_vectors(stats)
    namespace_vectors = _extract_namespace_vectors(stats, _NAMESPACE)
    print(
        f"[EvidenceRetrieveTool] Pinecone stats: total_vectors={total_vectors}, "
        f"namespace_vectors={namespace_vectors}"
    )

    texts = [fact["text"] for fact in facts]
    vectors = _get_embedder().encode(texts, normalize_embeddings=True)

    to_upsert = []
    for fact, vector in zip(facts, vectors, strict=False):
        metadata = {
            "text": fact["text"],
            "source_url": fact.get("source_url", ""),
            "source_tag": fact.get("source_tag", ""),
        }
        to_upsert.append((fact["id"], vector.tolist(), metadata))

    if to_upsert:
        if total_vectors == 0 or namespace_vectors == 0:
            print("[EvidenceRetrieveTool] Index empty. Re-indexing facts...")
        index.upsert(vectors=to_upsert, namespace=_NAMESPACE)


def _load_facts() -> list[dict]:
    if not _FACTS_PATH.exists():
        return []

    try:
        with _FACTS_PATH.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return []


def _search_pinecone(index, claim_vector) -> list[dict]:
    query = index.query(
        vector=claim_vector.tolist(),
        top_k=_TOP_K,
        include_metadata=True,
        namespace=_NAMESPACE,
    )

    print(
        "[EvidenceRetrieveTool] Pinecone similarity scores:",
        [round(float(m.get("score") or 0.0), 4) for m in query.get("matches", []) or []],
    )

    matches: list[dict] = []
    for match in query.get("matches", []) or []:
        metadata = match.get("metadata") or {}
        score = match.get("score") or 0.0
        similarity = max(0.0, min(1.0, float(score)))

        matches.append(
            {
                "fact_text": metadata.get("text", ""),
                "similarity": round(similarity, 4),
                "source_url": metadata.get("source_url", ""),
                "source_type": "pinecone",
            }
        )

    return matches


def _describe_index(index) -> dict:
    try:
        return index.describe_index_stats()
    except Exception as exc:
        print(f"[EvidenceRetrieveTool] Failed to describe index stats: {exc}")
        return {}


def _extract_total_vectors(stats: dict) -> int:
    try:
        return int(stats.get("total_vector_count") or 0)
    except Exception:
        return 0


def _extract_namespace_vectors(stats: dict, namespace: str) -> int:
    try:
        namespaces = stats.get("namespaces") or {}
        namespace_entry = namespaces.get(namespace) or {}
        return int(namespace_entry.get("vector_count") or 0)
    except Exception:
        return 0


def _search_google_factcheck(claim_text: str, claim_vector) -> list[dict]:
    api_key = os.environ.get("GOOGLE_FACT_CHECK_API_KEY")
    if not api_key:
        return []

    try:
        response = requests.get(
            "https://factchecktools.googleapis.com/v1alpha1/claims:search",
            params={
                "query": claim_text,
                "key": api_key,
                "pageSize": 3,
            },
            timeout=20,
        )
        response.raise_for_status()
    except requests.RequestException:
        return []

    data = response.json() or {}
    claims = data.get("claims") or []

    if not claims:
        return []

    texts = []
    urls = []
    for claim in claims:
        claim_text_value = (claim.get("text") or "").strip()
        if not claim_text_value:
            continue

        claim_reviews = claim.get("claimReview") or []
        url = ""
        if claim_reviews:
            url = (claim_reviews[0].get("url") or "").strip()

        texts.append(claim_text_value)
        urls.append(url)

    if not texts:
        return []

    vectors = _get_embedder().encode(texts, normalize_embeddings=True)

    matches: list[dict] = []
    for text, url, vector in zip(texts, urls, vectors, strict=False):
        similarity = float(_cosine_similarity(claim_vector, vector))
        similarity = max(0.0, min(1.0, similarity))

        matches.append(
            {
                "fact_text": text,
                "similarity": round(similarity, 4),
                "source_url": url,
                "source_type": "google_fact_check",
            }
        )

    return matches


def _cosine_similarity(vec_a, vec_b) -> float:
    dot = float((vec_a * vec_b).sum())
    norm = (float((vec_a * vec_a).sum()) ** 0.5) * (float((vec_b * vec_b).sum()) ** 0.5)
    if norm == 0.0:
        return 0.0
    return dot / norm
