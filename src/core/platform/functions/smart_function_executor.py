import json
import logging
import re
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

from src.core.platform.functions.workflow_executor import WorkflowExecutor
from src.core.platform.functions.global_workflows import get_available_workflows
from src.core.platform.config.service import ConfigurationService
from src.core.domain import Profile

logger = logging.getLogger(__name__)

_PARAM_COLLECTION_TTL_SECONDS = 30 * 60


@dataclass
class FunctionConfig:
    """Configuration for a single callable function or workflow."""

    type: str  # "simple" | "workflow"
    sequential: bool = False
    sequential_number: Optional[int] = None
    name: str = ""
    method: str = "GET"
    body: Optional[str] = None
    headers: str = ""
    url: str = ""
    keywords: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    param_descriptions: Dict[str, str] = field(default_factory=dict)
    response_field: Optional[str] = None
    description: str = ""
    body_mode: str = "template"  # "template" | "llm"
    body_prompt: Optional[str] = None
    required_body_params: List[str] = field(default_factory=list)
    response_default_message: Optional[str] = None
    # The workflow definition this config came from. Carried here so a run
    # never has to look it up in a registry shared with every other tenant.
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FunctionResult:
    """Result of a function execution carrying both the LLM response and an optional pre-message."""

    response: str
    default_message: Optional[str] = None


