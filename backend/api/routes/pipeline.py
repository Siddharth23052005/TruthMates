from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from api.deps import limiter, require_admin_api_key, require_public_api_key
from core.config import get_settings
from models.schemas import ClassifyResponse, GenerateResponse, ScrapeResponse, VerifyResponse
from pydantic import BaseModel
from services.pipeline_service import (
    analyze_claim,
    classify_pipeline,
    generate_pipeline,
    scrape_pipeline,
    validate_pipeline,
    verify_pipeline,
)


class AnalyzeRequest(BaseModel):
    claim: str


router = APIRouter()


@router.post("/analyze", tags=["Analyzer"], dependencies=[Depends(require_public_api_key)])
@router.post("/api/analyze", tags=["Analyzer"], dependencies=[Depends(require_public_api_key)])
@limiter.limit(get_settings().public_rate_limit)
async def analyze(request: Request, payload: AnalyzeRequest):
    return await analyze_claim(payload.claim, request_id=getattr(request.state, "request_id", None))


@router.post("/scrape", tags=["Scraper"], dependencies=[Depends(require_admin_api_key)])
@limiter.limit(get_settings().admin_rate_limit)
async def scrape(request: Request):
    return await scrape_pipeline(request_id=getattr(request.state, "request_id", None))


@router.post("/classify", tags=["Classifier"], dependencies=[Depends(require_admin_api_key)])
@limiter.limit(get_settings().admin_rate_limit)
async def classify(request: Request, scrape_response: ScrapeResponse):
    return await classify_pipeline(scrape_response, request_id=getattr(request.state, "request_id", None))


@router.post("/verify", tags=["Verifier"], dependencies=[Depends(require_admin_api_key)])
@limiter.limit(get_settings().admin_rate_limit)
async def verify(request: Request, classify_response: ClassifyResponse):
    return await verify_pipeline(classify_response, request_id=getattr(request.state, "request_id", None))


@router.post("/generate", tags=["CounterInfo"], dependencies=[Depends(require_admin_api_key)])
@limiter.limit(get_settings().admin_rate_limit)
async def generate(request: Request, verify_response: VerifyResponse):
    return await generate_pipeline(verify_response, request_id=getattr(request.state, "request_id", None))


@router.post("/validate", tags=["Validator"], dependencies=[Depends(require_admin_api_key)])
@limiter.limit(get_settings().admin_rate_limit)
async def validate(request: Request, generate_response: GenerateResponse):
    return await validate_pipeline(generate_response, request_id=getattr(request.state, "request_id", None))
