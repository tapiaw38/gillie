"""
Token Counter Utility

Utilities for counting tokens in text.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class TokenCounter:
    """
    Token counter for various models.
    """

    def __init__(self, model_name: str = "gpt-3.5-turbo"):
        """
        Initialize token counter.

        Args:
            model_name: Name of the model to count tokens for
        """
        self.model_name = model_name
        self.encoding = self._get_encoding()

    def _get_encoding(self):
        """Get tiktoken encoding for model"""
        try:
            import tiktoken

            try:
                return tiktoken.encoding_for_model(self.model_name)
            except KeyError:
                logger.warning(
                    f"Model {self.model_name} not found, using cl100k_base encoding"
                )
                return tiktoken.get_encoding("cl100k_base")
        except ImportError:
            logger.warning("tiktoken not installed, using approximation")
            return None

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text.

        Args:
            text: Text to count tokens in

        Returns:
            Number of tokens
        """
        if self.encoding:
            return len(self.encoding.encode(text))
        else:
            # Rough approximation: 1 token ≈ 4 characters
            return len(text) // 4

    def count_messages_tokens(self, messages: list) -> int:
        """
        Count tokens in a list of messages.

        Args:
            messages: List of message dictionaries

        Returns:
            Total tokens including formatting overhead
        """
        total_tokens = 0

        for message in messages:
            # Every message has overhead: role + content separators
            total_tokens += 4  # Message formatting overhead

            for key, value in message.items():
                if isinstance(value, str):
                    total_tokens += self.count_tokens(value)

        total_tokens += 2  # Reply priming

        return total_tokens

    def estimate_cost(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        model: Optional[str] = None
    ) -> float:
        """
        Estimate cost based on token usage.

        Args:
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens
            model: Model name (uses self.model_name if not provided)

        Returns:
            Estimated cost in USD
        """
        model = model or self.model_name

        # Pricing per 1K tokens (as of 2024)
        pricing = {
            "gpt-4": {"prompt": 0.03, "completion": 0.06},
            "gpt-4-32k": {"prompt": 0.06, "completion": 0.12},
            "gpt-3.5-turbo": {"prompt": 0.0015, "completion": 0.002},
            "gpt-3.5-turbo-16k": {"prompt": 0.003, "completion": 0.004},
        }

        # Default pricing if model not found
        default_pricing = {"prompt": 0.0015, "completion": 0.002}

        model_pricing = pricing.get(model, default_pricing)

        prompt_cost = (prompt_tokens / 1000) * model_pricing["prompt"]
        completion_cost = (completion_tokens / 1000) * model_pricing["completion"]

        return prompt_cost + completion_cost


def count_tokens(text: str, model: str = "gpt-3.5-turbo") -> int:
    """
    Quick function to count tokens.

    Args:
        text: Text to count
        model: Model name

    Returns:
        Token count
    """
    counter = TokenCounter(model)
    return counter.count_tokens(text)
