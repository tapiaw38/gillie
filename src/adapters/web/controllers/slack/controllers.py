import json
import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, PlainTextResponse

from src.adapters.web.integrations.slack.slack import SlackIntegration
from src.adapters.web.dependencies import get_usecases

router = APIRouter(prefix="/api/slack", tags=["Slack"])


@router.get("/verify", response_class=PlainTextResponse)
async def verify_endpoint():
    """Simple health-check endpoint for the Slack webhook server."""
    logger = logging.getLogger(__name__)
    logger.info("Slack verification request received")
    return "Slack webhook server is running"


@router.post("/events")
async def slack_events(request: Request):
    """
    Slack Events API webhook endpoint.

    Handles:
    - URL verification challenges (type=url_verification)
    - Inbound message events (type=event_callback, event.type=message)

    Always returns HTTP 200 so Slack does not retry unnecessarily.
    Slack retries (X-Slack-Retry-Num > 0) are acknowledged immediately
    without re-processing to avoid duplicate AI responses.
    """
    logger = logging.getLogger(__name__)

    # Acknowledge Slack retries immediately to prevent duplicate processing
    retry_num_header = request.headers.get("X-Slack-Retry-Num")
    if retry_num_header is not None:
        try:
            if int(retry_num_header) > 0:
                logger.info(
                    f"Slack retry attempt {retry_num_header} received; acknowledging without processing"
                )
                return JSONResponse(status_code=200, content={"status": "ok"})
        except ValueError:
            pass

    raw_body = await request.body()

    try:
        payload = json.loads(raw_body)
    except Exception as e:
        logger.error(f"Failed to parse Slack event body: {str(e)}")
        return JSONResponse(status_code=200, content={"status": "error", "message": "invalid JSON"})

    # URL verification must be answered before any signature check or profile lookup
    if payload.get("type") == "url_verification":
        logger.info("Slack URL verification challenge received")
        return JSONResponse(
            status_code=200,
            content={"challenge": payload.get("challenge", "")},
        )

    # Resolve the active profile first so we can verify the request signature
    # against the configured signing secret.
    usecases = get_usecases(request)

    profile = await usecases.profile.find_with_active_slack_integration_usecase.execute()

    signing_secret = ""
    if profile:
        for integration in profile.integrations or []:
            if integration.name == "slack" and integration.activated:
                signing_secret = integration.config.get("signing_secret", "")
                break

    app_mode = getattr(request.app.state.config_service.server_config, "mode", "release")
    allow_insecure_dev = str(app_mode) == "debug"

    if not signing_secret and not allow_insecure_dev:
        logger.error("Slack signing secret is not configured; refusing to process webhook")
        return JSONResponse(status_code=200, content={"status": "ignored"})

    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    signature = request.headers.get("X-Slack-Signature", "")

    if allow_insecure_dev and not signing_secret:
        logger.warning("Slack webhook accepted without signature verification in debug mode")
    else:
        verifier = SlackIntegration(bot_token="", signing_secret=signing_secret)
        if not verifier.verify_signature(raw_body, timestamp, signature):
            logger.warning("Slack signature verification failed; ignoring request")
            return JSONResponse(status_code=200, content={"status": "ignored"})

    if payload.get("type") != "event_callback":
        logger.debug(f"Ignoring non-event_callback payload type: {payload.get('type')}")
        return JSONResponse(status_code=200, content={"status": "ok"})

    if not profile:
        logger.warning("No profile found with an active Slack integration; ignoring event")
        return JSONResponse(status_code=200, content={"status": "ignored"})

    try:
        await usecases.slack.process_message_usecase.execute(payload, profile)
    except Exception as e:
        logger.error(f"Error processing Slack event: {str(e)}", exc_info=True)

    # Always return 200 to prevent Slack from retrying the event
    return JSONResponse(status_code=200, content={"status": "ok"})
