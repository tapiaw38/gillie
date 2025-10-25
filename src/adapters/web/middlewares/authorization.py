from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Optional
import jwt
from jwt import PyJWTError
import logging
from src.core.platform.config.service import get_config_service
from src.core.use_cases.use_cases import Usecases

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

EXCLUDED_PATHS = {
    "/docs",
    "/docs/",
    "/openapi.json",
    "/redoc",
    "/redoc/",
    "/health",
    "/api/whatsapp/webhook",
    "/api/whatsapp/process-external-message",
}

async def decode_token(token: str):
    try:
        config = get_config_service().server_config
        payload = jwt.decode(
            token,
            config.jwt_secret,
            algorithms=[config.encryption_algorithm],
        )
        return payload
    except PyJWTError as e:
        logger.warning(f"Token decoding error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {str(e)}")

async def validate_api_key(token: str, usecases: Usecases, method: str):
    secret_key = get_config_service().server_config.jwt_secret
    try:
        payload = jwt.decode(token, secret_key, algorithms=["HS256"])

        # More strict token type checking
        if payload.get("type") != "api_key":
            logger.warning(f"Invalid token type for {method} request")
            return {"valid": False, "error": None}

        user_id = payload.get("user_id")
        api_key = await usecases.profile.find_by_api_key_value_usecase.execute(user_id, token)

        if not api_key:
            logger.warning(f"API key not found for user {user_id}")
            return {"valid": False, "error": None}

        if not api_key.is_active:
            logger.warning(f"Inactive API key for user {user_id}")
            return {"valid": False, "error": None}

        profile = usecases.profile.find_by_user_id_usecase.execute(user_id)

        if not profile:
            logger.warning(f"Profile not found for user {user_id}")
            return {"valid": False, "error": None}

        if not profile.data.is_active:
            logger.warning(f"Inactive profile for user {user_id}")
            return {"valid": False, "error": None}

        # More flexible iteration limit handling
        if (profile.data.iteration_limit is not None and
            profile.data.iteration_limit <= 0 and
            method == "POST"):  # Only restrict POST requests
            logger.warning(f"Iteration limit exhausted for user {user_id}")
            return {"valid": False, "error": "iteration_limit_exhausted"}

        # Optional: Log method-specific API key usage
        logger.info(f"API key validated for {method} request: {user_id}")

        # Decrement iteration limit only for specific methods if needed
        if method == "POST" and profile.data.iteration_limit is not None:
            updated_iteration_limit = profile.data.iteration_limit - 1
            await usecases.profile.update_iteration_limit_usecase.execute(user_id, updated_iteration_limit)

        return {"valid": True, "payload": payload, "error": None}

    except jwt.ExpiredSignatureError:
        logger.warning("Expired token signature")
        return {"valid": False, "error": None}
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {str(e)}")
        return {"valid": False, "error": None}

class AuthorizationMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, usecases: Usecases):
        super().__init__(app)
        self.usecases = usecases

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path in EXCLUDED_PATHS or path.startswith("/api/whatsapp") or request.method == "OPTIONS":
            return await call_next(request)

        authorization: Optional[str] = request.headers.get("Authorization")
        method = request.method

        if authorization:
            parts = authorization.split()
            if len(parts) == 2 and parts[0].lower() == "bearer":
                token = parts[1]
                try:
                    user_id = await decode_token(token)
                    request.state.user = user_id
                    return await call_next(request)
                except HTTPException:
                    # Log bearer token failure for debugging
                    logger.warning(f"Bearer token authentication failed for {path}")

        api_key = request.headers.get("x-api-key")
        if api_key:
            validation_result = await validate_api_key(api_key, self.usecases, method)
            if validation_result["valid"]:
                request.state.user = validation_result["payload"]
                return await call_next(request)
            else:
                # Check if the error is due to iteration limit exhausted
                if validation_result["error"] == "iteration_limit_exhausted":
                    raise HTTPException(
                        status_code=status.HTTP_402_PAYMENT_REQUIRED,
                        detail="Límite de interacciones de API agotado. Por favor actualiza tu plan :("
                    )
                logger.warning(f"API key validation failed for {path} on {method} method")

        # Contextual error message based on method
        detail = (f"Missing or invalid {method} authentication for {path}. "
                  "Ensure you have a valid Bearer token or API key.")

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail
        )