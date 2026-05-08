from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from api.deps import limiter, require_admin_api_key
from core.config import get_settings
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
