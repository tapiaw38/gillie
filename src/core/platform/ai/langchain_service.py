"""
LangChain Service

Owns everything around one LLM turn — provider selection, prompt assembly,
concurrency, circuit breaking — and hands the turn itself to the LangGraph
agent loop in :mod:`src.core.platform.ai.graph`.

Both entry points run that same graph. ``generate_response`` waits for the
final answer; ``generate_response_stream`` yields it as it arrives and can
pause mid-run to ask the user to approve a tool call.
"""

import asyncio
import logging
import os
import uuid
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.errors import GraphRecursionError
from langgraph.types import Command


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
    resolve_profile as _resolve_profile,
    PromptProfile as _PromptProfile,
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
from src.core.platform.ai.graph import (
    build_agent_graph,
    emit_event as _write_event,
    final_text,
    missing_file_urls,
)
from src.core.platform.ai.tools.approval_manager import create_pending, take_decision
from .tools.models import create_langchain_tools
from .memory.manager import ConversationMemoryManager
from .checkpointer import mongo_checkpointer

logger = logging.getLogger(__name__)


def schema_tokens(tools: list) -> int:
    """Rough token cost of sending these tool schemas once.

    Approximated at 4 chars per token — good enough to compare two tool sets,
    which is all this is used for.
    """
    from langchain_core.utils.function_calling import convert_to_openai_tool
    import json as _json

    try:
        return sum(len(_json.dumps(convert_to_openai_tool(t))) for t in tools) // 4
    except Exception:
        return 0


def _log_routing_saving(before: list, after: list) -> None:
    """Record what routing actually saved, so the trade stays measurable.

    The saving is per LLM call, and a turn makes one call per tool round, so
    the real figure for a turn is this multiplied by the number of rounds.
    """
    if len(after) >= len(before):
        return
    kept, full = schema_tokens(after), schema_tokens(before)
    logger.info(
        "tool_routing",
        extra={
            "tools_before": len(before),
            "tools_after": len(after),
            "tokens_before": full,
            "tokens_after": kept,
            "tokens_saved_per_call": full - kept,
        },
    )


