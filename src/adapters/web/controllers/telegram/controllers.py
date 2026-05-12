import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, PlainTextResponse

from src.core.use_cases.use_cases import Usecases
from src.adapters.web.dependencies import get_usecases

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/telegram", tags=["Telegram"])


@router.get("/verify", response_class=PlainTextResponse)
async def verify():
    return "Telegram webhook server is running"


@router.post("/webhook")
async def telegram_webhook(
    req: Request,
    usecases: Usecases = Depends(get_usecases),
):
    """
    Telegram Bot API webhook endpoint.

    Receives updates from Telegram, verifies the optional secret token,
    finds the matching profile, and processes messages via AI.
    Always returns HTTP 200 to avoid Telegram retries.
    """
    try:
        payload: Dict[str, Any] = await req.json()
        logger.info(f"[telegram] Webhook received update_id={payload.get('update_id')}")

        profile = await usecases.profile.find_with_active_telegram_integration_usecase.execute()

        if not profile:
            logger.warning("[telegram] No profile found with active Telegram integration")
            return JSONResponse(status_code=200, content={"status": "ignored"})

        # Verify secret token if configured
        secret_token = None
        if profile.integrations:
            for integration in profile.integrations:
                if integration.name == "telegram" and integration.activated:
                    secret_token = integration.config.get("secret_token", "")
                    break

        if secret_token:
            header_token = req.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
            if header_token != secret_token:
                logger.warning("[telegram] Invalid secret token in webhook request")
                return JSONResponse(status_code=200, content={"status": "unauthorized"})

        result = await usecases.telegram.process_message_usecase.execute(payload, profile)
        logger.info(f"[telegram] Processing result: {result}")
        return JSONResponse(status_code=200, content={"status": "ok"})

    except Exception as e:
        logger.error(f"[telegram] Unhandled error in webhook: {e}", exc_info=True)
        return JSONResponse(status_code=200, content={"status": "error", "message": str(e)})


@router.post("/set-webhook")
async def set_webhook(
    req: Request,
    usecases: Usecases = Depends(get_usecases),
):
    """
    Register the webhook URL with Telegram using the configured bot token.
    Call this endpoint once after configuring the integration.
    """
    try:
        body = await req.json()
        webhook_url = body.get("webhook_url")
        if not webhook_url:
            return JSONResponse(status_code=400, content={"error": "webhook_url is required"})

        profile = await usecases.profile.find_with_active_telegram_integration_usecase.execute()
        if not profile:
            return JSONResponse(status_code=404, content={"error": "No active Telegram integration found"})

        bot_token = None
        secret_token = ""
        for integration in (profile.integrations or []):
            if integration.name == "telegram" and integration.activated:
                bot_token = integration.config.get("bot_token")
                secret_token = integration.config.get("secret_token", "")
                break

        if not bot_token:
            return JSONResponse(status_code=400, content={"error": "bot_token not configured"})

        from src.adapters.web.integrations.telegram.telegram import TelegramIntegration
        tg = TelegramIntegration(bot_token=bot_token, secret_token=secret_token)
        ok = tg.set_webhook(webhook_url)

        if ok:
            return {"status": "success", "webhook_url": webhook_url}
        return JSONResponse(status_code=500, content={"error": "Failed to set webhook on Telegram"})

    except Exception as e:
        logger.error(f"[telegram] Error setting webhook: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"error": str(e)})
