from __future__ import annotations

import asyncio
import re
from fastapi import APIRouter, BackgroundTasks, Depends, Form, Request, Response

from api.deps import limiter, require_public_api_key
from core.config import get_settings
from core.logging import get_logger, log_event
from services.pipeline_service import analyze_claim, analyze_video_url
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse

logger = get_logger("truthmates.whatsapp")

router = APIRouter(tags=["WhatsApp"], dependencies=[Depends(require_public_api_key)])


async def _send_whatsapp_analysis_result(
    recipient_number: str,
    url: str,
    request_id: str | None = None
):
    """
    Background task to analyze a URL and send the result via Twilio REST API.
    This runs asynchronously after the webhook has already responded.
    """
    try:
        logger.info(f"[{request_id}] Starting background URL analysis for: {url}")

        # Perform the analysis
        response = await analyze_video_url(url, request_id=request_id)

        # Validate and extract results
        if not hasattr(response, 'posts') or not response.posts:
            error_msg = "Analysis failed - no results returned"
            logger.error(f"[{request_id}] {error_msg}")
            await _send_whatsapp_message(recipient_number, "Sorry, I couldn't analyze that link. Please try again.", request_id)
            return

        post = response.posts[0]

        # Safely extract fields
        verdict = getattr(post, 'verdict', 'Unable to determine')
        trust_score = getattr(post, 'trust_score', None)
        counter_english = getattr(post, 'counter_english', None)
        sources = getattr(post, 'sources', [])

        # Convert trust_score safely
        try:
            if trust_score is not None:
                trust_score = int(trust_score) if not isinstance(trust_score, int) else trust_score
            else:
                trust_score = 0
        except (ValueError, TypeError):
            trust_score = 0

        # Format sources safely
        try:
            if isinstance(sources, (list, tuple)):
                sources_str = ", ".join(str(s) for s in sources) if sources else "No sources found"
            else:
                sources_str = str(sources) if sources else "No sources found"
        except Exception:
            sources_str = "No sources found"

        # Build final message
        message_parts = [f"Verdict: {verdict}", f"Trust Score: {trust_score}/100"]
        if counter_english and str(counter_english).strip():
            message_parts.append(str(counter_english).strip())
        message_parts.append(f"Source: {sources_str}")

        final_message = "\n".join(message_parts)

        # Truncate if too long
        if len(final_message) > 1600:
            final_message = final_message[:1597] + "..."

        logger.info(f"[{request_id}] Background analysis complete, sending result to {recipient_number}")

        # Send the result via Twilio REST API
        await _send_whatsapp_message(recipient_number, final_message, request_id)

        log_event(
            logger,
            "whatsapp_background_analysis_complete",
            request_id=request_id,
            url=url,
            verdict=verdict,
            trust_score=trust_score,
        )

    except Exception as exc:
        logger.error(f"[{request_id}] Background analysis failed: {type(exc).__name__}: {str(exc)}", exc_info=True)
        try:
            await _send_whatsapp_message(
                recipient_number,
                "Sorry, I couldn't analyze that link. Please try again later.",
                request_id
            )
        except Exception as send_exc:
            logger.error(f"[{request_id}] Failed to send error message: {send_exc}")

        log_event(
            logger,
            "whatsapp_background_analysis_failed",
            level="error",
            request_id=request_id,
            url=url,
            error=str(exc),
        )


async def _send_whatsapp_message(
    to_number: str,
    message: str,
    request_id: str | None = None
):
    """
    Send a WhatsApp message using Twilio REST API.
    """
    try:
        settings = get_settings()
        client = Client(settings.twilio_account_sid, settings.twilio_auth_token)

        # Normalize sender and recipient numbers to a single whatsapp:+<number> format
        def _normalize_whatsapp_number(value: str) -> str:
            normalized = value.strip()
            if normalized.lower().startswith("whatsapp:"):
                normalized = normalized[len("whatsapp:"):]
            normalized = normalized.strip()
            if not normalized.startswith("+"):
                normalized = "+" + normalized
            return f"whatsapp:{normalized}"

        from_number = _normalize_whatsapp_number(settings.twilio_whatsapp_number)
        to_number = _normalize_whatsapp_number(to_number)

        # Send message asynchronously
        message_response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: client.messages.create(
                from_=from_number,
                body=message,
                to=to_number,
            )
        )

        logger.info(f"[{request_id}] WhatsApp message sent successfully. SID: {message_response.sid}")
        return message_response

    except Exception as exc:
        logger.error(f"[{request_id}] Failed to send WhatsApp message: {type(exc).__name__}: {str(exc)}")
        raise


def _extract_url_from_message(message: str) -> str | None:
    """
    Extract the first URL found in the message.
    Detects common URL patterns including YouTube, Instagram, Twitter/X, and news articles.
    Returns the URL if found, None otherwise.
    """
    # Pattern to detect URLs starting with http/https or common shortened forms
    url_pattern = r'https?://(?:www\.)?(?:[a-zA-Z0-9-]+\.)*[a-zA-Z0-9-]+\.[a-zA-Z]{2,}(?:/[^\s]*)?'
    match = re.search(url_pattern, message)
    if match:
        return match.group(0)
    return None


