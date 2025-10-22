"""
FastAPI Exception Handler

Provides exception handlers for integrating ApplicationError with FastAPI.
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from .application_error import ApplicationError, NewApplicationError
from .mappings.common import RequestBodyValidationError, DatabaseQueryError
from pymongo.errors import PyMongoError
import logging


logger = logging.getLogger(__name__)


async def application_error_handler(request: Request, exc: ApplicationError) -> JSONResponse:
    """
    Handle ApplicationError exceptions in FastAPI.

    Args:
        request: The FastAPI request object
        exc: The ApplicationError instance

    Returns:
        JSONResponse with appropriate status code and error details
    """
    exc.log()

    return JSONResponse(
        status_code=exc.status_code(),
        content=exc.to_dict()
    )


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Handle FastAPI RequestValidationError (Pydantic validation errors).

    Args:
        request: The FastAPI request object
        exc: The RequestValidationError instance

    Returns:
        JSONResponse with validation error details
    """
    app_error = NewApplicationError(
        RequestBodyValidationError,
        Exception(str(exc.errors()))
    )

    app_error.log()

    return JSONResponse(
        status_code=app_error.status_code(),
        content=app_error.to_dict()
    )


async def pymongo_error_handler(request: Request, exc: PyMongoError) -> JSONResponse:
    """
    Handle PyMongo database errors.

    Args:
        request: The FastAPI request object
        exc: The PyMongoError instance

    Returns:
        JSONResponse with database error details
    """
    app_error = NewApplicationError(DatabaseQueryError, exc)

    app_error.log()

    return JSONResponse(
        status_code=app_error.status_code(),
        content=app_error.to_dict()
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle any unhandled exceptions.

    Args:
        request: The FastAPI request object
        exc: The Exception instance

    Returns:
        JSONResponse with generic error message
    """
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "code": "common:internal-server-error",
            "message": "an unexpected error occurred"
        }
    )


def register_exception_handlers(app):
    """
    Register all exception handlers with FastAPI application.

    Args:
        app: The FastAPI application instance

    Example:
        >>> from fastapi import FastAPI
        >>> from src.core.platform.errors.exception_handler import register_exception_handlers
        >>> app = FastAPI()
        >>> register_exception_handlers(app)
    """
    from pymongo.errors import PyMongoError

    app.add_exception_handler(ApplicationError, application_error_handler)

    app.add_exception_handler(RequestValidationError, validation_error_handler)

    app.add_exception_handler(PyMongoError, pymongo_error_handler)

    app.add_exception_handler(Exception, generic_exception_handler)
