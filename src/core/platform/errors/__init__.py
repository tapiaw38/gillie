"""
Platform Errors Module

Provides structured error handling infrastructure for the application.
"""

from .application_error import (
    ApplicationError,
    ErrorDetails,
    NewApplicationError,
    ConcreteApplicationError
)

__all__ = [
    "ApplicationError",
    "ErrorDetails",
    "NewApplicationError",
    "ConcreteApplicationError"
]
