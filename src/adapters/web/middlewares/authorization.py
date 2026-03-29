from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import logging

logger = logging.getLogger(__name__)

_PUBLIC_PREFIXES = (
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/v1/calendar/oauth/callback",
    "/api/v1/drive/oauth/callback",
    "/api/v1/gmail/oauth/callback",
)


class SingleUserMiddleware(BaseHTTPMiddleware):
    """
    Single-user middleware: injects a fixed user_id into every request.

    When `profile_client` is provided the middleware validates the incoming
    `x-api-key` header against the active API keys stored in MongoDB.
    If no API keys exist yet (first-run) all requests are allowed so the
    user can create the first key from the UI.
    """

    def __init__(self, app, user_id: str, profile_client=None):
        super().__init__(app)
        self.user_id = user_id
        self.profile_client = profile_client

    async def dispatch(self, request: Request, call_next):
        # Always inject the user context
        request.state.user = {"user_id": self.user_id}

        path = request.url.path
        if any(path.startswith(prefix) for prefix in _PUBLIC_PREFIXES):
            return await call_next(request)

        if self.profile_client is None:
            return await call_next(request)

        try:
            has_any_key = self.profile_client.find_one(
                {"user_id": self.user_id, "api_keys": {"$elemMatch": {"is_active": True}}}
            )
        except Exception:
            return await call_next(request)

        if not has_any_key:
            return await call_next(request)

        api_key = request.headers.get("x-api-key", "").strip()
        if not api_key:
            return JSONResponse(
                status_code=401,
                content={"code": "auth:missing-api-key", "message": "API key required"},
            )

        try:
            match = self.profile_client.find_one(
                {
                    "user_id": self.user_id,
                    "api_keys": {"$elemMatch": {"value": api_key, "is_active": True}},
                }
            )
        except Exception:
            return await call_next(request)

        if not match:
            return JSONResponse(
                status_code=401,
                content={"code": "auth:invalid-api-key", "message": "Invalid or inactive API key"},
            )

        return await call_next(request)
