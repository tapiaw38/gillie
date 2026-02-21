from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import logging

logger = logging.getLogger(__name__)


class SingleUserMiddleware(BaseHTTPMiddleware):
    """
    Single-user middleware: injects a fixed user_id into every request.
    No authentication required — all requests are treated as the single configured user.
    """

    def __init__(self, app, user_id: str):
        super().__init__(app)
        self.user_id = user_id

    async def dispatch(self, request: Request, call_next):
        request.state.user = {"user_id": self.user_id}
        return await call_next(request)
