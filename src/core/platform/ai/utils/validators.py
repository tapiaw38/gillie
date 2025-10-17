"""
Response Validators

Validate AI-generated responses for quality and safety.
"""

import logging
import re
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of response validation"""
    is_valid: bool
    issues: List[str]
    warnings: List[str]
    metadata: Dict[str, Any]


class ResponseValidator:
    """
    Validator for AI responses.

    Checks for:
    - Minimum/maximum length
    - Prohibited content
    - Required patterns
    - Quality metrics
    """

    def __init__(
        self,
        min_length: int = 10,
        max_length: int = 10000,
        prohibited_patterns: Optional[List[str]] = None,
        required_patterns: Optional[List[str]] = None,
    ):
        """
        Initialize validator.

        Args:
            min_length: Minimum response length
            max_length: Maximum response length
            prohibited_patterns: Patterns that should not appear
            required_patterns: Patterns that must appear
        """
        self.min_length = min_length
        self.max_length = max_length
        self.prohibited_patterns = prohibited_patterns or []
        self.required_patterns = required_patterns or []

    def validate(self, response: str) -> ValidationResult:
        """
        Validate a response.

        Args:
            response: Response text to validate

        Returns:
            ValidationResult with validation status and issues
        """
        issues = []
        warnings = []
        metadata = {}

        # Check length
        response_length = len(response)
        metadata["length"] = response_length

        if response_length < self.min_length:
            issues.append(f"Response too short: {response_length} < {self.min_length}")

        if response_length > self.max_length:
            issues.append(f"Response too long: {response_length} > {self.max_length}")

        # Check for prohibited patterns
        for pattern in self.prohibited_patterns:
            if re.search(pattern, response, re.IGNORECASE):
                issues.append(f"Prohibited pattern found: {pattern}")

        # Check for required patterns
        for pattern in self.required_patterns:
            if not re.search(pattern, response, re.IGNORECASE):
                warnings.append(f"Required pattern missing: {pattern}")

        # Check for potential issues
        if self._contains_repetition(response):
            warnings.append("Response contains excessive repetition")

        if self._is_empty_or_generic(response):
            issues.append("Response is empty or too generic")

        is_valid = len(issues) == 0
        metadata["warning_count"] = len(warnings)
        metadata["issue_count"] = len(issues)

        return ValidationResult(
            is_valid=is_valid,
            issues=issues,
            warnings=warnings,
            metadata=metadata,
        )

    def _contains_repetition(self, text: str, threshold: int = 5) -> bool:
        """Check if text contains excessive repetition"""
        words = text.split()
        if len(words) < 10:
            return False

        # Check for repeated phrases
        for i in range(len(words) - threshold):
            phrase = " ".join(words[i:i + threshold])
            remaining = " ".join(words[i + threshold:])
            if phrase in remaining:
                return True

        return False

    def _is_empty_or_generic(self, text: str) -> bool:
        """Check if response is empty or too generic"""
        text = text.strip()

        if not text:
            return True

        # Check for overly generic responses
        generic_responses = [
            "i don't know",
            "i'm not sure",
            "i cannot help",
            "i can't answer",
        ]

        text_lower = text.lower()
        return any(generic in text_lower for generic in generic_responses)


class SafetyValidator:
    """
    Validator for safety and appropriateness of AI responses.
    """

    def __init__(self):
        """Initialize safety validator"""
        self.sensitive_patterns = [
            r"\b(password|api[_\s]?key|secret|token)\b",
            r"\b\d{3}-\d{2}-\d{4}\b",  # SSN pattern
            r"\b\d{16}\b",  # Credit card pattern (simple)
        ]

    def validate_safety(self, response: str) -> ValidationResult:
        """
        Validate response for safety concerns.

        Args:
            response: Response to validate

        Returns:
            ValidationResult with safety assessment
        """
        issues = []
        warnings = []
        metadata = {}

        # Check for sensitive information
        for pattern in self.sensitive_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            if matches:
                issues.append(f"Potential sensitive information detected: {pattern}")
                metadata["sensitive_matches"] = matches

        # Check for very long URLs (potential for injection)
        url_pattern = r'https?://[^\s]{100,}'
        if re.search(url_pattern, response):
            warnings.append("Response contains very long URL")

        is_valid = len(issues) == 0

        return ValidationResult(
            is_valid=is_valid,
            issues=issues,
            warnings=warnings,
            metadata=metadata,
        )
