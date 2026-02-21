"""
LangChain Service

Enhanced AI service using LangChain with:
- Pydantic validation for tools
- LangGraph memory management
- LangSmith observability
- Automatic retry and error handling
"""

import logging
import asyncio
import os
from typing import List, Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.tools import StructuredTool

from src.core.platform.config.service import ConfigurationService
from src.core.domain import Profile
from .tools.models import create_langchain_tools
from .memory.manager import ConversationMemoryManager

logger = logging.getLogger(__name__)


class LangChainService:
    """
    LangChain-based AI service with enhanced capabilities.

    Features:
    - Structured tool validation with Pydantic
    - Persistent memory with LangGraph
    - Optional LangSmith tracing
    - Concurrency control
    - Circuit breaker pattern
    """

    def __init__(
        self,
        config_service: ConfigurationService,
        openai_integration,
        max_concurrent_requests: int = 3,
        enable_langsmith: bool = False,
    ):
        """
        Initialize the LangChain service.

        Args:
            config_service: Configuration service instance
            openai_integration: OpenAI integration for tool execution
            max_concurrent_requests: Maximum concurrent LLM requests
            enable_langsmith: Enable LangSmith tracing
        """
        self.config = config_service.openai_config
        self.openai_integration = openai_integration

        # Initialize LangChain ChatOpenAI
        self.llm = ChatOpenAI(
            model=self.config.model,
            api_key=self.config.api_key,
            base_url=self.config.base_url if hasattr(self.config, 'base_url') and self.config.base_url else None,
            temperature=0.7,
            max_tokens=2000,
            timeout=45.0,
            max_retries=3,
        )

        # Initialize memory manager
        self.memory_manager = ConversationMemoryManager(max_messages=20)

        # Concurrency control
        self.semaphore = asyncio.Semaphore(max_concurrent_requests)

        # Circuit breaker
        self._consecutive_failures = 0
        self._max_failures = 3
        self._circuit_open_until = None

        # LangSmith configuration
        self.enable_langsmith = enable_langsmith
        if enable_langsmith:
            self._setup_langsmith()

        logger.info(
            f"LangChainService initialized: model={self.config.model}, "
            f"langsmith={enable_langsmith}"
        )

    def _setup_langsmith(self):
        """Configure LangSmith tracing"""
        try:
            from src.core.platform.config.service import get_config_service
            config = get_config_service()
            langsmith_config = config.langsmith_config

            if langsmith_config.api_key:
                os.environ["LANGCHAIN_TRACING_V2"] = "true"
                os.environ["LANGCHAIN_API_KEY"] = langsmith_config.api_key
                os.environ["LANGCHAIN_PROJECT"] = langsmith_config.project
                if langsmith_config.endpoint:
                    os.environ["LANGCHAIN_ENDPOINT"] = langsmith_config.endpoint
                logger.info(f"LangSmith tracing enabled: project={langsmith_config.project}")
            else:
                logger.warning("LANGSMITH_API_KEY not found, tracing disabled")
                self.enable_langsmith = False

        except Exception as e:
            logger.error(f"Error setting up LangSmith: {e}")
            self.enable_langsmith = False

    def _is_circuit_open(self) -> bool:
        """Check if circuit breaker is open"""
        if self._circuit_open_until is None:
            return False

        import time
        if time.time() < self._circuit_open_until:
            return True

        # Reset circuit
        self._circuit_open_until = None
        self._consecutive_failures = 0
        logger.info("Circuit breaker reset")
        return False

    def _record_failure(self):
        """Record a failure and potentially open circuit"""
        self._consecutive_failures += 1
        logger.warning(f"LLM failure #{self._consecutive_failures}")

        if self._consecutive_failures >= self._max_failures:
            import time
            self._circuit_open_until = time.time() + 60  # 60 seconds
            logger.error("Circuit breaker OPENED - bypassing LLM for 60 seconds")

    def _record_success(self):
        """Record a successful request"""
        if self._consecutive_failures > 0:
            logger.info(f"LLM recovered after {self._consecutive_failures} failures")
            self._consecutive_failures = 0

    async def generate_response(
        self,
        question: str,
        context: Optional[str],
        previous_messages: List[Dict[str, Any]],
        profile: Profile,
        conversation_id: str,
        use_tools: bool = True,
    ) -> str:
        """
        Generate AI response using LangChain with tool support.

        Args:
            question: User's question
            context: Additional context (RAG results, etc.)
            previous_messages: Conversation history
            profile: User profile
            conversation_id: Conversation identifier
            use_tools: Whether to enable tool calling

        Returns:
            Generated response text

        Raises:
            Exception: If circuit breaker is open or generation fails
        """

        # Check circuit breaker
        if self._is_circuit_open():
            logger.warning("Circuit breaker is OPEN - using fallback")
            raise Exception("AI service temporarily unavailable (circuit breaker)")

        async with self.semaphore:
            try:
                # Build system prompt
                system_prompt = self._build_system_prompt(profile, context)

                # Convert messages to LangChain format
                messages = self._convert_messages_to_langchain(
                    previous_messages=previous_messages,
                    system_prompt=system_prompt,
                    current_question=question
                )

                # Optimize message history
                thread_id = self.memory_manager.create_thread_id(
                    conversation_id, profile.user_id
                )
                messages = self.memory_manager.optimize_message_history(
                    messages, system_prompt=None  # Already included
                )

                # Create LLM with tools if enabled
                tools = None
                if use_tools:
                    tools = create_langchain_tools(
                        self.openai_integration,
                        profile,
                    )
                    llm_with_tools = self.llm.bind_tools(tools)
                    logger.debug(f"Bound {len(tools)} tools to LLM")
                else:
                    llm_with_tools = self.llm
                    logger.debug("No tools enabled")

                # Generate response
                logger.info(f"Generating response for user {profile.user_id}")
                response = await llm_with_tools.ainvoke(messages)

                # Handle tool calls if present
                if hasattr(response, 'tool_calls') and response.tool_calls:
                    response_text = await self._handle_tool_calls(
                        response=response,
                        messages=messages,
                        llm_with_tools=llm_with_tools,
                        tools=tools
                    )
                else:
                    response_text = response.content

                # Save checkpoint
                self.memory_manager.save_checkpoint(
                    thread_id=thread_id,
                    messages=messages + [response],
                    metadata={"profile_id": profile.user_id}
                )

                self._record_success()
                logger.info("Response generated successfully")
                return response_text

            except Exception as e:
                self._record_failure()
                logger.error(f"Error generating response: {e}")
                raise

    async def _handle_tool_calls(
        self,
        response: AIMessage,
        messages: List,
        llm_with_tools,
        tools: List = None
    ) -> str:
        """
        Handle tool calls from the AI response.

        Args:
            response: AI response with tool calls
            messages: Current message history
            llm_with_tools: LLM instance with tools
            tools: List of available tools

        Returns:
            Final response text after tool execution
        """
        logger.info(f"Handling {len(response.tool_calls)} tool calls")

        # Add AI response to messages
        messages.append(response)

        # Execute each tool call
        for tool_call in response.tool_calls:
            try:
                tool_name = tool_call.get("name")
                tool_args = tool_call.get("args", {})
                tool_id = tool_call.get("id", "unknown")

                logger.info(f"Executing tool: {tool_name} with args: {tool_args}")

                # Find and execute the tool
                tool_result = None
                tool_found = False

                for tool in tools or []:
                    if tool.name == tool_name:
                        tool_found = True
                        try:
                            # Try different execution methods
                            if hasattr(tool, 'coroutine') and tool.coroutine:
                                # Prefer coroutine for async tools
                                logger.debug(f"Executing tool via coroutine")
                                tool_result = await tool.coroutine(**tool_args)
                            elif hasattr(tool, 'afunc') and tool.afunc:
                                # Try afunc (async function)
                                logger.debug(f"Executing tool via afunc")
                                tool_result = await tool.afunc(**tool_args)
                            elif hasattr(tool, 'func') and tool.func:
                                # Fallback to func (may be sync or async)
                                logger.debug(f"Executing tool via func")
                                import asyncio
                                import inspect
                                if inspect.iscoroutinefunction(tool.func):
                                    tool_result = await tool.func(**tool_args)
                                else:
                                    tool_result = tool.func(**tool_args)
                            else:
                                logger.error(f"Tool {tool_name} has no executable method")
                                tool_result = f"Tool {tool_name} has no executable method"
                        except Exception as e:
                            logger.error(f"Error executing tool function: {e}", exc_info=True)
                            tool_result = f"Error executing tool: {str(e)}"
                        break

                if not tool_found:
                    logger.warning(f"Tool {tool_name} not found in bound tools")
                    tool_result = f"Tool {tool_name} not found"

                # Convert result to string if it's a dict
                if isinstance(tool_result, dict):
                    import json
                    tool_result_str = json.dumps(tool_result, ensure_ascii=False)
                else:
                    tool_result_str = str(tool_result)

                logger.info(f"Tool {tool_name} result: {tool_result_str[:200]}...")

                tool_message = ToolMessage(
                    content=tool_result_str,
                    tool_call_id=tool_id,
                )
                messages.append(tool_message)

            except Exception as e:
                logger.error(f"Error executing tool {tool_name}: {e}", exc_info=True)
                tool_message = ToolMessage(
                    content=f"Error executing tool: {str(e)}",
                    tool_call_id=tool_id,
                )
                messages.append(tool_message)

        # Generate final response with tool results
        logger.info("Generating final response with tool results")
        final_response = await llm_with_tools.ainvoke(messages)
        return final_response.content

    def _build_system_prompt(
        self,
        profile: Profile,
        context: Optional[str]
    ) -> str:
        """
        Build system prompt from profile and context.

        Args:
            profile: User profile
            context: Additional context

        Returns:
            System prompt string
        """
        from src.adapters.web.integrations.openapi.context import (
            CONTEXT_INFORMATION,
            CONTEXT_ROLE_ASSISTANT,
            CONTEXT_ROLE_SELLER,
            CONTEXT_ROLE_TUTOR,
            CONTEXT_RULES,
        )

        system_prompt = CONTEXT_INFORMATION.format(
            assistant_name=profile.assistant_name,
            business_name=profile.business_name,
            business_context=profile.business_context,
            functions=profile.functions,
            product_context=context or "",
            question="",  # Will be added as separate message
            previous_messages="",  # Handled by message history
        )

        # Add role-specific context
        if profile.role == "seller":
            system_prompt += CONTEXT_ROLE_SELLER
        elif profile.role == "tutor":
            system_prompt += CONTEXT_ROLE_TUTOR
        elif profile.role == "assistant":
            system_prompt += CONTEXT_ROLE_ASSISTANT

        system_prompt += CONTEXT_RULES

        # Add strong FAQ priority instructions if FAQs are in context
        if context and "PREGUNTAS FRECUENTES" in context:
            system_prompt += (
                "\n\nINSTRUCCIÓN CRÍTICA - PRIORIDAD ABSOLUTA:\n"
                "Las PREGUNTAS FRECUENTES (FAQs) están incluidas en el contexto anterior.\n"
                "DEBES seguir este proceso ESTRICTAMENTE:\n"
                "1. PRIMERO: Lee cuidadosamente todas las FAQs en el contexto\n"
                "2. Si la pregunta del usuario coincide con alguna FAQ (aunque sea parcialmente), USA LA RESPUESTA DE LA FAQ DIRECTAMENTE\n"
                "3. NO uses herramientas de búsqueda (search_faqs, search_documents) si ya tienes la respuesta en las FAQs del contexto\n"
                "4. SOLO si NO encuentras la respuesta en las FAQs del contexto, entonces puedes usar herramientas de búsqueda\n"
                "5. Las respuestas de las FAQs son oficiales y pre-aprobadas, tienen prioridad sobre cualquier otra información\n"
            )

        return system_prompt

    def _convert_messages_to_langchain(
        self,
        previous_messages: List[Dict[str, Any]],
        system_prompt: str,
        current_question: str
    ) -> List:
        """
        Convert application messages to LangChain format.

        Args:
            previous_messages: List of previous messages
            system_prompt: System prompt
            current_question: Current user question

        Returns:
            List of LangChain messages
        """
        messages = []

        # Add system prompt
        messages.append(SystemMessage(content=system_prompt))

        # Add conversation history
        langchain_history = self.memory_manager.messages_to_langchain(
            previous_messages
        )
        messages.extend(langchain_history)

        # Add current question
        messages.append(HumanMessage(content=current_question))

        return messages

    def get_stats(self) -> Dict[str, Any]:
        """
        Get service statistics.

        Returns:
            Dictionary with service stats
        """
        return {
            "model": self.config.model,
            "langsmith_enabled": self.enable_langsmith,
            "consecutive_failures": self._consecutive_failures,
            "circuit_open": self._is_circuit_open(),
            "memory_stats": self.memory_manager.get_memory_stats(),
        }
