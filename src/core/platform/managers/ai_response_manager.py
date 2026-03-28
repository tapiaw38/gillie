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
from typing import Optional, List, Tuple
from src.core.platform.functions.smart_function_executor import SmartFunctionExecutor, FunctionResult
from src.core.platform.functions.global_workflows import get_available_workflows

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
        smart_function_executor: Optional[SmartFunctionExecutor] = None,
        mcp_client=None
    ):
        """
        Initialize the AI response service.

        Args:
            openai_integration: OpenAI integration instance
            config_service: Configuration service instance
            smart_function_executor: Optional smart function executor
            mcp_client: Optional MCP client for datetime parsing
        """
        self.openai_integration = openai_integration
        self.config_service = config_service
        self.mcp_client = mcp_client  # Store MCP client for datetime responses
        self.smart_function_executor = smart_function_executor or SmartFunctionExecutor(
            config_service
        )

    async def generate_response(
        self,
        user_message: str,
        profile,
        message_context: Optional[str] = None,
        conversation_history: Optional[str] = None,
        chat_history: Optional[List[str]] = None,
        auth_token: Optional[str] = None,
        client_workspace: str = "",
    ) -> Tuple[Optional[str], str]:
        """
        Generates an AI response with intelligent function execution.

        Returns:
            Tuple of (default_message, response_text) where default_message is an optional
            pre-message to send before the LLM response (set via response_default_message in
            the function config), and response_text is the main AI response.
        """
        try:
            # Check if profile has functions configured
            if self._has_functions_configured(profile):
                return await self._generate_response_with_functions(
                    user_message=user_message,
                    profile=profile,
                    message_context=message_context,
                    conversation_history=conversation_history,
                    chat_history=chat_history,
                    auth_token=auth_token,
                    client_workspace=client_workspace,
                )
            else:
                response = await self._generate_standard_response(
                    user_message=user_message,
                    profile=profile,
                    message_context=message_context,
                    conversation_history=conversation_history,
                    client_workspace=client_workspace,
                )
                return (None, response)

        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
            return (None, self._get_fallback_error_message(profile))

    async def _generate_response_with_functions(
        self,
        user_message: str,
        profile,
        message_context: Optional[str],
        conversation_history: Optional[str],
        chat_history: Optional[List[str]],
        auth_token: Optional[str] = None,
        client_workspace: str = "",
    ) -> Tuple[Optional[str], str]:
        """
        Generates response with smart function execution enabled.

        Args:
            user_message: User's message
            profile: User profile
            message_context: Message context
            conversation_history: Conversation history
            chat_history: Chat history list

        Returns:
            Tuple of (default_message, response_text)
        """
        try:
            logger.info("Using smart function executor for response generation")

            # Execute smart function
            function_result = await self.smart_function_executor.execute_function(
                user_message=user_message,
                profile=profile,
                chat_history=chat_history or [],
                auth_token=auth_token
            )

            # Check if function was successfully executed (None = no match found)
            if function_result is not None:
                logger.info("Function executed successfully")
                return (function_result.default_message, function_result.response)
            else:
                # No matching function found, fallback to standard AI
                logger.info("No function matched, using standard AI response")
                response = await self._generate_standard_response(
                    user_message=user_message,
                    profile=profile,
                    message_context=message_context,
                    conversation_history=conversation_history,
                    client_workspace=client_workspace,
                )
                return (None, response)

        except Exception as function_error:
            logger.error(f"Error in smart function execution: {function_error}")
            # Fallback to standard AI response
            response = await self._generate_standard_response_with_fallback(
                user_message=user_message,
                profile=profile,
                message_context=message_context,
                conversation_history=conversation_history,
                client_workspace=client_workspace,
            )
            return (None, response)

    async def _generate_standard_response(
        self,
        user_message: str,
        profile,
        message_context: Optional[str],
        conversation_history: Optional[str],
        client_workspace: str = "",
    ) -> str:
        """
        Generates a standard AI response without function execution.

        Args:
            user_message: User's message
            profile: User profile
            message_context: Message context (FAQ already injected in add_message_use_case)
            conversation_history: Conversation history

        Returns:
            Generated AI response
        """
        try:
            mcp_response = await self._try_mcp_datetime_response(user_message, profile)
            if mcp_response:
                return mcp_response

            # FAQ context is injected upstream in add_message_use_case
            # to ensure all paths (functions, langchain, standard) receive it
            response = await self.openai_integration.ask(
                user_message,
                message_context,
                conversation_history,
                profile,
                client_workspace=client_workspace,
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
        conversation_history: Optional[str],
        client_workspace: str = "",
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
                conversation_history=conversation_history,
                client_workspace=client_workspace,
            )
        except Exception as fallback_error:
            logger.error(f"Error in fallback AI response: {fallback_error}")
            return self._get_fallback_error_message(profile)

    def _has_functions_configured(self, profile) -> bool:
        """
        Checks if the profile has functions configured or global workflows available.

        Args:
            profile: User profile

        Returns:
            True if functions are configured OR global workflows are available, False otherwise
        """
        if profile.functions:
            return True

        try:
            global_workflows = get_available_workflows(profile)
            if global_workflows and len(global_workflows) > 0:
                logger.info(f"Profile has {len(global_workflows)} global workflows available")
                return True
        except Exception as e:
            logger.warning(f"Error checking global workflows: {e}")

        return False

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

    async def _try_mcp_datetime_response(
        self, user_message: str, profile
    ) -> Optional[str]:
        """
        Tries to answer date/time questions using MCP server.

        Detects if user is asking about current date/time and responds
        directly from MCP without using OpenAI.

        Args:
            user_message: User's message
            profile: User profile with timezone info

        Returns:
            MCP response string if question is about date/time, None otherwise
        """
        if not hasattr(self, 'mcp_client') or self.mcp_client is None:
            return None

        message_lower = user_message.lower().strip()

        datetime_patterns = [
            # Fecha
            'qué día', 'que dia', 'qué fecha', 'que fecha',
            'cuál es la fecha', 'cual es la fecha',
            # Hora
            'qué hora', 'que hora', 'cuál es la hora', 'cual es la hora',
            # Día de la semana
            'qué día es hoy', 'que dia es hoy', 'día de hoy',
            # Ambos
            'fecha y hora', 'hora y fecha', 'día y hora',
            # Inglés
            'what time', 'what date', 'what day', 'current time', 'current date',
            # Portugués
            'que horas', 'que dia', 'data de hoje',
        ]

        is_datetime_question = any(
            pattern in message_lower for pattern in datetime_patterns
        )

        if not is_datetime_question:
            return None

        try:
            user_timezone = getattr(profile, 'timezone', None)
            if not user_timezone:
                user_timezone = "America/Argentina/Buenos_Aires"

            result = await self.mcp_client.get_current_datetime(
                timezone=user_timezone,
                format_type="readable"
            )

            if result.get("success"):
                formats = result.get("formats", {})
                readable = formats.get("readable", "")
                date_only = formats.get("date_only", "")
                time_only = formats.get("time_only", "")

                if 'fecha' in message_lower or 'dia' in message_lower or 'date' in message_lower or 'day' in message_lower:
                    if 'hora' in message_lower or 'time' in message_lower:
                        response = f"📅 Hoy es {date_only} y son las {time_only}."
                    else:
                        from datetime import datetime

                        iso_datetime = formats.get("iso8601", "")
                        dt = datetime.fromisoformat(iso_datetime)
                        day_names = {
                            0: "lunes", 1: "martes", 2: "miércoles",
                            3: "jueves", 4: "viernes", 5: "sábado", 6: "domingo"
                        }
                        day_name = day_names.get(dt.weekday(), "")
                        response = f"📅 Hoy es {day_name}, {date_only}."
                elif 'hora' in message_lower or 'time' in message_lower:
                    response = f"🕐 Son las {time_only}."
                else:
                    response = f"📅 {readable}"

                logger.info(f"MCP answered datetime question: {user_message}")
                return response

        except Exception as e:
            logger.error(f"Error getting datetime from MCP: {str(e)}")
            return None

        return None
