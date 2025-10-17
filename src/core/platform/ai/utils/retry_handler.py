"""
Retry Handler Utility

Retry logic with exponential backoff for AI service calls.
"""

import logging
import asyncio
from typing import Callable, Any, Optional, Type
from functools import wraps

logger = logging.getLogger(__name__)


class RetryConfig:
    """Configuration for retry behavior"""

    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
    ):
        """
        Initialize retry configuration.

        Args:
            max_retries: Maximum number of retry attempts
            initial_delay: Initial delay in seconds
            max_delay: Maximum delay between retries
            exponential_base: Base for exponential backoff
            jitter: Whether to add random jitter to delays
        """
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter


class RetryHandler:
    """
    Handler for retrying operations with exponential backoff.
    """

    def __init__(self, config: Optional[RetryConfig] = None):
        """
        Initialize retry handler.

        Args:
            config: Retry configuration
        """
        self.config = config or RetryConfig()

    async def retry_async(
        self,
        func: Callable,
        *args,
        exceptions: tuple = (Exception,),
        **kwargs
    ) -> Any:
        """
        Retry an async function with exponential backoff.

        Args:
            func: Async function to retry
            *args: Positional arguments for func
            exceptions: Tuple of exceptions to catch and retry
            **kwargs: Keyword arguments for func

        Returns:
            Result from successful function call

        Raises:
            Last exception if all retries fail
        """
        last_exception = None
        delay = self.config.initial_delay

        for attempt in range(self.config.max_retries + 1):
            try:
                return await func(*args, **kwargs)

            except exceptions as e:
                last_exception = e

                if attempt < self.config.max_retries:
                    # Calculate delay with exponential backoff
                    current_delay = min(
                        delay * (self.config.exponential_base ** attempt),
                        self.config.max_delay
                    )

                    # Add jitter if enabled
                    if self.config.jitter:
                        import random
                        current_delay *= (0.5 + random.random())

                    logger.warning(
                        f"Attempt {attempt + 1}/{self.config.max_retries + 1} failed: {e}. "
                        f"Retrying in {current_delay:.2f}s..."
                    )

                    await asyncio.sleep(current_delay)
                else:
                    logger.error(
                        f"All {self.config.max_retries + 1} attempts failed. "
                        f"Last error: {e}"
                    )

        # Raise the last exception if all retries failed
        if last_exception:
            raise last_exception

    def retry_sync(
        self,
        func: Callable,
        *args,
        exceptions: tuple = (Exception,),
        **kwargs
    ) -> Any:
        """
        Retry a sync function with exponential backoff.

        Args:
            func: Function to retry
            *args: Positional arguments for func
            exceptions: Tuple of exceptions to catch and retry
            **kwargs: Keyword arguments for func

        Returns:
            Result from successful function call

        Raises:
            Last exception if all retries fail
        """
        import time

        last_exception = None
        delay = self.config.initial_delay

        for attempt in range(self.config.max_retries + 1):
            try:
                return func(*args, **kwargs)

            except exceptions as e:
                last_exception = e

                if attempt < self.config.max_retries:
                    current_delay = min(
                        delay * (self.config.exponential_base ** attempt),
                        self.config.max_delay
                    )

                    if self.config.jitter:
                        import random
                        current_delay *= (0.5 + random.random())

                    logger.warning(
                        f"Attempt {attempt + 1}/{self.config.max_retries + 1} failed: {e}. "
                        f"Retrying in {current_delay:.2f}s..."
                    )

                    time.sleep(current_delay)
                else:
                    logger.error(
                        f"All {self.config.max_retries + 1} attempts failed. "
                        f"Last error: {e}"
                    )

        if last_exception:
            raise last_exception


def with_retry(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    exceptions: tuple = (Exception,)
):
    """
    Decorator for retrying async functions.

    Args:
        max_retries: Maximum retry attempts
        initial_delay: Initial delay in seconds
        exceptions: Exceptions to catch and retry

    Returns:
        Decorated function

    Example:
        @with_retry(max_retries=3, exceptions=(APIError,))
        async def call_api():
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            config = RetryConfig(max_retries=max_retries, initial_delay=initial_delay)
            handler = RetryHandler(config)
            return await handler.retry_async(
                func,
                *args,
                exceptions=exceptions,
                **kwargs
            )
        return wrapper
    return decorator
