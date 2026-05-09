"""
Observability service for TruthMates.

Logs a structured trace to the 'observability_traces' collection for every
/analyze call.  Each trace captures per-agent spans so callers can inspect
exactly what input/output each stage received, how long it took, and whether
it passed or failed.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from time import perf_counter
from typing import Any

from db.mongo import get_db


# ---------------------------------------------------------------------------
# Trace context — callers build up a trace then flush it.
# ---------------------------------------------------------------------------

class TraceContext:
    """Lightweight mutable holder for a single pipeline trace."""

    def __init__(self, claim: str) -> None:
        self.trace_id: str = str(uuid.uuid4())
        self.claim: str = claim
        self.timestamp: str = datetime.now(timezone.utc).isoformat()
        self._started_at: float = perf_counter()
        self.spans: list[dict] = []
        self.final_verdict: str = ""
        self.trust_score: float = 0.0
        self.flags: dict = {}

    # ------------------------------------------------------------------
    # Span helpers
    # ------------------------------------------------------------------

    def begin_span(self, agent: str, input_data: Any) -> dict:
        """Return a span dict in progress — caller must call end_span."""
        return {
            "agent": agent,
            "input": input_data,
            "output": None,
            "status": "pending",
            "retries": 0,
            "duration_seconds": 0.0,
            "_started_at": perf_counter(),
        }

    def end_span(self, span: dict, output: Any, *, status: str = "pass", retries: int = 0) -> None:
        """Finalise a span and append it to this trace."""
        elapsed = perf_counter() - span.pop("_started_at", perf_counter())
        span.update(
            {
                "output": output,
                "status": status,
                "retries": retries,
                "duration_seconds": round(elapsed, 4),
            }
        )
        self.spans.append(span)

    # ------------------------------------------------------------------
    # Serialise & persist
    # ------------------------------------------------------------------

    def to_document(self) -> dict:
        total = round(perf_counter() - self._started_at, 4)
        return {
            "trace_id": self.trace_id,
            "claim": self.claim,
            "timestamp": self.timestamp,
            "spans": self.spans,
            "total_duration_seconds": total,
            "final_verdict": self.final_verdict,
            "trust_score": self.trust_score,
            "flags": self.flags,
        }


async def flush_trace(ctx: TraceContext) -> None:
    """Persist the completed trace to MongoDB (fire-and-forget safe)."""
    doc = ctx.to_document()
    try:
        collection = get_db()["observability_traces"]
        await collection.insert_one(doc)
    except Exception:
        pass  # Observability must never break the pipeline


# ---------------------------------------------------------------------------
# Query helpers used by the observability routes
# ---------------------------------------------------------------------------

async def get_recent_traces(limit: int = 20) -> list[dict]:
    """Return the last *limit* traces, newest first."""
    collection = get_db()["observability_traces"]
    cursor = collection.find().sort("timestamp", -1).limit(limit)
    docs = [doc async for doc in cursor]
    for doc in docs:
        doc["_id"] = str(doc["_id"])
    return docs


async def get_trace_by_id(trace_id: str) -> dict | None:
    """Return a single trace by its trace_id string."""
    collection = get_db()["observability_traces"]
    doc = await collection.find_one({"trace_id": trace_id})
    if doc:
        doc["_id"] = str(doc["_id"])
    return doc
