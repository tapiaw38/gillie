"""
Application Error Module

This module defines the core error handling infrastructure for the application.
It provides structured error handling with unique error codes, HTTP status codes,
and automatic logging capabilities.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any
import logging
from abc import ABC, abstractmethod


@dataclass
class ErrorDetails:
    """
    Error details definition containing all information about a specific error type.

    Attributes:
        internal_code: Unique identifier for the error (e.g., "profile:create:validation-error")
        status_code: HTTP status code to return to client (e.g., 400, 404, 500)
        message: User-friendly error message
    """
    internal_code: str
    status_code: int
    message: str


class ApplicationError(Exception, ABC):
    """
    Base exception class for all application errors.

    Provides structured error handling with:
    - Unique error codes for identifying error types
    - Appropriate HTTP status codes
    - User-friendly messages
    - Original error tracking for debugging
    - Automatic logging capabilities
    - Extra context fields for detailed logging
    """

    def __init__(
        self,
        error_details: ErrorDetails,
        original_error: Optional[Exception] = None,
        extra_fields: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize an ApplicationError.

        Args:
            error_details: ErrorDetails object with error information
            original_error: The original exception that caused this error (for debugging)
            extra_fields: Additional context fields for logging
        """
        self.error_details = error_details
        self.original_error = original_error
        self.extra_fields = extra_fields or {}

        super().__init__(self.message())

    def internal_code(self) -> str:
        """Get the unique internal error code."""
        return self.error_details.internal_code

    def status_code(self) -> int:
        """Get the HTTP status code for this error."""
        return self.error_details.status_code

    def message(self) -> str:
        """Get the user-friendly error message."""
        return self.error_details.message

    def original_message(self) -> str:
        """Get the original technical error message (for debugging)."""
        if self.original_error:
            return str(self.original_error)
        return ""

    def add_extra_fields(self, fields: Dict[str, Any]) -> 'ApplicationError':
        """
        Add extra context fields for logging.

        Args:
            fields: Dictionary of additional fields to log

        Returns:
            Self for method chaining
        """
        self.extra_fields.update(fields)
        return self

    def is_based_on(self, error_details: ErrorDetails) -> bool:
        """
        Check if this error is based on a specific ErrorDetails.

        Args:
            error_details: ErrorDetails to compare against

        Returns:
            True if this error matches the given ErrorDetails
        """
        return self.error_details.internal_code == error_details.internal_code

    def log(self) -> None:
        """
        Log this error with structured context.

        Logs all relevant information including:
        - Internal error code
        - HTTP status code
        - User-friendly message
        - Original technical error message
        - Any extra context fields
        """
        logger = logging.getLogger(__name__)

        log_data = {
            "internal_code": self.internal_code(),
            "status_code": self.status_code(),
            "message": self.message(),
            "original_message": self.original_message(),
            **self.extra_fields
        }

        logger.error(f"ApplicationError: {log_data}")

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert error to dictionary for JSON serialization.

        Returns:
            Dictionary with code and message for API responses
        """
        return {
            "code": self.internal_code(),
            "message": self.message()
        }


class ConcreteApplicationError(ApplicationError):
    """
    Concrete implementation of ApplicationError.

    This class can be instantiated directly to create application errors.
    Use NewApplicationError factory function for consistent error creation.
    """
    pass


def NewApplicationError(
    error_details: ErrorDetails,
    original_error: Optional[Exception] = None,
    extra_fields: Optional[Dict[str, Any]] = None
) -> ApplicationError:
    """
    Factory function to create ApplicationError instances.

    Args:
        error_details: ErrorDetails object defining the error
        original_error: Optional original exception
        extra_fields: Optional extra context for logging

    Returns:
        A new ApplicationError instance

    Example:
        >>> from src.core.platform.errors.mappings.profile import ProfileCreateQueryError
        >>> error = NewApplicationError(ProfileCreateQueryError, original_exception)
        >>> error.log()
        >>> return error
    """
    return ConcreteApplicationError(error_details, original_error, extra_fields)
