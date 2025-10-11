"""
AI Metrics Module

Track and monitor AI service metrics.
"""

import logging
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class RequestMetrics:
    """Metrics for a single AI request"""
    timestamp: datetime
    model: str
    tokens_used: Optional[int] = None
    latency_ms: Optional[float] = None
    success: bool = True
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class AIMetricsCollector:
    """
    Collector for AI service metrics.

    Tracks requests, tokens, latency, errors, etc.
    """

    def __init__(self):
        """Initialize metrics collector"""
        self.requests: list[RequestMetrics] = []
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.total_tokens = 0
        self.total_latency_ms = 0.0

        logger.info("AI Metrics Collector initialized")

    def record_request(
        self,
        model: str,
        tokens_used: Optional[int] = None,
        latency_ms: Optional[float] = None,
        success: bool = True,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Record a request metric.

        Args:
            model: Model used
            tokens_used: Tokens consumed
            latency_ms: Request latency in milliseconds
            success: Whether request succeeded
            error: Error message if failed
            metadata: Additional metadata
        """
        metrics = RequestMetrics(
            timestamp=datetime.utcnow(),
            model=model,
            tokens_used=tokens_used,
            latency_ms=latency_ms,
            success=success,
            error=error,
            metadata=metadata or {},
        )

        self.requests.append(metrics)
        self.total_requests += 1

        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1

        if tokens_used:
            self.total_tokens += tokens_used

        if latency_ms:
            self.total_latency_ms += latency_ms

        logger.debug(f"Recorded metric: {model}, success={success}, tokens={tokens_used}")

    def get_summary(self) -> Dict[str, Any]:
        """
        Get metrics summary.

        Returns:
            Summary statistics
        """
        avg_latency = (
            self.total_latency_ms / self.successful_requests
            if self.successful_requests > 0
            else 0
        )

        avg_tokens = (
            self.total_tokens / self.successful_requests
            if self.successful_requests > 0
            else 0
        )

        success_rate = (
            self.successful_requests / self.total_requests
            if self.total_requests > 0
            else 0
        )

        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": round(success_rate * 100, 2),
            "total_tokens": self.total_tokens,
            "avg_tokens_per_request": round(avg_tokens, 2),
            "avg_latency_ms": round(avg_latency, 2),
        }

    def get_recent_requests(self, limit: int = 10) -> list[RequestMetrics]:
        """
        Get recent requests.

        Args:
            limit: Maximum number of requests to return

        Returns:
            List of recent requests
        """
        return self.requests[-limit:]

    def clear(self) -> None:
        """Clear all metrics"""
        self.requests.clear()
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.total_tokens = 0
        self.total_latency_ms = 0.0
        logger.info("Metrics cleared")


# Global metrics collector
_metrics_collector: Optional[AIMetricsCollector] = None


def get_metrics_collector() -> AIMetricsCollector:
    """
    Get or create global metrics collector.

    Returns:
        Metrics collector instance
    """
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = AIMetricsCollector()
    return _metrics_collector