def _pending_approval(snapshot) -> Optional[dict]:
    """The approval a suspended run is waiting on, or None if it finished.

    Only the first is returned: the graph runs one tool per step, so there is
    never more than one outstanding request.
    """
    for task in getattr(snapshot, "tasks", ()) or ():
        for interruption in getattr(task, "interrupts", ()) or ():
            value = interruption.value
            if isinstance(value, dict):
                return value
    return None


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
        brain=None,
        avatar_mcp=None,
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
        self.brain = brain
        self.avatar_mcp = avatar_mcp

        self.llm = _build_llm(
            model=self.config.model,
            api_key=self.config.api_key,
            base_url=self.config.base_url if hasattr(self.config, 'base_url') and self.config.base_url else None,
            auth_type=getattr(self.config, 'auth_type', 'api_key'),
        )


        self.memory_manager = ConversationMemoryManager(max_messages=20)
        self.checkpointer = mongo_checkpointer(config_service)

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
        self.config.model = model
        self.config.base_url = base_url
        self.config.api_key = api_key
        self.config.auth_type = auth_type
        self.llm = _build_llm(model=model, api_key=api_key, base_url=base_url, auth_type=auth_type)
        logger.info(f"LangChainService LLM reloaded: model={model}")

    def _get_profile(self) -> _PromptProfile:
        """Resolve PromptProfile based on the current provider URL."""
        base_url = getattr(self.config, "base_url", "") or ""
        model = getattr(self.config, "model", "") or ""
        provider_name = getattr(self.config, "provider_name", "") or ""
        return _resolve_profile(base_url, model, provider_name)

    async def _route_tools(self, user_message: str, all_tools: list) -> list:
        """For Ollama: run a fast routing call to select only relevant tool groups."""
        routed = await _route_tools_ollama(self.llm, user_message, all_tools)
        # The avatar is local runtime control, not an Ollama tool category.
        avatar_tools = [tool for tool in all_tools if tool.name.startswith("avatar_")]
        routed_names = {tool.name for tool in routed}
        return routed + [tool for tool in avatar_tools if tool.name not in routed_names]

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

    def _prepare_run(
        self,
        question: str,
        context: Optional[str],
        previous_messages: List[Dict[str, Any]],
        profile: Profile,
        use_tools: bool,
        client_workspace: str,
        approvals_enabled: bool = False,
        plan_mode: bool = False,
        auth_token: Optional[str] = None,
        shell_output_callback=None,
    ):
        """Assemble everything one agent run needs: prompt, history, tools, LLM."""
        prompt_profile = self._get_profile()
        system_prompt = self._build_system_prompt(
            profile, context, client_workspace, prompt_profile
        )
        messages = self._convert_messages_to_langchain(
            previous_messages=previous_messages,
            system_prompt=system_prompt,
            current_question=question,
        )
        messages = self.memory_manager.optimize_message_history(
            messages,
            system_prompt=system_prompt,
            max_messages=prompt_profile.max_history_messages,
            max_chars=prompt_profile.max_context_chars,
        )
        if not use_tools:
            logger.debug("No tools enabled")
            return prompt_profile, messages, []

        tools = create_langchain_tools(
            self.openai_integration,
            profile,
            skill_manager=self.skill_manager,
            store_service=self.store_service,
            job_usecases=self.job_usecases,
            shell_output_callback=shell_output_callback,
            client_workspace=client_workspace,
            approvals_enabled=approvals_enabled,
            plan_mode=plan_mode,
            brain=self.brain,
            avatar_mcp=self.avatar_mcp,
            auth_token=auth_token,
        )
        return prompt_profile, messages, tools

    async def _bind_tools(self, question: str, tools: list):
        """Narrow the tool set to what this turn needs, then bind it.

        Routing used to run only for local models, which framed it as a
        context-window workaround. It is really a cost control: the schemas go
        out again on every call of a turn, so a 30-round turn pays for the full
        catalogue thirty times over. Hosted models have the room, not the
        budget.

        Set GILLIE_TOOL_ROUTING=off to send everything, e.g. to check whether a
        misrouted turn is the router's fault.
        """
        if not tools:
            return self.llm, []

        if os.getenv("GILLIE_TOOL_ROUTING", "on").lower() not in ("off", "0", "false"):
            before = tools
            tools = await self._route_tools(question, tools)
            _log_routing_saving(before, tools)

        logger.debug(f"Bound {len(tools)} tools to LLM")
        return self.llm.bind_tools(tools), tools

    @staticmethod
    def _run_config(thread_id: str, max_tool_rounds: int) -> Dict[str, Any]:
        """Graph config for one turn.

        The recursion limit stands in for the old max-rounds counter: a round
        is one model step plus one tool step, plus the final model step that
        produces the answer.
        """
        return {
            "configurable": {"thread_id": thread_id},
            "recursion_limit": max(4, 2 * max_tool_rounds + 2),
        }

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
        Generate a complete AI response, running tools to completion first.

        Approvals are off on this path: it serves callers with no one watching
        (WhatsApp, cron, the HTTP API), where pausing for a human would hang
        the request until it times out.

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
                prompt_profile, messages, tools = self._prepare_run(
                    question=question,
                    context=context,
                    previous_messages=previous_messages,
                    profile=profile,
                    use_tools=use_tools,
                    client_workspace=client_workspace,
                )
                llm_with_tools, tools = await self._bind_tools(question, tools)

                logger.info(
                    f"Generating response for user {profile.user_id} "
                    f"[profile={prompt_profile.name}]"
                )
                graph = build_agent_graph(llm_with_tools, tools, checkpointer=self.checkpointer)
                config = self._run_config(
                    self.memory_manager.create_thread_id(conversation_id, profile.user_id),
                    prompt_profile.max_tool_rounds,
                )

                try:
                    state = await graph.ainvoke(
                        {"messages": messages, "file_urls": {}}, config
                    )
                except GraphRecursionError:
                    logger.warning(
                        f"Agent hit the {prompt_profile.max_tool_rounds}-round limit; "
                        f"answering from the work done so far"
                    )
                    state = (await graph.aget_state(config)).values
                finally:
                    await self._discard_checkpoints(config)

                response_text = final_text(state, _extract_text)
                self._record_success()
                logger.info("Response generated successfully")
                return response_text

            except Exception as e:
                self._record_failure()
                logger.error(f"Error generating response: {e}")
                raise

    async def _discard_checkpoints(self, config: Dict[str, Any]) -> None:
        """Drop a finished run's checkpoints. Never fails the turn over it."""
        try:
            await self.checkpointer.adelete_thread(config["configurable"]["thread_id"])
        except Exception as e:
            logger.warning(f"Could not delete agent checkpoints: {e}")

    async def generate_response_stream(
        self,
        question: str,
        context: Optional[str],
        previous_messages: List[Dict[str, Any]],
        profile: Profile,
        conversation_id: str,
        use_tools: bool = True,
        client_workspace: str = "",
        plan_mode: bool = False,
        auth_token: Optional[str] = None,
        approval_timeout: float = 300.0,
        run_id: Optional[str] = None,
    ):
        """
        Stream the response as it is produced.

        Yields plain ``str`` tokens for answer text, and dicts for everything
        the CLI renders alongside it: ``tool_call``, ``tool_result``,
        ``shell_output``, ``local_file_used`` and ``approval_request``.

        A tool that needs approval suspends the whole graph. This method emits
        the ``approval_request``, waits for ``POST /conversation/tool/approve``
        to answer it, then resumes the run exactly where it stopped.
        """
        if self._is_circuit_open():
            raise Exception("AI service temporarily unavailable (circuit breaker)")

        async with self.semaphore:
            try:
                async def emit_shell_line(line: str) -> None:
                    _write_event({"type": "shell_output", "line": line})

                prompt_profile, messages, tools = self._prepare_run(
                    question=question,
                    context=context,
                    previous_messages=previous_messages,
                    profile=profile,
                    use_tools=use_tools,
                    client_workspace=client_workspace,
                    approvals_enabled=True,
                    plan_mode=plan_mode,
                    auth_token=auth_token,
                    shell_output_callback=emit_shell_line,
                )
                llm_with_tools, tools = await self._bind_tools(question, tools)

                logger.info(
                    f"Stream: profile={prompt_profile.name}, "
                    f"max_rounds={prompt_profile.max_tool_rounds}"
                )
                graph = build_agent_graph(
                    llm_with_tools, tools, checkpointer=self.checkpointer, approvals_enabled=True
                )
                thread_id = run_id or self.memory_manager.create_thread_id(conversation_id, profile.user_id)
                config = self._run_config(
                    thread_id,
                    prompt_profile.max_tool_rounds,
                )

                streamed = ""
                yield {"type": "agent_run", "run_id": thread_id}
                payload: Any = {"messages": messages, "file_urls": {}}
                exhausted = False

                request = (
                    _pending_approval(await graph.aget_state(config)) if run_id else None
                )

                while True:
                    if request is not None:
                        request_id = str(uuid.uuid4())
                        answered = await create_pending(request_id, thread_id, request)
                        yield {
                            "type": "approval_request",
                            "request_id": request_id,
                            "tool": request.get("tool", "unknown"),
                            "file": request.get("file", ""),
                            "diff": request.get("diff", ""),
                            "risk": request.get("risk", "unknown"),
                            "always_ask": bool(request.get("always_ask", False)),
                        }
                        try:
                            await asyncio.wait_for(
                                answered.wait(), timeout=approval_timeout
                            )
                        except asyncio.TimeoutError:
                            logger.warning(
                                f"Approval request {request_id} timed out after "
                                f"{approval_timeout}s — rejecting"
                            )
                        payload = Command(resume=await take_decision(request_id))

                    suppressed: set = set()
                    try:
                        async for mode, item in graph.astream(
                            payload, config, stream_mode=["messages", "custom"]
                        ):
                            if mode == "custom":
                                yield item
                                continue
                            chunk, metadata = item
                            if metadata.get("langgraph_node") != "model":
                                continue
                            if getattr(chunk, "tool_call_chunks", None):
                                suppressed.add(chunk.id)
                            if chunk.id in suppressed or not chunk.content:
                                continue
                            text = _extract_text(chunk.content)
                            if text:
                                streamed += text
                                yield text
                    except GraphRecursionError:
                        logger.warning(
                            f"Agent hit the {prompt_profile.max_tool_rounds}-round limit "
                            f"mid-stream; answering from the work done so far"
                        )
                        exhausted = True

                    snapshot = await graph.aget_state(config)
                    request = None if exhausted else _pending_approval(snapshot)
                    if request is None:
                        break

                state = (await graph.aget_state(config)).values
                if not streamed.strip():
                    text = final_text(state, _extract_text)
                    streamed = text
                    yield text
                else:
                    for url in missing_file_urls(state, streamed):
                        logger.info(f"Appending missing file URL to response: {url}")
                        yield f"\n{url}"

                self._record_success()
                await self._discard_checkpoints(config)

            except Exception as e:
                self._record_failure()
                logger.error(f"Error in generate_response_stream: {e}")
                raise

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
        prompt_profile: "_PromptProfile | None" = None,
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
            EMBODIMENT_INSTRUCTION,
            get_language_instruction,
        )

        from src.core.platform.functions.global_workflows import redact_functions_for_prompt

        language = getattr(profile, "response_language", None) or "en"
        system_prompt = CONTEXT_INFORMATION.format(
            assistant_name=profile.assistant_name or "Assistant",
            functions=redact_functions_for_prompt(profile.functions),
            product_context=context or "",
            language_instruction=get_language_instruction(language),
        )

        try:
            from src.core.platform.functions.global_workflows import get_available_workflows
            available_workflows = get_available_workflows(profile)
            if available_workflows:
                # Name and inputs only: the model calls run_workflow, so the
                # per-step endpoints are the engine's business, not the prompt's.
                workflow_lines = []
                for wf in available_workflows:
                    line = f"- **{wf.get('name', '')}**: {wf.get('description', '')}"
                    required = wf.get("input_params") or []
                    optional = wf.get("optional_params") or []
                    if required:
                        line += f"\n  params: {', '.join(required)}"
                    if optional:
                        line += f"\n  optional: {', '.join(optional)}"
                    workflow_lines.append(line)

                system_prompt += (
                    "\n\n## Available Integrations\n"
                    "Run these with the `run_workflow` tool, passing the workflow name and "
                    "its parameters. It handles authentication, parameter substitution and "
                    "the chaining between steps. Do NOT call these endpoints with curl or "
                    "fetch_url, and do NOT answer that you have no access.\n\n"
                    + "\n".join(workflow_lines)
                )
        except Exception as e:
            logger.warning(f"Could not inject global workflows into system prompt: {e}")

        if self.avatar_mcp is not None and self.avatar_mcp.avatar_available():
            system_prompt += EMBODIMENT_INSTRUCTION.format(
                assistant_name=profile.assistant_name or "Assistant",
            )

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

        if prompt_profile and prompt_profile.short_answers:
            system_prompt += (
                "\n\nIMPORTANT: Keep answers short and direct. "
                "Prefer concrete results over long explanations. "
                "Do not repeat the user's request. "
                "Avoid unnecessary preamble."
            )

        max_workspace_files = prompt_profile.max_workspace_files if prompt_profile else 180
        if max_workspace_files > 0 and client_workspace and os.path.isdir(client_workspace):
            try:
                workspace_map = self._build_workspace_map(client_workspace, max_files=max_workspace_files)
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
            "max_history_messages": self.memory_manager.max_messages,
        }
