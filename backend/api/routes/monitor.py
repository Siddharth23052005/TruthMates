from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request

from api.deps import limiter, require_admin_api_key
from core.config import get_settings
from db.mongo import get_db
from services.pipeline_service import monitor_logs_payload, monitor_status_payload, monitor_summary_payload


router = APIRouter(prefix="/monitor", tags=["Monitor"], dependencies=[Depends(require_admin_api_key)])


@router.get("/logs")
@limiter.limit(get_settings().admin_rate_limit)
async def monitor_logs(request: Request):
    return await monitor_logs_payload(request_id=getattr(request.state, "request_id", None))


@router.get("/status")
@limiter.limit(get_settings().admin_rate_limit)
async def monitor_status(request: Request):
    return await monitor_status_payload(request_id=getattr(request.state, "request_id", None))


@router.get("/summary")
@limiter.limit(get_settings().admin_rate_limit)
async def monitor_summary(request: Request):
    return await monitor_summary_payload(request_id=getattr(request.state, "request_id", None))


@router.get("/dashboard")
@limiter.limit(get_settings().admin_rate_limit)
async def monitor_dashboard(request: Request):
    """
    Aggregate pipeline health, per-agent stats and verdict distribution.
    Pulls exclusively from existing agent_monitor_logs and civic_validated.
    """
    db = get_db()

    # ── Agent stats from agent_monitor_logs ──────────────────────────────────
    logs_cursor = db["agent_monitor_logs"].find()
    logs: list[dict] = [doc async for doc in logs_cursor]

    agent_map: dict[str, dict] = {}
    for log in logs:
        name = (log.get("agent_name") or "unknown").strip()
        if name not in agent_map:
            agent_map[name] = {
                "name": name,
                "total_runs": 0,
                "passed": 0,
                "failed": 0,
                "retries": 0,
                "last_run": None,
                "_durations": [],
            }
        entry = agent_map[name]
        entry["total_runs"] += 1
        status = (log.get("status") or "").upper()
        if status == "PASS":
            entry["passed"] += 1
        else:
            entry["failed"] += 1
        entry["retries"] += int(log.get("retries") or 0)
        ts = log.get("timestamp")
        if ts:
            ts_str = ts if isinstance(ts, str) else ts.isoformat()
            if entry["last_run"] is None or ts_str > entry["last_run"]:
                entry["last_run"] = ts_str
        # accumulate duration if stored
        dur = log.get("duration_seconds")
        if dur is not None:
            try:
                entry["_durations"].append(float(dur))
            except (TypeError, ValueError):
                pass

    agents_out = []
    for entry in agent_map.values():
        durs = entry.pop("_durations", [])
        avg_dur = round(sum(durs) / len(durs), 3) if durs else None
        agents_out.append({**entry, "avg_pipeline_seconds": avg_dur})

    # ── Pipeline health (pass-rate based) ───────────────────────────────────
    # healthy  → every agent has pass rate >= 60 %
    # degraded → any agent has pass rate 30–59 %
    # down     → any agent has pass rate < 30 %
    # no data  → down
    def _pass_rate(a: dict) -> float:
        if not a["total_runs"]:
            return 0.0
        return a["passed"] / a["total_runs"] * 100

    if not agents_out:
        pipeline_health = "down"
    elif any(_pass_rate(a) < 30 for a in agents_out):
        pipeline_health = "down"
    elif any(_pass_rate(a) < 60 for a in agents_out):
        pipeline_health = "degraded"
    else:
        pipeline_health = "healthy"

    # ── Verdict counts from civic_validated ───────────────────────────────────
    validated_cursor = db["civic_validated"].find({}, {"verdict": 1, "_id": 0})
    total_claims = 0
    verdicts: dict[str, int] = {"SUPPORTED": 0, "REFUTED": 0, "MISLEADING": 0, "UNVERIFIED": 0}
    async for doc in validated_cursor:
        total_claims += 1
        v = (doc.get("verdict") or "").upper()
        if v in verdicts:
            verdicts[v] += 1

    return {
        "agents": agents_out,
        "pipeline_health": pipeline_health,
        "total_claims_analyzed": total_claims,
        "verdicts": verdicts,
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/reset")
@limiter.limit(get_settings().admin_rate_limit)
async def monitor_reset(request: Request):
    """
    Clear agent_monitor_logs for a fresh stats baseline.
    Admin-only — protected by require_admin_api_key on the router.
    """
    db = get_db()
    result = await db["agent_monitor_logs"].delete_many({})
    return {
        "status": "reset",
        "deleted": result.deleted_count,
        "message": f"Cleared {result.deleted_count} log entries from agent_monitor_logs.",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
