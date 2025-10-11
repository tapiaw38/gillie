"""
Circuit Breaker Service

Implements the Circuit Breaker pattern for AI services to prevent
cascading failures and provide graceful degradation.
"""

import logging
import time
from typing import Callable, Any, Optional
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Blocking requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker"""
    failure_threshold: int = 3  # Failures before opening
    success_threshold: int = 2  # Successes in half-open before closing
    timeout: float = 60.0  # Seconds to wait before half-open
    half_open_max_calls: int = 1  # Max calls allowed in half-open


class CircuitBreakerService:
    """
    Circuit Breaker implementation for AI services.

    Prevents cascading failures by temporarily blocking requests
    when the service is experiencing issues.
    """

    def __init__(self, config: Optional[CircuitBreakerConfig] = None):
        """
        Initialize circuit breaker.

        Args:
            config: Circuit breaker configuration
        """
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self.half_open_calls = 0

        logger.info(
            f"Circuit breaker initialized: threshold={self.config.failure_threshold}, "
            f"timeout={self.config.timeout}s"
        )

    def is_open(self) -> bool:
        """Check if circuit is open (blocking requests)"""
        if self.state == CircuitState.OPEN:
            # Check if timeout expired
            if self._should_attempt_reset():
                self._move_to_half_open()
                return False
            return True
        return False

    def record_success(self) -> None:
        """Record a successful operation"""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            logger.info(
                f"Circuit breaker: success in HALF_OPEN state "
                f"({self.success_count}/{self.config.success_threshold})"
            )

            if self.success_count >= self.config.success_threshold:
                self._move_to_closed()
        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success
            if self.failure_count > 0:
                logger.info(
                    f"Circuit breaker: service recovered after {self.failure_count} failures"
                )
                self.failure_count = 0

    def record_failure(self) -> None:
        """Record a failed operation"""
        self.failure_count += 1
        self.last_failure_time = time.time()

        logger.warning(
            f"Circuit breaker: failure #{self.failure_count} "
            f"(threshold: {self.config.failure_threshold})"
        )

        if self.state == CircuitState.HALF_OPEN:
            # Single failure in half-open reopens circuit
            self._move_to_open()
        elif self.failure_count >= self.config.failure_threshold:
            self._move_to_open()

    async def call(
        self,
        func: Callable,
        *args,
        fallback: Optional[Callable] = None,
        **kwargs
    ) -> Any:
        """
        Call a function through the circuit breaker.

        Args:
            func: Async function to call
            *args: Positional arguments for func
            fallback: Optional fallback function if circuit is open
            **kwargs: Keyword arguments for func

        Returns:
            Result from func or fallback

        Raises:
            CircuitBreakerOpenError: If circuit is open and no fallback provided
        """
        if self.is_open():
            logger.warning("Circuit breaker is OPEN - request blocked")
            if fallback:
                logger.info("Using fallback function")
                return await fallback(*args, **kwargs) if callable(fallback) else fallback
            raise CircuitBreakerOpenError("Circuit breaker is open")

        # Track half-open calls
        if self.state == CircuitState.HALF_OPEN:
            self.half_open_calls += 1
            if self.half_open_calls > self.config.half_open_max_calls:
                raise CircuitBreakerOpenError("Too many calls in half-open state")

        try:
            result = await func(*args, **kwargs)
            self.record_success()
            return result
        except Exception as e:
            self.record_failure()
            raise

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        if self.last_failure_time is None:
            return False
        elapsed = time.time() - self.last_failure_time
        return elapsed >= self.config.timeout

    def _move_to_open(self) -> None:
        """Move circuit to OPEN state"""
        self.state = CircuitState.OPEN
        self.success_count = 0
        self.half_open_calls = 0
        logger.error(
            f"Circuit breaker OPENED - blocking requests for {self.config.timeout}s"
        )

    def _move_to_half_open(self) -> None:
        """Move circuit to HALF_OPEN state"""
        self.state = CircuitState.HALF_OPEN
        self.half_open_calls = 0
        logger.info("Circuit breaker moved to HALF_OPEN - testing service health")

    def _move_to_closed(self) -> None:
        """Move circuit to CLOSED state"""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.half_open_calls = 0
        logger.info("Circuit breaker CLOSED - normal operation resumed")

    def get_state(self) -> dict:
        """Get current circuit breaker state"""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time,
        }

    def reset(self) -> None:
        """Manually reset the circuit breaker"""
        logger.info("Circuit breaker manually reset")
        self._move_to_closed()


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open"""
    pass
