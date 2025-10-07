"""
Message History Service

This service handles message history operations and conversions,
following the Single Responsibility Principle by focusing
solely on message history management.

Responsibilities:
- Convert messages to string format for AI context
- Build chat history from messages
- Extract recent conversation context
"""

import logging
from typing import List, Optional
from src.core.domain import Message

logger = logging.getLogger(__name__)


class MessageHistoryService:
    """
    Service for managing and formatting message history.

    This service encapsulates all message history operations,
    making them reusable and testable.
    """

    def convert_messages_to_string(self, messages: List[Message]) -> str:
        """
        Converts a list of Message objects to a single string for context.

        This format is used to provide conversation context to AI models.

        Args:
            messages: List of Message domain objects

        Returns:
            String representation of messages
        """
        if not messages:
            return ""

        message_objects = [
            f"{message.sender}: {message.content}"
            for message in messages
        ]
        return " - ".join(message_objects)

    def build_chat_history(
        self,
        messages: List[Message],
        max_messages: int = 5
    ) -> List[str]:
        """
        Builds a chat history list from messages for function execution.

        Takes the most recent messages to maintain context while
        avoiding token limit issues.

        Args:
            messages: List of Message domain objects
            max_messages: Maximum number of recent messages to include

        Returns:
            List of formatted message strings
        """
        if not messages:
            return []

        # Take the last N messages
        recent_messages = messages[-max_messages:] if len(messages) > max_messages else messages

        chat_history = [
            f"{msg.sender}: {msg.content}"
            for msg in recent_messages
        ]

        logger.info(
            f"Built chat history with {len(chat_history)} messages "
            f"from {len(messages)} total messages"
        )

        return chat_history

    def get_last_messages(
        self,
        messages: List[Message],
        count: int = 10
    ) -> List[Message]:
        """
        Retrieves the last N messages from the conversation.

        Args:
            messages: List of Message domain objects
            count: Number of recent messages to retrieve

        Returns:
            List of the most recent messages
        """
        if not messages:
            return []

        return messages[-count:] if len(messages) > count else messages

    def count_messages(self, messages: List[Message]) -> int:
        """
        Counts the total number of messages.

        Args:
            messages: List of Message domain objects

        Returns:
            Total message count
        """
        return len(messages) if messages else 0

    def get_messages_by_sender(
        self,
        messages: List[Message],
        sender: str
    ) -> List[Message]:
        """
        Filters messages by sender.

        Args:
            messages: List of Message domain objects
            sender: Sender identifier (e.g., 'user', 'assistant')

        Returns:
            Filtered list of messages from the specified sender
        """
        if not messages:
            return []

        return [msg for msg in messages if msg.sender == sender]

    def has_previous_messages(self, messages: Optional[List[Message]]) -> bool:
        """
        Checks if there are any previous messages in the conversation.

        Args:
            messages: List of Message domain objects or None

        Returns:
            True if messages exist, False otherwise
        """
        return bool(messages and len(messages) > 0)

    def format_message_for_logging(self, message: Message, max_length: int = 100) -> str:
        """
        Formats a message for logging purposes with content truncation.

        Args:
            message: Message domain object
            max_length: Maximum length of content to include

        Returns:
            Formatted message string for logging
        """
        content_preview = (
            message.content[:max_length] + "..."
            if len(message.content) > max_length
            else message.content
        )

        return f"[{message.sender}] {content_preview}"
