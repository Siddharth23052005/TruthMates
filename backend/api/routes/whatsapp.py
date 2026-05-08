from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request

from api.deps import limiter, require_public_api_key
from core.config import get_settings
from core.logging import get_logger, log_event
from services.pipeline_service import analyze_claim
from twilio.twiml.messaging_response import MessagingResponse

logger = get_logger("truthmates.whatsapp")

router = APIRouter(tags=["WhatsApp"], dependencies=[Depends(require_public_api_key)])


@router.post("/whatsapp/webhook")
@limiter.limit(get_settings().public_rate_limit)
async def whatsapp_webhook(
    request: Request,
    Body: str = Form(...),
):
    """
    Handle incoming WhatsApp messages via Twilio webhook.
    Extract message body, analyze claim, and respond with verdict.
    """
    request_id = getattr(request.state, "request_id", None)

    log_event(
        logger,
        "whatsapp_message_received",
        request_id=request_id,
        message_body=Body[:200] + "..." if len(Body) > 200 else Body,
    )

    # Analyze the claim using existing pipeline
    try:
        response = await analyze_claim(Body, request_id=request_id)
        if not response.posts:
            raise ValueError("No analysis result returned")

        post = response.posts[0]

        # Format response as specified
        verdict = post.verdict
        trust_score = int(post.trust_score)
        counter_english = post.counter_english
        sources = ", ".join(post.sources) if post.sources else "No sources found"

        whatsapp_response = f"Verdict: {verdict}\nTrust Score: {trust_score}/100\n{counter_english}\nSource: {sources}"

        log_event(
            logger,
            "whatsapp_analysis_complete",
            request_id=request_id,
            verdict=verdict,
            trust_score=trust_score,
        )

    except Exception as exc:
        log_event(
            logger,
            "whatsapp_analysis_failed",
            level="error",
            request_id=request_id,
            error=str(exc),
        )
        whatsapp_response = "Sorry, I couldn't analyze that message. Please try again."

    # Return Twilio MessagingResponse
    resp = MessagingResponse()
    resp.message(whatsapp_response)
    return str(resp)