class SmartFunctionExecutor:
    """
    Analyzes user messages with an LLM to detect function intent, extracts
    parameters, and executes simple HTTP functions or multi-step workflows.

    Supports multi-turn parameter collection when parameters are missing.
    """

    def __init__(self, config_service: ConfigurationService):
        self.config_service = config_service
        self.workflow_executor = WorkflowExecutor(config_service)
        self.llm = ChatOpenAI(
            api_key=config_service.openai_config.api_key,
            base_url=config_service.openai_config.base_url,
            model=config_service.openai_config.model,
            temperature=0.1,
        )
        self._setup_prompt()
        self.function_params_storage: Dict[str, Dict[str, Dict[str, Any]]] = {}

    def _setup_prompt(self):
        """Build the intent-analysis prompt template."""
        current_date = datetime.now().strftime("%Y-%m-%d")

        system_message = f"""You are an AI assistant that analyzes user messages to determine if they match any available functions.

Your task is to:
1. Analyze the user's message
2. Check if it matches any function names, descriptions, keywords, or examples from the available list
3. If there is a match, identify which function and what parameters are needed
4. If no match, respond that no suitable function was found

Available functions: {{available_functions}}

IMPORTANT: Respond ONLY with valid JSON in this exact format:
{{{{
    "match_found": true/false,
    "function_name": "name_of_matched_function",
    "confidence": 0.0-1.0,
    "reasoning": "explanation of why this function matches",
    "missing_params": ["param1", "param2"],
    "extracted_params": {{{{"param1": "value1"}}}}
}}}}

CRITICAL: A parameter cannot be in both "missing_params" AND "extracted_params" simultaneously.
- Successfully extracted → put in "extracted_params" only
- Could not extract → put in "missing_params" only

ANALYSIS GUIDELINES:
- Look for exact matches in function names first
- Check if the user's message contains keywords or matches examples from the function
- Consider function descriptions
- Extract any parameter values you can directly from the message

DATE AND TIME EXTRACTION:
When extracting date/time parameters, convert to RFC3339 format: YYYY-MM-DDTHH:MM:SSZ
- If only a date is provided (no time), use 09:00:00 as default time
- Use 24-hour format
- Add "Z" suffix for UTC
- Current date reference: {current_date}

CRITICAL OUTPUT RULES:
- Respond ONLY with the JSON — no extra text before or after
- Use double quotes for all strings
- Use true/false (not "true"/"false") for booleans
- If no match is found, set match_found to false"""

        from langchain_core.prompts import ChatPromptTemplate
        self.intent_prompt = ChatPromptTemplate.from_messages(
            [("system", system_message), ("human", "User message: {{user_question}}")]
        )

    def _parse_functions_config(self, functions_string) -> List[FunctionConfig]:
        """Parse function configurations from a JSON string or list."""
        try:
            if isinstance(functions_string, str):
                functions_list = json.loads(functions_string)
            else:
                functions_list = functions_string

            if isinstance(functions_list, dict):
                functions_list = [functions_list]

            parsed = []
            for func in functions_list:
                config = FunctionConfig(
                    type=func.get("type", "simple"),
                    sequential=func.get("sequential", False),
                    sequential_number=func.get("sequential_number"),
                    name=func.get("name", ""),
                    method=func.get("method", "GET"),
                    body=func.get("body"),
                    headers=func.get("headers", ""),
                    url=func.get("url_template", func.get("url", "")),
                    keywords=func.get("keywords", []),
                    examples=func.get("examples", []),
                    param_descriptions=func.get("param_descriptions", {}),
                    response_field=func.get("response_field"),
                    description=func.get("description", ""),
                    body_mode=func.get("body_mode", "template"),
                    body_prompt=func.get("body_prompt"),
                    required_body_params=func.get("required_body_params", []),
                    response_default_message=func.get("response_default_message"),
                    raw=func if isinstance(func, dict) else {},
                )
                parsed.append(config)

            return parsed

        except Exception as e:
            logger.error(f"Error parsing functions config: {e}")
            return []

    def _get_all_available_functions(self, profile: Profile) -> List[FunctionConfig]:
        """Combine profile functions with active global workflows."""
        all_functions: List[FunctionConfig] = []

        if profile.functions:
            profile_functions = self._parse_functions_config(profile.functions)
            all_functions.extend(profile_functions)
            logger.info(f"Loaded {len(profile_functions)} functions from profile")

        try:
            global_workflows = get_available_workflows(profile)
            if global_workflows:
                for workflow in global_workflows:
                    all_functions.extend(self._parse_functions_config([workflow]))
                logger.info(f"Loaded {len(global_workflows)} global workflows")
        except Exception as e:
            logger.warning(f"Error loading global workflows: {e}")

        logger.info(f"Total available functions: {len(all_functions)}")
        return all_functions

    async def _analyze_user_intent(
        self,
        user_question: str,
        available_functions: List[FunctionConfig],
        chat_history: List[str] = None,
    ) -> Dict[str, Any]:
        """Use the LLM to detect which function the user is asking for."""
        try:
            functions_info = []
            for func in available_functions:
                info: Dict[str, Any] = {
                    "name": func.name,
                    "description": func.description or f"{func.type} — {func.url}",
                    "type": func.type,
                }
                if func.keywords:
                    info["keywords"] = func.keywords
                if func.examples:
                    info["examples"] = func.examples[:2]
                functions_info.append(info)

            history_context = ""
            if chat_history:
                recent = chat_history[-4:]
                history_context = (
                    "\n\nCONVERSATION HISTORY (recent messages):\n"
                    + "\n".join(recent)
                    + "\n\nUse the conversation history to resolve context-dependent references "
                    "(e.g. IDs mentioned in previous messages, confirmation responses, etc.)"
                )

            prompt = self.intent_prompt.format(
                available_functions=json.dumps(functions_info, indent=2),
                user_question=user_question,
            ) + history_context

            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            content = response.content.strip()

            start = content.find("{")
            end = content.rfind("}") + 1
            if start != -1 and end > start:
                analysis = json.loads(content[start:end])
                analysis.setdefault("match_found", False)
                return analysis

            logger.error(f"No valid JSON in AI response: {content}")
            return {"match_found": False, "reasoning": "No valid JSON in AI response"}

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error in AI response: {e}")
            return {"match_found": False, "reasoning": "Failed to parse AI response"}

        except Exception as e:
            logger.error(f"Error analyzing user intent: {e}")
            try:
                return self._fallback_intent_analysis(user_question, available_functions) or {
                    "match_found": False,
                    "reasoning": str(e),
                }
            except Exception:
                return {"match_found": False, "reasoning": str(e)}

    def _fallback_intent_analysis(
        self, user_question: str, available_functions: List[FunctionConfig]
    ) -> Optional[Dict[str, Any]]:
        """Keyword-based fallback when the LLM is unavailable."""
        lower = user_question.lower()

        for func in available_functions:
            if func.name.lower() in lower:
                return {
                    "match_found": True,
                    "function_name": func.name,
                    "confidence": 0.7,
                    "reasoning": f"Name match: {func.name}",
                    "missing_params": [],
                    "extracted_params": self._extract_generic_params(user_question),
                }
            for keyword in func.keywords:
                if keyword.lower() in lower:
                    return {
                        "match_found": True,
                        "function_name": func.name,
                        "confidence": 0.6,
                        "reasoning": f"Keyword match: {keyword}",
                        "missing_params": [],
                        "extracted_params": self._extract_generic_params(user_question),
                    }

        return None

    def _extract_url_params(self, url: str) -> List[str]:
        """Return all {param} placeholders found in a URL template."""
        return re.findall(r"\{(\w+)\}", url)

    def _extract_generic_params(self, text: str) -> Dict[str, str]:
        """
        Extract format-driven parameters that are unambiguous regardless of domain:
        - Decimal coordinate pairs  (lat, lon)
        - Email addresses
        - Phone numbers
        """
        extracted: Dict[str, str] = {}

        # Coordinate pair (e.g. "-34.61, -58.37")
        coord = re.search(r"(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)", text)
        if coord:
            extracted["lat"] = coord.group(1)
            extracted["lon"] = coord.group(2)

        # Email
        email = re.search(r"\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b", text)
        if email:
            extracted["email"] = email.group(1)

        # Phone (E.164-ish)
        phone = re.search(r"(\+?\d{1,3}[\s-]?\d{3,4}[\s-]?\d{6,7})", text)
        if phone:
            extracted["phone"] = phone.group(1).replace(" ", "").replace("-", "")

        return extracted

    async def _request_missing_params(
        self, missing_params: List[str], function_name: str, user_message: str = ""
    ) -> Dict[str, Any]:
        """Ask the LLM to generate a natural request for missing parameters."""
        try:
            prompt = (
                f"The user sent this message: \"{user_message}\"\n\n"
                f"To complete the '{function_name}' action, the following parameters are still needed: "
                f"{', '.join(missing_params)}.\n\n"
                "Ask the user to provide all missing parameters in a single, natural, "
                "conversational message. Respond in the SAME language the user used."
            )
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            return {
                "message": response.content,
                "next_param": missing_params[0] if missing_params else None,
                "remaining_params": missing_params[1:] if len(missing_params) > 1 else [],
            }
        except Exception as e:
            logger.error(f"Error requesting missing params: {e}")
            return {
                "message": f"Necesito los siguientes datos para continuar: {', '.join(missing_params)}.",
                "next_param": missing_params[0] if missing_params else None,
                "remaining_params": missing_params[1:] if len(missing_params) > 1 else [],
            }

    def _build_url(self, url_template: str, params: Dict[str, str]) -> str:
        for param, value in params.items():
            url_template = url_template.replace(f"{{{param}}}", str(value))
        return url_template

    async def _build_body_with_llm(
        self,
        function_config: "FunctionConfig",
        user_message: str,
        params: Dict[str, Any],
        chat_history: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Use the LLM to build a complex JSON body (e.g. a shopping cart) from
        the user message, the body_prompt catalog/instructions, and already-
        extracted params.  Returns a dict/list or None on failure.
        """
        try:
            history_context = ""
            if chat_history:
                recent = chat_history[-6:]  # last 3 exchanges
                history_context = "Recent conversation:\n" + "\n".join(recent) + "\n\n"

            prompt = (
                f"{function_config.body_prompt}\n\n"
                f"{history_context}"
                f"User request: \"{user_message}\"\n"
                f"Already extracted params: {json.dumps(params, ensure_ascii=False)}\n\n"
                "Build the complete JSON body for the API call based on the user's request "
                "and the instructions above.\n"
                "CRITICAL: Respond ONLY with valid JSON — no extra text, no markdown fences."
            )
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            content = response.content.strip()

            content = re.sub(r"^```(?:json)?\s*", "", content)
            content = re.sub(r"\s*```$", "", content)
            content = content.strip()

            for start_char, end_char in [("{", "}"), ("[", "]")]:
                start = content.find(start_char)
                end = content.rfind(end_char) + 1
                if start != -1 and end > start:
                    return json.loads(content[start:end])

            logger.error(f"_build_body_with_llm: no valid JSON in response: {content[:200]}")
            return None

        except Exception as e:
            logger.error(f"Error building body with LLM: {e}", exc_info=True)
            return None

    async def _execute_simple_function(
        self,
        function_config: FunctionConfig,
        params: Dict[str, str],
        prebuilt_body: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute a simple HTTP function."""
        try:
            import aiohttp

            url = self._build_url(function_config.url, params)
            headers: Dict[str, str] = {}
            if function_config.headers:
                try:
                    raw_headers = json.loads(function_config.headers) if isinstance(function_config.headers, str) else function_config.headers
                    for k, v in raw_headers.items():
                        headers[k] = self._build_url(str(v), params)
                except Exception:
                    pass

            body = None
            if prebuilt_body is not None:
                body = prebuilt_body
            elif function_config.body:
                try:
                    raw_body = function_config.body if isinstance(function_config.body, str) else json.dumps(function_config.body)
                    body = json.loads(self._build_url(raw_body, params))
                except Exception:
                    pass

            kwargs: Dict[str, Any] = {}
            if body and function_config.method.upper() not in ("GET", "DELETE"):
                kwargs["json"] = body

            logger.info(f"[{function_config.name}] {function_config.method} {url}")
            logger.info(f"[{function_config.name}] body: {json.dumps(body, ensure_ascii=False) if body else 'None'}")

            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method=function_config.method,
                    url=url,
                    headers=headers,
                    timeout=timeout,
                    **kwargs,
                ) as response:
                    response_text = await response.text()
                    logger.info(f"[{function_config.name}] response {response.status}: {response_text[:300]}")
                    response.raise_for_status()
                    result = json.loads(response_text)

            return {"success": True, "result": result, "url_executed": url, "type": "simple_function"}

        except Exception as e:
            logger.error(f"Error executing simple function '{function_config.name}': {e}")
            return {"success": False, "error": str(e), "type": "simple_function"}

    async def _execute_workflow(
        self,
        function_config: FunctionConfig,
        params: Dict[str, str],
        profile=None,
        auth_token: str = None,
    ) -> Dict[str, Any]:
        """Execute a registered workflow."""
        try:
            result = await self.workflow_executor.execute_workflow(
                workflow=function_config.raw,
                input_params=params,
                profile=profile,
                auth_token=auth_token,
            )
            return {"success": True, "result": result, "type": "workflow"}
        except Exception as e:
            logger.error(f"Error executing workflow '{function_config.name}': {e}")
            return {"success": False, "error": str(e), "type": "workflow"}

    def _extract_response_field(
        self, execution_result: Dict[str, Any], function_type: str, field_name: str
    ) -> Optional[str]:
        """Extract a specific field from the execution result, returns None if not found."""
        result_data = execution_result.get("result", {})

        if function_type == "workflow":
            final_result = result_data.get("final_result", {})
            if isinstance(final_result, dict) and field_name in final_result:
                return str(final_result[field_name])
            context = result_data.get("context", {})
            if isinstance(context, dict) and field_name in context:
                return str(context[field_name])
        else:
            if isinstance(result_data, dict) and field_name in result_data:
                return str(result_data[field_name])

        return None

    async def _generate_friendly_response(
        self,
        function_name: str,
        function_type: str,
        execution_result: Dict[str, Any],
        params: Dict[str, str],
        user_message: str = "",
        chat_history: List[str] = None,
    ) -> str:
        """Ask the LLM to turn a raw execution result into a user-friendly message."""
        try:
            result_data = execution_result.get("result", {})

            if function_type == "workflow":
                steps_executed = result_data.get("steps_executed", [])
                final_result = result_data.get("final_result", {})
                has_error = not steps_executed

                context_str = (
                    f"Type: Workflow\n"
                    f"Name: {function_name}\n"
                    f"Steps executed: {', '.join(steps_executed) if steps_executed else 'NONE'}\n"
                    f"Step results: {json.dumps(final_result, indent=2, ensure_ascii=False)}\n"
                    f"Parameters used: {json.dumps(params, indent=2, ensure_ascii=False)}\n"
                    f"Error detected: {'YES' if has_error else 'NO'}"
                )
            else:
                context_str = (
                    f"Type: Simple function\n"
                    f"Name: {function_name}\n"
                    f"Parameters used: {json.dumps(params, indent=2, ensure_ascii=False)}\n"
                    f"Result: {json.dumps(result_data, indent=2, ensure_ascii=False)}"
                )

            history_str = ""
            if chat_history:
                recent = chat_history[-4:]
                history_str = (
                    f"\nRecent conversation (for tone/context):\n"
                    + "\n".join(recent)
                    + "\n"
                )

            prompt = (
                f"You are an assistant generating natural, friendly responses based on the "
                f"results of technical operations.\n\n"
                f"The user sent: \"{user_message}\"\n"
                f"Respond in the SAME language the user used.\n"
                f"{history_str}\n"
                f"Operation executed:\n{context_str}\n\n"
                f"Instructions:\n"
                f"1. If 'Error detected: YES' or no steps were executed, inform the user about the error clearly\n"
                f"2. If successful, confirm success and include the most relevant details\n"
                f"3. Be concise and conversational — avoid raw JSON or technical data\n"
                f"4. Keep your response coherent with the tone of the recent conversation\n\n"
                f"Generate the response now:"
            )

            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            return response.content.strip()

        except Exception as e:
            logger.error(f"Error generating friendly response: {e}", exc_info=True)
            return f"✅ Listo."

    async def _generate_friendly_error(
        self, function_name: str, error_detail: str, user_message: str = ""
    ) -> str:
        """Ask the LLM to turn a raw error into a user-friendly apology message."""
        try:
            prompt = (
                "You are an assistant that communicates technical errors in a friendly, "
                "reassuring way.\n\n"
                f"The user sent: \"{user_message}\"\n"
                f"Respond in the SAME language the user used.\n\n"
                f"A background operation called '{function_name}' failed with this technical error:\n"
                f"{error_detail}\n\n"
                "Instructions:\n"
                "1. Apologize briefly and let the user know the action could not be completed\n"
                "2. Do NOT expose raw error messages, stack traces, or technical details\n"
                "3. If the error suggests a fixable issue (e.g. missing data), hint at what the user could try\n"
                "4. Be concise — 1 or 2 sentences max\n\n"
                "Generate the response now:"
            )
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            return response.content.strip()
        except Exception:
            return "Disculpá, no pude completar la acción. Por favor intentá de nuevo."

    async def execute_function(
        self,
        user_message: str,
        profile: Profile,
        chat_history: List[str] = None,
        auth_token: str = None,
    ) -> Optional[FunctionResult]:
        """Analyze the user message, find a matching function, and execute it."""
        try:
            available_functions = self._get_all_available_functions(profile)
            if not available_functions:
                return FunctionResult(response="No functions are configured for this profile.")

            user_id = profile.user_id or "default_user"

            ongoing_function = self._detect_ongoing_function(user_id)
            if ongoing_function:
                return await self._process_ongoing_function(
                    user_id, ongoing_function, user_message, available_functions,
                    profile=profile, auth_token=auth_token, chat_history=chat_history,
                )

            intent = await self._analyze_user_intent(user_message, available_functions, chat_history)

            if not isinstance(intent, dict) or not intent.get("match_found", False):
                return None

            matched_name = intent.get("function_name")
            matched_function = next((f for f in available_functions if f.name == matched_name), None)
            if not matched_function:
                return FunctionResult(response=f"Error: function '{matched_name}' not found in configuration.")

            missing_params: List[str] = intent.get("missing_params", [])
            extracted_params: Dict[str, Any] = intent.get("extracted_params", {})
            stored_params = self._get_stored_params(user_id, matched_name)
            all_params = {**stored_params, **extracted_params}

            if matched_function.body_mode == "llm" and matched_function.required_body_params:
                missing_body = [p for p in matched_function.required_body_params if p not in all_params]
                if missing_body:
                    missing_params = list(set(missing_params + missing_body))

            if missing_params:
                if extracted_params:
                    self._store_params(user_id, matched_name, extracted_params)
                self._store_params(user_id, matched_name, {"__trigger_message__": user_message})
                param_request = await self._request_missing_params(missing_params, matched_name, user_message)
                return FunctionResult(response=param_request["message"])

            clean_params = self._strip_metadata(all_params)

            if matched_function.type == "simple":
                prebuilt_body = None
                if matched_function.body_mode == "llm" and matched_function.body_prompt:
                    prebuilt_body = await self._build_body_with_llm(
                        matched_function, user_message, clean_params, chat_history
                    )
                result = await self._execute_simple_function(matched_function, clean_params, prebuilt_body)
            elif matched_function.type == "workflow":
                result = await self._execute_workflow(matched_function, clean_params, profile, auth_token)
            else:
                return FunctionResult(response=f"Unsupported function type: {matched_function.type}")

            if not result.get("success", False):
                error_response = await self._generate_friendly_error(matched_name, result.get("error", "Unknown error"), user_message)
                return FunctionResult(response=error_response)

            if matched_function.response_field:
                extracted = self._extract_response_field(result, matched_function.type, matched_function.response_field)
                if extracted is not None:
                    return FunctionResult(
                        response=extracted,
                        default_message=matched_function.response_default_message,
                    )

            response_text = await self._generate_friendly_response(
                matched_name, matched_function.type, result, all_params, user_message, chat_history
            )
            return FunctionResult(
                response=response_text,
                default_message=matched_function.response_default_message,
            )

        except Exception as e:
            logger.error(f"Error in SmartFunctionExecutor: {e}", exc_info=True)
            error_response = await self._generate_friendly_error("request", str(e), user_message)
            return FunctionResult(response=error_response)

    def _detect_ongoing_function(self, user_id: str) -> Optional[str]:
        """Return the name of the function currently awaiting parameters, or None."""
        self._expire_stale_params(user_id)
        user_storage = self.function_params_storage.get(user_id, {})
        for function_name, params in user_storage.items():
            if any(key != "__updated_at" for key in params):
                return function_name
        return None

    async def _process_ongoing_function(
        self,
        user_id: str,
        function_name: str,
        user_message: str,
        available_functions: List[FunctionConfig],
        profile=None,
        auth_token: str = None,
        chat_history: List[str] = None,
    ) -> FunctionResult:
        """Continue collecting parameters for a function already in progress."""
        try:
            matched_function = next((f for f in available_functions if f.name == function_name), None)
            if not matched_function:
                return FunctionResult(response=f"Error: function '{function_name}' not found.")

            stored_params = self._get_stored_params(user_id, function_name)
            new_params = self._extract_generic_params(user_message)

            if matched_function.body_mode == "llm" and matched_function.required_body_params:
                required_params = matched_function.required_body_params
            elif matched_function.type == "workflow" and matched_function.raw:
                required_params = matched_function.raw.get("input_params", [])
            else:
                required_params = self._extract_url_params(matched_function.url)

            all_params = {**stored_params, **new_params}

            missing = [p for p in required_params if p not in all_params]
            if missing and not new_params:
                all_params[missing[0]] = user_message.strip()
                new_params[missing[0]] = user_message.strip()
                missing = missing[1:]

            if new_params:
                self._store_params(user_id, function_name, new_params)

            missing = [p for p in required_params if p not in all_params]
            if missing:
                param_request = await self._request_missing_params(missing, function_name, user_message)
                return FunctionResult(response=param_request["message"])

            trigger_message = all_params.get("__trigger_message__", user_message)
            clean_params = self._strip_metadata(all_params)
            if matched_function.type == "simple":
                prebuilt_body = None
                if matched_function.body_mode == "llm" and matched_function.body_prompt:
                    prebuilt_body = await self._build_body_with_llm(
                        matched_function, trigger_message, clean_params, chat_history
                    )
                result = await self._execute_simple_function(matched_function, clean_params, prebuilt_body)
            elif matched_function.type == "workflow":
                result = await self._execute_workflow(matched_function, clean_params, profile, auth_token)
            else:
                return FunctionResult(response=f"Unsupported function type: {matched_function.type}")

            if result.get("success", False):
                self._clear_params(user_id, function_name)
                if matched_function.response_field:
                    extracted = self._extract_response_field(result, matched_function.type, matched_function.response_field)
                    if extracted is not None:
                        return FunctionResult(
                            response=extracted,
                            default_message=matched_function.response_default_message,
                        )
                response_text = await self._generate_friendly_response(
                    function_name, matched_function.type, result, all_params, trigger_message, chat_history
                )
                return FunctionResult(
                    response=response_text,
                    default_message=matched_function.response_default_message,
                )
            else:
                self._clear_params(user_id, function_name)
                error_response = await self._generate_friendly_error(function_name, result.get("error", "Unknown error"), user_message)
                return FunctionResult(response=error_response)

        except Exception as e:
            self._clear_params(user_id, function_name)
            logger.error(f"Error processing ongoing function: {e}", exc_info=True)
            error_response = await self._generate_friendly_error(function_name, str(e), user_message)
            return FunctionResult(response=error_response)

    def _store_params(self, user_id: str, function_name: str, params: Dict[str, Any]):
        stored = self.function_params_storage.setdefault(user_id, {}).setdefault(function_name, {})
        stored.update(params)
        stored["__updated_at"] = time.time()

    def _get_stored_params(self, user_id: str, function_name: str) -> Dict[str, Any]:
        params = self.function_params_storage.get(user_id, {}).get(function_name, {}).copy()
        params.pop("__updated_at", None)
        return params

    def _clear_params(self, user_id: str, function_name: str):
        try:
            del self.function_params_storage[user_id][function_name]
        except KeyError:
            pass

    def _expire_stale_params(self, user_id: str) -> None:
        """Drop half-collected parameters the user walked away from.

        Without this, an abandoned booking from weeks ago still counts as an
        ongoing function and hijacks the next unrelated message.
        """
        user_storage = self.function_params_storage.get(user_id)
        if not user_storage:
            return
        cutoff = time.time() - _PARAM_COLLECTION_TTL_SECONDS
        for function_name in [
            name for name, params in user_storage.items()
            if params.get("__updated_at", 0) < cutoff
        ]:
            logger.info(f"Expiring stale parameters for '{function_name}' (user {user_id})")
            del user_storage[function_name]
        if not user_storage:
            del self.function_params_storage[user_id]

    @staticmethod
    def _strip_metadata(params: Dict[str, Any]) -> Dict[str, Any]:
        """Remove internal metadata keys (prefixed with '__') before sending to a function."""
        return {k: v for k, v in params.items() if not k.startswith("__")}

    def get_available_functions(self, profile: Profile) -> List[Dict[str, Any]]:
        """Return a summary of all functions available for a given profile."""
        try:
            if not profile.functions:
                return []
            return [
                {
                    "name": f.name,
                    "type": f.type,
                    "sequential": f.sequential,
                    "sequential_number": f.sequential_number,
                    "method": f.method,
                    "url": f.url,
                }
                for f in self._parse_functions_config(profile.functions)
            ]
        except Exception as e:
            logger.error(f"Error getting available functions: {e}")
            return []
