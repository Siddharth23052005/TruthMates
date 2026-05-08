from __future__ import annotations

from fastapi import APIRouter, Request

from services.pipeline_service import health_check_payload


router = APIRouter(tags=["Health"])


@router.get("/")
async def health_check(request: Request):
    return await health_check_payload(request_id=getattr(request.state, "request_id", None))
