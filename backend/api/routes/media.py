from __future__ import annotations

from fastapi import APIRouter, Depends, File, Request, UploadFile
from pydantic import BaseModel

from api.deps import limiter, require_public_api_key
from core.config import get_settings
from services.pipeline_service import analyze_audio_upload, analyze_video_url


class AnalyzeVideoRequest(BaseModel):
    url: str


router = APIRouter(tags=["Media"], dependencies=[Depends(require_public_api_key)])


@router.post("/analyze-video", tags=["Video"])
@limiter.limit(get_settings().public_rate_limit)
async def analyze_video(request: Request, payload: AnalyzeVideoRequest):
    return await analyze_video_url(payload.url, request_id=getattr(request.state, "request_id", None))


@router.post("/analyze-audio", tags=["Audio"])
@limiter.limit(get_settings().public_rate_limit)
async def analyze_audio(request: Request, file: UploadFile = File(...)):
    return await analyze_audio_upload(file, request_id=getattr(request.state, "request_id", None))
