from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import logging
import os

logger = logging.getLogger(__name__)

_PUBLIC_EXACT_PATHS = {
    "/",
    "/health",
}

_PUBLIC_PREFIXES = (
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/slack/events",
    "/api/slack/verify",
    "/api/teams/activities",
    "/api/v1/calendar/oauth/callback",
    "/api/v1/drive/oauth/callback",
    "/api/v1/gmail/oauth/callback",
    "/api/v1/notion/oauth/callback",
)


class SingleUserMiddleware(BaseHTTPMiddleware):
    """
    Single-user middleware: injects a fixed user_id into every request.

    When `profile_client` is provided the middleware validates the incoming
    `x-api-key` header against the active API keys stored in MongoDB.
    If no API keys exist yet (first-run) all requests are allowed so the
    user can create the first key from the UI.
    """

    def __init__(self, app, user_id: str | None = None, profile_client=None):
        super().__init__(app)
        self.user_id = user_id
        self.profile_client = profile_client
        self.trust_localhost = os.getenv("AUTH_TRUST_LOCALHOST", "true").lower() == "true"

    async def dispatch(self, request: Request, call_next):
        user_id = self.user_id or getattr(request.app.state, "user_id", "default-user")
        profile_client = self.profile_client or getattr(request.app.state, "profile_client", None)

        # Always inject the user context
        request.state.user = {"user_id": user_id}

        path = request.url.path
        if path in _PUBLIC_EXACT_PATHS or any(path.startswith(prefix) for prefix in _PUBLIC_PREFIXES):
            return await call_next(request)

        if self.trust_localhost and request.client and request.client.host in {"127.0.0.1", "::1", "localhost"}:
            return await call_next(request)

        if profile_client is None:
            return await call_next(request)

        try:
            has_any_key = await profile_client.find_one(
                {"user_id": user_id, "api_keys": {"$elemMatch": {"is_active": True}}},
            )
        except Exception:
            logger.error("Failed to validate API key state", exc_info=True)
            return JSONResponse(
                status_code=503,
                content={"code": "auth:backend-unavailable", "message": "Authentication backend unavailable"},
            )

        if not has_any_key:
            return await call_next(request)

        api_key = request.headers.get("x-api-key", "").strip()
        if not api_key:
            return JSONResponse(
                status_code=401,
                content={"code": "auth:missing-api-key", "message": "API key required"},
            )

        try:
            match = await profile_client.find_one(
                {
                    "user_id": user_id,
                    "api_keys": {"$elemMatch": {"value": api_key, "is_active": True}},
                },
            )
        except Exception:
            logger.error("Failed to validate incoming API key", exc_info=True)
            return JSONResponse(
                status_code=503,
                content={"code": "auth:backend-unavailable", "message": "Authentication backend unavailable"},
            )

        if not match:
            return JSONResponse(
                status_code=401,
                content={"code": "auth:invalid-api-key", "message": "Invalid or inactive API key"},
            )

        return await call_next(request)
