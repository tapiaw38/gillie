"""
AI Response Service

This service handles AI-powered response generation with smart function execution,
following the Single Responsibility Principle by focusing
solely on AI interaction and response generation.

Responsibilities:
- Execute smart functions when available
- Generate AI responses using OpenAI integration
- Handle fallback scenarios gracefully
- Provide error recovery mechanisms
"""

import logging
from typing import Optional, List
from src.core.platform.functions.smart_function_executor import SmartFunctionExecutor

logger = logging.getLogger(__name__)


class AIResponseService:
    """
    Service for generating AI responses with smart function execution.

    This service encapsulates the logic for determining whether to use
    function execution or standard AI responses, with proper fallback handling.
    """

    def __init__(
        self,
        openai_integration,
        config_service,
        smart_function_executor: Optional[SmartFunctionExecutor] = None
    ):
        """
        Initialize the AI response service.

        Args:
            openai_integration: OpenAI integration instance
            config_service: Configuration service instance
            smart_function_executor: Optional smart function executor
        """
        self.openai_integration = openai_integration
        self.config_service = config_service
        self.smart_function_executor = smart_function_executor or SmartFunctionExecutor(
            config_service
        )

    async def generate_response(
        self,
        user_message: str,
        profile,
        message_context: Optional[str] = None,
        conversation_history: Optional[str] = None,
        chat_history: Optional[List[str]] = None
    ) -> str:
        """
        Generates an AI response with intelligent function execution.

        This method implements a strategy pattern:
        1. If functions are configured, try smart function execution
        2. If function execution fails or returns no match, use standard AI
        3. If all fails, return a friendly error message

        Args:
            user_message: The user's message content
            profile: User profile with assistant configuration
            message_context: Optional message context
            conversation_history: Optional conversation history string
            chat_history: Optional list of recent chat messages

        Returns:
            Generated AI response string
        """
        try:
            # Check if profile has functions configured
            if self._has_functions_configured(profile):
                return await self._generate_response_with_functions(
                    user_message=user_message,
                    profile=profile,
                    message_context=message_context,
                    conversation_history=conversation_history,
                    chat_history=chat_history
                )
            else:
                return await self._generate_standard_response(
                    user_message=user_message,
                    profile=profile,
                    message_context=message_context,
                    conversation_history=conversation_history
                )

        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
            return self._get_fallback_error_message(profile)

    async def _generate_response_with_functions(
        self,
        user_message: str,
        profile,
        message_context: Optional[str],
        conversation_history: Optional[str],
        chat_history: Optional[List[str]]
    ) -> str:
        """
        Generates response with smart function execution enabled.

        Args:
            user_message: User's message
            profile: User profile
            message_context: Message context
            conversation_history: Conversation history
            chat_history: Chat history list

        Returns:
            Generated response
        """
        try:
            logger.info("Using smart function executor for response generation")

            # Execute smart function
            function_response = await self.smart_function_executor.execute_function(
                user_message=user_message,
                profile=profile,
                chat_history=chat_history or []
            )

            # Check if function was successfully executed
            if function_response and not function_response.startswith(
                "No encontré una función"
            ):
                logger.info("Function executed successfully")
                return function_response
            else:
                # No matching function found, fallback to standard AI
                logger.info("No function found, using standard AI response")
                return await self._generate_standard_response(
                    user_message=user_message,
                    profile=profile,
                    message_context=message_context,
                    conversation_history=conversation_history
                )

        except Exception as function_error:
            logger.error(f"Error in smart function execution: {function_error}")
            # Fallback to standard AI response
            return await self._generate_standard_response_with_fallback(
                user_message=user_message,
                profile=profile,
                message_context=message_context,
                conversation_history=conversation_history
            )

    async def _generate_standard_response(
        self,
        user_message: str,
        profile,
        message_context: Optional[str],
        conversation_history: Optional[str]
    ) -> str:
        """
        Generates a standard AI response without function execution.

        Args:
            user_message: User's message
            profile: User profile
            message_context: Message context
            conversation_history: Conversation history

        Returns:
            Generated AI response
        """
        try:
            response = await self.openai_integration.ask(
                user_message,
                message_context,
                conversation_history,
                profile
            )
            return response

        except Exception as e:
            logger.error(f"Error in standard AI response: {e}")
            raise

    async def _generate_standard_response_with_fallback(
        self,
        user_message: str,
        profile,
        message_context: Optional[str],
        conversation_history: Optional[str]
    ) -> str:
        """
        Generates standard AI response with error fallback.

        Args:
            user_message: User's message
            profile: User profile
            message_context: Message context
            conversation_history: Conversation history

        Returns:
            Generated response or fallback error message
        """
        try:
            return await self._generate_standard_response(
                user_message=user_message,
                profile=profile,
                message_context=message_context,
                conversation_history=conversation_history
            )
        except Exception as fallback_error:
            logger.error(f"Error in fallback AI response: {fallback_error}")
            return self._get_fallback_error_message(profile)

    def _has_functions_configured(self, profile) -> bool:
        """
        Checks if the profile has functions configured.

        Args:
            profile: User profile

        Returns:
            True if functions are configured, False otherwise
        """
        return bool(profile.functions)

    def _get_fallback_error_message(self, profile) -> str:
        """
        Returns a friendly fallback error message.

        Args:
            profile: User profile to get assistant name

        Returns:
            Friendly error message
        """
        assistant_name = getattr(profile, "assistant_name", "Asistente")
        return (
            f"¡Hola! Soy {assistant_name} 😊 Disculpa, estoy teniendo algunos "
            f"problemas técnicos en este momento. ¿Podrías intentarlo de nuevo "
            f"en unos minutos?"
        )
