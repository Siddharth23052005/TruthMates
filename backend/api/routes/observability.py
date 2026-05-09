"""
Observability routes — expose stored pipeline traces.

GET /observability/traces          → last 20 traces
GET /observability/traces/{id}     → single trace detail
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from api.deps import limiter, require_admin_api_key
from core.config import get_settings
from services.observability_service import get_recent_traces, get_trace_by_id


router = APIRouter(
    prefix="/observability",
    tags=["Observability"],
    dependencies=[Depends(require_admin_api_key)],
)


@router.get("/traces")
@limiter.limit(get_settings().admin_rate_limit)
async def list_traces(request: Request):
    """Return the last 20 observability traces, newest first."""
    traces = await get_recent_traces(limit=20)
    return {"status": "success", "count": len(traces), "traces": traces}


@router.get("/traces/{trace_id}")
@limiter.limit(get_settings().admin_rate_limit)
async def get_trace(request: Request, trace_id: str):
    """Return a single observability trace by its UUID."""
    trace = await get_trace_by_id(trace_id)
    if trace is None:
        raise HTTPException(status_code=404, detail=f"Trace '{trace_id}' not found.")
    return {"status": "success", "trace": trace}
