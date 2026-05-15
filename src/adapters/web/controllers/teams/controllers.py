import logging
from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse

from src.core.use_cases.use_cases import Usecases
from src.adapters.web.dependencies import get_usecases

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/teams", tags=["teams"])


@router.post("/verify", status_code=status.HTTP_200_OK)
async def verify_teams_connection(
    request: Request,
    usecases: Usecases = Depends(get_usecases),
):
    """Verify that the configured Teams app_id + app_password can obtain a Bot Framework token."""
    user_id = request.state.user.get("user_id")
    await usecases.teams.verify_connection_usecase.execute(user_id)
    return {"status": "ok", "message": "Teams credentials verified successfully"}


@router.post("/activities", status_code=status.HTTP_200_OK)
async def teams_activities(request: Request):
    """
    Receive Bot Framework activities from Microsoft Teams.

    Teams sends a POST to this endpoint when a user messages the bot.
    No auth middleware is applied here — the Bot Framework activity contains
    the service URL and conversation IDs needed to reply.
    """
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse(status_code=200, content={"status": "ignored", "reason": "invalid json"})

    try:
        usecases: Usecases = request.app.state.usecases
        tenant_id = (
            payload.get("channelData", {}).get("tenant", {}).get("id")
            or payload.get("conversation", {}).get("tenantId", "")
        )
        activity_type = payload.get("type", "")
        channel_id = payload.get("channelId", "")
        service_url = payload.get("serviceUrl", "")
        authorization = request.headers.get("Authorization", "")

        all_profiles = await usecases.profile.find_all_usecase.execute()
        active_profiles = []
        for candidate in all_profiles:
            for integration in candidate.integrations or []:
                if integration.name == "teams" and integration.activated:
                    active_profiles.append((candidate, integration))
                    break

        profile = None
        if tenant_id:
            profile = await usecases.profile.find_with_active_teams_integration_by_tenant_id_usecase.execute(tenant_id)

        if profile is None and len(active_profiles) == 1 and not active_profiles[0][1].config.get("tenant_id"):
            profile = active_profiles[0][0]

        if profile is None:
            logger.warning("Teams activity received but no active Teams integration found")
            return JSONResponse(status_code=200, content={"status": "ignored", "reason": "no active integration"})

        integration = next(
            (integ for integ in (profile.integrations or []) if integ.name == "teams" and integ.activated),
            None,
        )
        if integration is None:
            return JSONResponse(status_code=200, content={"status": "ignored", "reason": "no active integration"})

        client = request.app.state.integrations.make_teams_client(
            integration.config.get("app_id", ""),
            integration.config.get("app_password", ""),
        )
        client.validate_incoming_activity(
            authorization_header=authorization,
            service_url=service_url,
            channel_id=channel_id,
        )

        # Respond immediately to non-message activities after auth succeeds.
        if activity_type != "message":
            return JSONResponse(status_code=200, content={"status": "ignored", "type": activity_type})

        result = await usecases.teams.process_message_usecase.execute(payload, profile)
        return JSONResponse(status_code=200, content=result)

    except Exception as e:
        logger.error(f"Error processing Teams activity: {e}", exc_info=True)
        # Always return 200 to Teams to prevent retries
        return JSONResponse(status_code=200, content={"status": "error"})