@router.post("/whatsapp/webhook")
@limiter.limit(get_settings().public_rate_limit)
async def whatsapp_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    Body: str = Form(...),
    From: str = Form(...),  # Sender's WhatsApp number
):
    """
    Handle incoming WhatsApp messages via Twilio webhook.
    For URLs: immediately respond with "please wait" and analyze in background.
    For text: analyze immediately and respond.
    Returns verdict analysis to WhatsApp.
    """
    request_id = getattr(request.state, "request_id", None)

    log_event(
        logger,
        "whatsapp_message_received",
        request_id=request_id,
        message_body=Body[:200] + "..." if len(Body) > 200 else Body,
        sender=From,
    )

    # Detect URL in the message
    detected_url = _extract_url_from_message(Body)
    analysis_type = "url" if detected_url else "text"

    # Extract sender's number (remove whatsapp: prefix if present)
    sender_number = From.replace("whatsapp:", "") if From.startswith("whatsapp:") else From

    whatsapp_response = None

    try:
        if detected_url:
            # URL detected - respond immediately and analyze in background
            log_event(
                logger,
                "whatsapp_url_detected",
                request_id=request_id,
                url=detected_url,
            )

            # Start background analysis
            background_tasks.add_task(
                _send_whatsapp_analysis_result,
                sender_number,
                detected_url,
                request_id
            )

            # Immediate response
            whatsapp_response = "🔍 Analyzing your link... please wait for the results!"
            logger.info(f"[{request_id}] Started background URL analysis for: {detected_url}")

        else:
            # Text message - analyze immediately
            logger.info(f"[{request_id}] Starting text analysis for message")
            response = await analyze_claim(Body, request_id=request_id)
            logger.info(f"[{request_id}] Text analysis completed")

            # Validate response structure
            if not hasattr(response, 'posts') or not response.posts:
                error_msg = "Invalid response structure - missing or empty posts"
                logger.error(f"[{request_id}] {error_msg}")
                raise ValueError(error_msg)

            post = response.posts[0]

            # Safely extract fields
            verdict = getattr(post, 'verdict', 'Unable to determine')
            trust_score = getattr(post, 'trust_score', None)
            counter_english = getattr(post, 'counter_english', None)
            sources = getattr(post, 'sources', [])

            # Convert trust_score safely
            try:
                if trust_score is not None:
                    trust_score = int(trust_score) if not isinstance(trust_score, int) else trust_score
                else:
                    trust_score = 0
            except (ValueError, TypeError):
                trust_score = 0

            # Format sources safely
            try:
                if isinstance(sources, (list, tuple)):
                    sources_str = ", ".join(str(s) for s in sources) if sources else "No sources found"
                else:
                    sources_str = str(sources) if sources else "No sources found"
            except Exception:
                sources_str = "No sources found"

            # Build WhatsApp response message
            message_parts = [f"Verdict: {verdict}", f"Trust Score: {trust_score}/100"]
            if counter_english and str(counter_english).strip():
                message_parts.append(str(counter_english).strip())
            message_parts.append(f"Source: {sources_str}")

            whatsapp_response = "\n".join(message_parts)

            # Truncate if too long for WhatsApp (1600 char limit)
            if len(whatsapp_response) > 1600:
                logger.warning(f"[{request_id}] Message too long ({len(whatsapp_response)} chars), truncating")
                whatsapp_response = whatsapp_response[:1597] + "..."

            logger.info(f"[{request_id}] Text analysis response ({len(whatsapp_response)} chars): {whatsapp_response[:150]}...")

            log_event(
                logger,
                "whatsapp_analysis_complete",
                request_id=request_id,
                analysis_type=analysis_type,
                verdict=verdict,
                trust_score=trust_score,
            )

    except Exception as exc:
        logger.error(f"[{request_id}] Analysis failed: {type(exc).__name__}: {str(exc)}", exc_info=True)
        log_event(
            logger,
            "whatsapp_analysis_failed",
            level="error",
            request_id=request_id,
            analysis_type=analysis_type,
            error=str(exc),
        )
        whatsapp_response = "TruthMates AI is temporarily unavailable. Please try again later."

    # Ensure we always have a response to send
    if whatsapp_response is None:
        whatsapp_response = "TruthMates AI is temporarily unavailable. Please try again later."

    # Return Twilio MessagingResponse as XML
    try:
        logger.info(f"[{request_id}] Creating TwiML response: {whatsapp_response[:100]}...")

        resp = MessagingResponse()
        resp.message(whatsapp_response)
        xml_response = str(resp)

        # Validate XML
        if '<Message>' not in xml_response or '</Message>' not in xml_response:
            logger.error(f"[{request_id}] Invalid TwiML generated")
            raise ValueError("Generated TwiML is invalid")

        logger.info(f"[{request_id}] TwiML response created ({len(xml_response)} bytes)")
        return Response(content=xml_response, media_type="application/xml")

    except Exception as exc:
        logger.error(f"[{request_id}] TwiML creation failed: {type(exc).__name__}: {str(exc)}", exc_info=True)
        # Fallback XML
        fallback_xml = '<?xml version="1.0" encoding="UTF-8"?><Response><Message>TruthMates AI is temporarily unavailable. Please try again later.</Message></Response>'
        return Response(content=fallback_xml, media_type="application/xml")