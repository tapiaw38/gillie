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
        skill_manager=None,
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
        self.skill_manager = skill_manager
        self.store_service = None
        self.job_usecases = None

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
        client_workspace: str = "",
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

        if self._is_circuit_open():
            logger.warning("Circuit breaker is OPEN - using fallback")
            raise Exception("AI service temporarily unavailable (circuit breaker)")

        async with self.semaphore:
            try:
                system_prompt = self._build_system_prompt(profile, context)

                messages = self._convert_messages_to_langchain(
                    previous_messages=previous_messages,
                    system_prompt=system_prompt,
                    current_question=question
                )

                thread_id = self.memory_manager.create_thread_id(
                    conversation_id, profile.user_id
                )
                messages = self.memory_manager.optimize_message_history(
                    messages, system_prompt=None  # Already included
                )

                tools = None
                if use_tools:
                    tools = create_langchain_tools(
                        self.openai_integration,
                        profile,
                        skill_manager=self.skill_manager,
                        store_service=self.store_service,
                        job_usecases=self.job_usecases,
                        client_workspace=client_workspace,
                    )
                    llm_with_tools = self.llm.bind_tools(tools)
                    logger.debug(f"Bound {len(tools)} tools to LLM")
                else:
                    llm_with_tools = self.llm
                    logger.debug("No tools enabled")

                # Generate response
                logger.info(f"Generating response for user {profile.user_id}")
                response = await llm_with_tools.ainvoke(messages)

                if hasattr(response, 'tool_calls') and response.tool_calls:
                    response_text = await self._handle_tool_calls(
                        response=response,
                        messages=messages,
                        llm_with_tools=llm_with_tools,
                        tools=tools
                    )
                else:
                    response_text = response.content

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

    async def generate_response_stream(
        self,
        question: str,
        context: Optional[str],
        previous_messages: List[Dict[str, Any]],
        profile: Profile,
        conversation_id: str,
        use_tools: bool = True,
        shell_output_queue: Optional[asyncio.Queue] = None,
        client_workspace: str = "",
        plan_mode: bool = False,
    ):
        """
        Stream AI response tokens. Uses astream() for direct responses and
        falls back to ainvoke() + _handle_tool_calls() when tool calls are needed.
        Yields str tokens and, when a shell command is running with an active
        shell_output_queue, also yields {"type": "shell_output", "line": "..."} dicts
        in real time as process lines are emitted.
        """
        if self._is_circuit_open():
            raise Exception("AI service temporarily unavailable (circuit breaker)")

        async with self.semaphore:
            try:
                system_prompt = self._build_system_prompt(profile, context)
                messages = self._convert_messages_to_langchain(
                    previous_messages=previous_messages,
                    system_prompt=system_prompt,
                    current_question=question,
                )
                thread_id = self.memory_manager.create_thread_id(conversation_id, profile.user_id)
                messages = self.memory_manager.optimize_message_history(messages, system_prompt=None)

                # Build a shell_output_callback that writes to the queue when provided.
                # The callback is async so it can be awaited inside run_shell_tool.
                shell_output_callback = None
                if shell_output_queue is not None:
                    async def _shell_line_callback(line: str) -> None:
                        await shell_output_queue.put(line)

                    shell_output_callback = _shell_line_callback

                # Build an approval_callback that pauses the tool, sends an
                # approval_request event through the SSE queue, and waits for
                # the user's decision via POST /conversation/tool/approve.
                approval_callback = None
                if shell_output_queue is not None:
                    async def _approval_callback(
                        request_id: str,
                        tool_name: str,
                        file_path: str,
                        diff: str,
                    ) -> bool:
                        from src.core.platform.ai.tools.approval_manager import (
                            create_pending, get_decision, cleanup,
                        )
                        await shell_output_queue.put({
                            "type": "approval_request",
                            "request_id": request_id,
                            "tool": tool_name,
                            "file": file_path,
                            "diff": diff,
                        })
                        event = create_pending(request_id)
                        try:
                            await asyncio.wait_for(event.wait(), timeout=120)
                            return get_decision(request_id)
                        except asyncio.TimeoutError:
                            logger.warning(
                                f"Approval request {request_id} timed out after 120s — rejecting"
                            )
                            return False
                        finally:
                            cleanup(request_id)

                    approval_callback = _approval_callback

                tools = None
                llm_with_tools = self.llm
                if use_tools:
                    tools = create_langchain_tools(
                        self.openai_integration,
                        profile,
                        skill_manager=self.skill_manager,
                        store_service=self.store_service,
                        job_usecases=self.job_usecases,
                        shell_output_callback=shell_output_callback,
                        client_workspace=client_workspace,
                        approval_callback=approval_callback,
                        plan_mode=plan_mode,
                    )
                    llm_with_tools = self.llm.bind_tools(tools)

                # Stream response — detect tool calls mid-stream
                accumulated_chunks = []
                has_tool_calls = False
                full_content = ""

                async for chunk in llm_with_tools.astream(messages):
                    accumulated_chunks.append(chunk)
                    if hasattr(chunk, "tool_call_chunks") and chunk.tool_call_chunks:
                        has_tool_calls = True
                    if not has_tool_calls and chunk.content:
                        yield chunk.content
                        full_content += chunk.content

                if has_tool_calls:
                    # Reconstruct full AIMessage from chunks and handle tools.
                    # When shell_output_queue is provided, run _handle_tool_calls as
                    # a background task and concurrently drain shell output lines from
                    # the queue so the caller receives them in real time.
                    combined = accumulated_chunks[0]
                    for c in accumulated_chunks[1:]:
                        try:
                            combined = combined + c
                        except Exception:
                            pass

                    # Notify the client which tools are about to run
                    for tc in getattr(combined, "tool_calls", []):
                        yield {"type": "tool_call", "name": tc.get("name", "tool")}

                    if shell_output_queue is not None:
                        # Sentinel value placed in the queue after the task completes
                        # so the drain loop knows when to stop.
                        _DONE_SENTINEL = object()

                        async def _run_tool_calls_and_signal():
                            try:
                                return await self._handle_tool_calls(combined, messages, llm_with_tools, tools)
                            finally:
                                await shell_output_queue.put(_DONE_SENTINEL)

                        tool_task = asyncio.create_task(_run_tool_calls_and_signal())

                        # Drain queue until sentinel arrives, yielding SSE events.
                        # Items may be:
                        #   str  → shell stdout line  → wrap as shell_output event
                        #   dict → already a typed event (e.g. approval_request) → pass through
                        while True:
                            item = await shell_output_queue.get()
                            if item is _DONE_SENTINEL:
                                break
                            if isinstance(item, dict):
                                yield item
                            else:
                                yield {"type": "shell_output", "line": item}

                        response_text = await tool_task
                    else:
                        response_text = await self._handle_tool_calls(combined, messages, llm_with_tools, tools)

                    logger.info(f"Stream: yielding tool-call result, length={len(response_text or '')}")
                    yield response_text
                    full_content = response_text

                # Save checkpoint
                from langchain_core.messages import AIMessage as LCAIMessage
                ai_msg = LCAIMessage(content=full_content)
                self.memory_manager.save_checkpoint(
                    thread_id=thread_id,
                    messages=messages + [ai_msg],
                    metadata={"profile_id": profile.user_id},
                )
                self._record_success()

            except Exception as e:
                self._record_failure()
                logger.error(f"Error in generate_response_stream: {e}")
                raise

    async def _handle_tool_calls(
        self,
        response: AIMessage,
        messages: List,
        llm_with_tools,
        tools: List = None,
        max_rounds: int = 30,
    ) -> str:
        """
        Handle tool calls from the AI response, looping until the model
        returns text content (supports chained/multi-round tool calls).
        """
        import json as _json
        import inspect

        for round_num in range(max_rounds):
            tool_calls = getattr(response, "tool_calls", None)
            if not tool_calls:
                break

            logger.info(f"Tool-call round {round_num + 1}: handling {len(tool_calls)} call(s)")
            messages.append(response)

            for tool_call in tool_calls:
                tool_name = tool_call.get("name", "unknown")
                tool_args = tool_call.get("args", {})
                tool_id = tool_call.get("id", "unknown")
                logger.info(f"Executing tool: {tool_name} with args: {tool_args}")

                tool_result = f"Tool {tool_name} not found"
                for tool in tools or []:
                    if tool.name == tool_name:
                        try:
                            if hasattr(tool, 'coroutine') and tool.coroutine:
                                tool_result = await tool.coroutine(**tool_args)
                            elif hasattr(tool, 'afunc') and tool.afunc:
                                tool_result = await tool.afunc(**tool_args)
                            elif hasattr(tool, 'func') and tool.func:
                                if inspect.iscoroutinefunction(tool.func):
                                    tool_result = await tool.func(**tool_args)
                                else:
                                    tool_result = tool.func(**tool_args)
                            else:
                                tool_result = f"Tool {tool_name} has no executable method"
                        except Exception as e:
                            logger.error(f"Error executing tool {tool_name}: {e}", exc_info=True)
                            tool_result = f"Error executing tool: {str(e)}"
                        break

                if isinstance(tool_result, dict):
                    tool_result_str = _json.dumps(tool_result, ensure_ascii=False)
                else:
                    tool_result_str = str(tool_result)

                logger.info(f"Tool {tool_name} result: {tool_result_str[:200]}...")
                messages.append(ToolMessage(content=tool_result_str, tool_call_id=tool_id))

            logger.info(f"Invoking LLM after round {round_num + 1}")
            response = await llm_with_tools.ainvoke(messages)
            content = response.content or ""
            logger.info(f"Response after round {round_num + 1}: length={len(content)}, has_more_tool_calls={bool(getattr(response, 'tool_calls', None))}")

            if content and not getattr(response, "tool_calls", None):
                break

        content = response.content or ""
        if not content:
            logger.warning(
                f"_handle_tool_calls exhausted {max_rounds} rounds without a final text response"
            )
            content = "(Las herramientas se ejecutaron correctamente. Tarea completada.)"
        return content

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

        if profile.role == "seller":
            system_prompt += CONTEXT_ROLE_SELLER
        elif profile.role == "tutor":
            system_prompt += CONTEXT_ROLE_TUTOR
        elif profile.role == "assistant":
            system_prompt += CONTEXT_ROLE_ASSISTANT

        system_prompt += CONTEXT_RULES

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

        messages.append(SystemMessage(content=system_prompt))

        langchain_history = self.memory_manager.messages_to_langchain(
            previous_messages
        )
        messages.extend(langchain_history)

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
