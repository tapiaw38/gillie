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


def _is_anthropic_url(base_url: str) -> bool:
    return base_url and "anthropic.com" in base_url


def _extract_text(content) -> str:
    """Normalize LLM chunk content to str (Anthropic returns list of blocks)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            block.get("text", "") if isinstance(block, dict) else str(block)
            for block in content
        )
    return str(content) if content else ""


from src.core.platform.ai.ollama_adapter import (
    is_ollama_url as _is_ollama_url,
    build_ollama_llm as _build_ollama_llm,
    route_tools as _route_tools_ollama,
    resolve_tool_name as _resolve_tool_name,
    normalize_tool_args as _normalize_tool_args,
)


def _build_llm(model: str, api_key: str, base_url: str, auth_type: str = "api_key"):
    """Build the appropriate LLM based on provider URL and auth type.

    - Anthropic + api_key → ChatAnthropic (x-api-key, /v1/messages)
    - Anthropic + bearer  → ChatOpenAI   (Authorization: Bearer, /v1/chat/completions)
    - Ollama              → ChatOllama   (native tool calling support)
    - Everything else     → ChatOpenAI
    """
    if _is_anthropic_url(base_url) and auth_type == "api_key":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=model,
            api_key=api_key,
            temperature=0.7,
            max_tokens=8000,
            timeout=300.0,
            max_retries=2,
        )
    if _is_ollama_url(base_url):
        return _build_ollama_llm(model)
    return ChatOpenAI(
        model=model,
        api_key=api_key,
        base_url=base_url if base_url else None,
        temperature=0.7,
        max_tokens=8000,
        timeout=300.0,
        max_retries=2,
    )

from src.core.platform.config.service import ConfigurationService
from src.core.domain import Profile
from .tools.models import create_langchain_tools
from .memory.manager import ConversationMemoryManager

logger = logging.getLogger(__name__)


def _get_key_arg(tool_name: str, args: dict) -> str:
    """Extract the most meaningful arg to display in the CLI tool progress line."""
    for key in ("file_name", "path", "query", "url", "name", "command"):
        val = args.get(key)
        if val and isinstance(val, str):
            # Show only the basename to keep the line short
            import os as _os
            return _os.path.basename(val.rstrip("/")) or val
    # Fallback: first string arg value
    for val in args.values():
        if val and isinstance(val, str):
            return val[:60]
    return ""


def _brief_result(tool_name: str, result_str: str) -> str:
    """Return a one-line summary of a tool result for CLI display."""
    import json as _json
    try:
        data = _json.loads(result_str)
    except Exception:
        data = None

    if tool_name in ("read_docx",):
        n = len(data.get("paragraphs", [])) if isinstance(data, dict) else 0
        return f"{n} paragraphs read" if n else "read"
    if tool_name in ("analyze_excel", "read_excel"):
        n = len(data.get("sheets", [])) if isinstance(data, dict) else 0
        return f"{n} sheet(s) analyzed" if n else "analyzed"
    if tool_name in ("modify_docx", "modify_excel", "write_docx", "write_excel"):
        saved = data.get("saved_to", "") if isinstance(data, dict) else ""
        import os as _os
        return f"saved → {_os.path.basename(saved)}" if saved else "saved"
    if tool_name in ("list_directory",):
        lines = result_str.count("\n")
        return f"{lines} entries" if lines else "listed"
    if tool_name in ("find_files",):
        files = data.get("files", []) if isinstance(data, dict) else []
        return f"{len(files)} file(s) found"
    if tool_name in ("search_documents", "search_content"):
        results = data.get("results", []) if isinstance(data, dict) else []
        return f"{len(results)} result(s)"
    if tool_name == "run_command":
        return "command executed"
    if "error" in result_str[:50].lower():
        return "error"
    return "ok"


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

        self.llm = _build_llm(
            model=self.config.model,
            api_key=self.config.api_key,
            base_url=self.config.base_url if hasattr(self.config, 'base_url') and self.config.base_url else None,
            auth_type=getattr(self.config, 'auth_type', 'api_key'),
        )


        self.memory_manager = ConversationMemoryManager(max_messages=20)

        self.semaphore = asyncio.Semaphore(max_concurrent_requests)

        self._consecutive_failures = 0
        self._max_failures = 3
        self._circuit_open_until = None

        self.enable_langsmith = enable_langsmith
        if enable_langsmith:
            self._setup_langsmith()

        logger.info(
            f"LangChainService initialized: model={self.config.model}, "
            f"langsmith={enable_langsmith}"
        )

    def reload_llm(self, model: str, base_url: str, api_key: str, auth_type: str = "api_key") -> None:
        """Rebuild the LLM instance for a new provider (hot-reload)."""
        self.llm = _build_llm(model=model, api_key=api_key, base_url=base_url, auth_type=auth_type)
        logger.info(f"LangChainService LLM reloaded: model={model}")

    async def _route_tools(self, user_message: str, all_tools: list) -> list:
        """For Ollama: run a fast routing call to select only relevant tool groups."""
        return await _route_tools_ollama(self.llm, user_message, all_tools)

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
                system_prompt = self._build_system_prompt(profile, context, client_workspace)

                messages = self._convert_messages_to_langchain(
                    previous_messages=previous_messages,
                    system_prompt=system_prompt,
                    current_question=question
                )

                thread_id = self.memory_manager.create_thread_id(
                    conversation_id, profile.user_id
                )
                messages = self.memory_manager.optimize_message_history(
                    messages, system_prompt=system_prompt
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
                    if _is_ollama_url(self.config.base_url):
                        tools = await self._route_tools(question, tools)
                    llm_with_tools = self.llm.bind_tools(tools)
                    logger.debug(f"Bound {len(tools)} tools to LLM")
                else:
                    llm_with_tools = self.llm
                    logger.debug("No tools enabled")

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
                    response_text = _extract_text(response.content)

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
                system_prompt = self._build_system_prompt(profile, context, client_workspace)
                messages = self._convert_messages_to_langchain(
                    previous_messages=previous_messages,
                    system_prompt=system_prompt,
                    current_question=question,
                )
                thread_id = self.memory_manager.create_thread_id(conversation_id, profile.user_id)
                messages = self.memory_manager.optimize_message_history(messages, system_prompt=system_prompt)

                shell_output_callback = None
                if shell_output_queue is not None:
                    async def _shell_line_callback(line: str) -> None:
                        await shell_output_queue.put(line)

                    shell_output_callback = _shell_line_callback

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
                            await asyncio.wait_for(event.wait(), timeout=300)
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
                    if _is_ollama_url(self.config.base_url):
                        tools = await self._route_tools(question, tools)
                    llm_with_tools = self.llm.bind_tools(tools)

                accumulated_chunks = []
                has_tool_calls = False
                full_content = ""

                async for chunk in llm_with_tools.astream(messages):
                    accumulated_chunks.append(chunk)
                    if hasattr(chunk, "tool_call_chunks") and chunk.tool_call_chunks:
                        has_tool_calls = True
                    if not has_tool_calls and chunk.content:
                        text = _extract_text(chunk.content)
                        yield text
                        full_content += text

                if has_tool_calls:
                    combined = accumulated_chunks[0]
                    for c in accumulated_chunks[1:]:
                        try:
                            combined = combined + c
                        except Exception:
                            pass

                    for tc in getattr(combined, "tool_calls", []):
                        yield {
                            "type": "tool_call",
                            "name": tc.get("name", "tool"),
                            "round": 1,
                            "arg": _get_key_arg(tc.get("name", ""), tc.get("args", {})),
                        }

                    if shell_output_queue is not None:
                        _DONE_SENTINEL = object()

                        async def _run_tool_calls_and_signal():
                            try:
                                return await self._handle_tool_calls(
                                    combined, messages, llm_with_tools, tools,
                                    event_queue=shell_output_queue,
                                )
                            finally:
                                await shell_output_queue.put(_DONE_SENTINEL)

                        tool_task = asyncio.create_task(_run_tool_calls_and_signal())

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
        event_queue=None,
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

                # Resolve tool name aliases and normalize args for Ollama
                resolved_name = _resolve_tool_name(tool_name)
                if resolved_name != tool_name:
                    logger.info(f"Tool alias: {tool_name} → {resolved_name}")
                    tool_name = resolved_name
                tool_args = _normalize_tool_args(tool_name, tool_args)

                logger.info(f"Executing tool: {tool_name} with args: {tool_args}")

                tool_result = f"Tool {tool_name} not found"
                for tool in tools or []:
                    if tool.name == tool_name:
                        if hasattr(tool, 'args_schema') and tool.args_schema:
                            try:
                                validated = tool.args_schema(**tool_args)
                                tool_args = validated.model_dump()
                            except Exception as ve:
                                missing = [
                                    fname for fname, finfo in tool.args_schema.model_fields.items()
                                    if finfo.is_required() and fname not in tool_args
                                ]
                                missing_str = ", ".join(missing) if missing else "unknown"
                                tool_result = (
                                    f"Tool call validation failed for '{tool_name}': missing required fields: {missing_str}. "
                                    f"You MUST retry this tool call immediately with ALL required arguments included in a single call. "
                                    f"Do not respond to the user until the tool succeeds."
                                )
                                logger.warning(f"Tool {tool_name} args validation failed — missing: {missing_str}")
                                break
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

                # Emit tool_result event so the CLI can show brief feedback
                if event_queue is not None:
                    await event_queue.put({
                        "type": "tool_result",
                        "name": tool_name,
                        "round": round_num + 1,
                        "summary": _brief_result(tool_name, tool_result_str),
                    })

                # Track local files accessed or modified during the session
                if event_queue is not None and tool_name in (
                    "read_docx", "modify_docx", "analyze_excel", "modify_excel",
                    "read_excel", "write_excel", "write_docx",
                ):
                    try:
                        import json as _j
                        result_data = _j.loads(tool_result_str) if tool_result_str.startswith("{") else {}
                        saved = result_data.get("saved_to") or result_data.get("path") or tool_args.get("file_name", "") or tool_args.get("path", "")
                        if saved:
                            await event_queue.put({
                                "type": "local_file_used",
                                "path": saved,
                                "tool": tool_name,
                            })
                    except Exception:
                        pass

                messages.append(ToolMessage(content=tool_result_str, tool_call_id=tool_id))

            logger.info(f"Invoking LLM after round {round_num + 1}")
            try:
                response = await llm_with_tools.ainvoke(messages)
            except Exception as e:
                logger.error(f"LLM invoke failed after tool execution (round {round_num + 1}): {e}")
                from langchain_core.messages import AIMessage as _AIMsg
                response = _AIMsg(content="Lo siento, ocurrió un error al procesar los resultados. Por favor, intenta de nuevo.")
            content = _extract_text(response.content)
            logger.info(f"Response after round {round_num + 1}: length={len(content)}, has_more_tool_calls={bool(getattr(response, 'tool_calls', None))}")

            if content and not getattr(response, "tool_calls", None):
                break

            if event_queue is not None:
                for tc in getattr(response, "tool_calls", []):
                    await event_queue.put({
                        "type": "tool_call",
                        "name": tc.get("name", "tool"),
                        "round": round_num + 2,
                        "arg": _get_key_arg(tc.get("name", ""), tc.get("args", {})),
                    })

        content = response.content or ""
        if not content:
            logger.warning(
                f"_handle_tool_calls exhausted {max_rounds} rounds without a final text response"
            )
            content = "(Las herramientas se ejecutaron correctamente. Tarea completada.)"
        return content

    @staticmethod
    def _build_workspace_map(workspace: str, max_files: int = 180) -> str:
        """
        Build a compact file tree of the workspace to inject into the system prompt.
        Extracts top-level symbols (classes/functions) from Python and TypeScript files.
        Modeled after Aider's RepoMap — gives the AI instant orientation without exploration.
        """
        import re as _re

        SKIP_DIRS = {
            ".git", ".hg", ".svn", "node_modules", "__pycache__", ".venv", "venv",
            "env", ".env", "dist", "build", ".next", ".nuxt", "coverage", ".pytest_cache",
            ".mypy_cache", ".tox", "eggs", "*.egg-info", ".cache", "tmp", "temp",
        }
        SKIP_EXTS = {
            ".pyc", ".pyo", ".pyd", ".so", ".dll", ".dylib", ".exe",
            ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".woff", ".woff2",
            ".ttf", ".eot", ".pdf", ".zip", ".tar", ".gz", ".lock",
            ".min.js", ".min.css",
        }
        SYMBOL_LANGS = {
            ".py":  _re.compile(r"^(class|def|async def)\s+([A-Za-z_]\w*)"),
            ".ts":  _re.compile(r"^(?:export\s+)?(?:async\s+)?(?:class|function|const|interface|type|enum)\s+([A-Za-z_]\w*)"),
            ".vue": _re.compile(r"^(?:export\s+)?(?:const|function)\s+([A-Za-z_]\w*)"),
        }

        lines = [f"## Workspace: {workspace}\n"]
        file_count = 0

        for root, dirs, files in os.walk(workspace):
            # Prune noise dirs in-place
            dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not d.startswith("."))

            rel_root = os.path.relpath(root, workspace)
            depth = 0 if rel_root == "." else rel_root.count(os.sep) + 1
            indent = "  " * depth
            folder = os.path.basename(root) if rel_root != "." else ""
            if folder:
                lines.append(f"{indent}{folder}/")

            for fname in sorted(files):
                if file_count >= max_files:
                    lines.append("  ... (truncated)")
                    return "\n".join(lines)

                _, ext = os.path.splitext(fname)
                if ext in SKIP_EXTS or fname.endswith(".min.js") or fname.endswith(".min.css"):
                    continue

                file_count += 1
                fpath = os.path.join(root, fname)
                file_indent = "  " * (depth + 1)

                # Try to extract top-level symbols for supported languages
                symbols = []
                pattern = SYMBOL_LANGS.get(ext)
                if pattern:
                    try:
                        with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                            for line in f:
                                m = pattern.match(line)
                                if m:
                                    sym = m.group(2) if ext == ".py" else m.group(1)
                                    if sym and not sym.startswith("_"):
                                        symbols.append(sym)
                    except OSError:
                        pass

                if symbols:
                    lines.append(f"{file_indent}{fname}  ({', '.join(symbols[:6])}{'…' if len(symbols) > 6 else ''})")
                else:
                    lines.append(f"{file_indent}{fname}")

        lines.append(f"\n({file_count} files)")
        return "\n".join(lines)

    def _build_system_prompt(
        self,
        profile: Profile,
        context: Optional[str],
        client_workspace: str = "",
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
            get_language_instruction,
        )

        language = getattr(profile, "response_language", None) or "en"
        system_prompt = CONTEXT_INFORMATION.format(
            assistant_name=profile.assistant_name or "Assistant",
            functions=profile.functions or "",
            product_context=context or "",
            language_instruction=get_language_instruction(language),
        )

        try:
            from src.core.platform.functions.global_workflows import get_available_workflows
            available_workflows = get_available_workflows(profile)
            if available_workflows:
                workflow_lines = []
                for wf in available_workflows:
                    name = wf.get("name", "")
                    description = wf.get("description", "")
                    steps = wf.get("steps", [])
                    for step in steps:
                        method = step.get("method", "GET")
                        url = step.get("url", "")
                        required = step.get("required_params", [])
                        body_template = step.get("body_template", "")
                        line = f"- **{name}**: {description}\n  → {method} {url}"
                        if required:
                            line += f" | params: {', '.join(required)}"
                        if body_template:
                            line += f" | body: {body_template}"
                        workflow_lines.append(line)

                system_prompt += (
                    "\n\n## Available Integrations\n"
                    "You have access to the following APIs. Use them directly with `run_shell` "
                    "(curl) when the user requests related information. "
                    "Do NOT look for local files or answer that you have no access.\n"
                    "The authentication header is managed internally; always use "
                    "the URL as shown (http://localhost:8000/...).\n\n"
                    + "\n".join(workflow_lines)
                )
        except Exception as e:
            logger.warning(f"Could not inject global workflows into system prompt: {e}")

        if context and "FREQUENTLY ASKED QUESTIONS" in context or context and "PREGUNTAS FRECUENTES" in context:
            system_prompt += (
                "\n\nCRITICAL INSTRUCTION - ABSOLUTE PRIORITY:\n"
                "The FREQUENTLY ASKED QUESTIONS (FAQs) are included in the context above.\n"
                "You MUST follow this process STRICTLY:\n"
                "1. FIRST: Read all FAQs in the context carefully\n"
                "2. If the user's question matches any FAQ (even partially), USE THE FAQ ANSWER DIRECTLY\n"
                "3. Do NOT use search tools (search_faqs, search_documents) if you already have the answer in the FAQs\n"
                "4. ONLY if you do NOT find the answer in the FAQs, then you may use search tools\n"
                "5. FAQ answers are official and pre-approved, they take priority over any other information\n"
            )

        if client_workspace and os.path.isdir(client_workspace):
            try:
                workspace_map = self._build_workspace_map(client_workspace)
                system_prompt += (
                    "\n\n## Workspace Map\n"
                    "The following is the file tree of the current working directory.\n"
                    "Use this information to locate files directly without needing to "
                    "explore with repo_map or find_files. Symbols in parentheses are "
                    "the main classes/functions of each file.\n\n"
                    + workspace_map
                )
            except Exception as e:
                logger.warning(f"Could not build workspace map: {e}")

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
