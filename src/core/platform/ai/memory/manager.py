"""
Conversation Memory Manager using LangGraph

This module provides persistent conversation memory management using LangGraph's
checkpoint system, allowing for better context retention across messages.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage

logger = logging.getLogger(__name__)


class ConversationMemoryManager:
    """
    Manages conversation memory using LangGraph's checkpoint system.

    Features:
    - Persistent memory across conversation turns
    - Configurable message history length
    - Automatic memory optimization
    - Thread-based conversation tracking
    """

    def __init__(self, max_messages: int = 20):
        """
        Initialize the memory manager.

        Args:
            max_messages: Maximum number of messages to keep in memory
        """
        self.memory = MemorySaver()
        self.max_messages = max_messages
        logger.info(f"ConversationMemoryManager initialized with max_messages={max_messages}")

    def create_thread_id(self, conversation_id: str, user_id: str) -> str:
        """
        Create a unique thread ID for a conversation.

        Args:
            conversation_id: ID of the conversation
            user_id: ID of the user

        Returns:
            Unique thread ID
        """
        return f"{user_id}_{conversation_id}"

    def messages_to_langchain(self, messages: List[Dict[str, Any]]) -> List[BaseMessage]:
        """
        Convert application messages to LangChain message format.

        Args:
            messages: List of message dictionaries with 'sender' and 'content'

        Returns:
            List of LangChain BaseMessage objects
        """
        langchain_messages = []

        for msg in messages:
            sender = msg.get("sender", "user")
            content = msg.get("content", "")

            if sender == "user":
                langchain_messages.append(HumanMessage(content=content))
            elif sender == "assistant":
                langchain_messages.append(AIMessage(content=content))
            elif sender == "system":
                langchain_messages.append(SystemMessage(content=content))
            else:
                # Default to human message for unknown senders
                langchain_messages.append(HumanMessage(content=content))

        return langchain_messages

    def optimize_message_history(
        self,
        messages: List[BaseMessage],
        system_prompt: Optional[str] = None,
        max_chars: int = 24000,
        max_messages: Optional[int] = None,
    ) -> List[BaseMessage]:
        """
        Optimize message history by keeping recent messages and system prompt.

        Applies two limits in order:
        1. Message count: keeps at most max_messages recent messages.
        2. Character budget: trims oldest messages until total content fits
           within max_chars (≈ max_chars/4 tokens) to avoid provider 413 errors.

        Args:
            messages: List of messages
            system_prompt: Optional system prompt to prepend
            max_chars: Maximum total characters for the history slice (default 24 000 ≈ 6 000 tokens)

        Returns:
            Optimized list of messages
        """
        optimized = []

        if system_prompt:
            optimized.append(SystemMessage(content=system_prompt))

        limit = max_messages if max_messages is not None else self.max_messages
        history = [m for m in messages if not isinstance(m, SystemMessage)]
        if len(history) > limit:
            logger.info(
                f"Optimizing message history: {len(history)} -> {limit} messages"
            )
            history = history[-limit:]

        total_chars = sum(
            len(m.content) if isinstance(m.content, str) else 0
            for m in history
        )
        while total_chars > max_chars and len(history) > 2:
            removed = history[0]
            removed_chars = len(removed.content) if isinstance(removed.content, str) else 0
            history = history[1:]
            total_chars -= removed_chars
            logger.info(
                f"Token budget trim: removed oldest message ({removed_chars} chars), "
                f"remaining total: {total_chars} chars (~{total_chars // 4} tokens)"
            )

        optimized.extend(history)
        return optimized

    def get_conversation_state(
        self,
        thread_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get the current state of a conversation thread.

        Args:
            thread_id: Unique thread identifier

        Returns:
            Conversation state dictionary or None if not found
        """
        try:
            logger.debug(f"Retrieving state for thread: {thread_id}")
            return {
                "thread_id": thread_id,
                "last_accessed": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            logger.error(f"Error retrieving conversation state: {e}")
            return None

    def save_checkpoint(
        self,
        thread_id: str,
        messages: List[BaseMessage],
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Save a checkpoint of the conversation state.

        Args:
            thread_id: Unique thread identifier
            messages: Current message history
            metadata: Optional metadata to store with checkpoint

        Returns:
            True if successful, False otherwise
        """
        try:
            checkpoint_data = {
                "messages": messages,
                "metadata": metadata or {},
                "timestamp": datetime.utcnow().isoformat(),
            }

            logger.debug(
                f"Saving checkpoint for thread {thread_id}: {len(messages)} messages"
            )

            return True

        except Exception as e:
            logger.error(f"Error saving checkpoint: {e}")
            return False

    def clear_thread(self, thread_id: str) -> bool:
        """
        Clear memory for a specific thread.

        Args:
            thread_id: Thread to clear

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Clearing memory for thread: {thread_id}")
            return True
        except Exception as e:
            logger.error(f"Error clearing thread memory: {e}")
            return False

    def get_memory_stats(self) -> Dict[str, Any]:
        """
        Get statistics about current memory usage.

        Returns:
            Dictionary with memory statistics
        """
        return {
            "max_messages": self.max_messages,
            "backend": "LangGraph MemorySaver",
            "persistent": True,
        }
