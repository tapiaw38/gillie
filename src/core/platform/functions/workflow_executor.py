import asyncio
import ipaddress
import json
import logging
import os
import re
from datetime import datetime
from typing import Dict, Any, List, Optional
from urllib.parse import quote, urlparse

import aiohttp

logger = logging.getLogger(__name__)

_DEFAULT_STEP_TIMEOUT = 30.0

# Workflow URLs come from user-authored config, so the server is being told to
# make a request on the user's behalf. Loopback stays reachable because the
# built-in workflows call this very API, but the cloud metadata endpoint and
# the RFC1918 ranges are off limits unless an operator opts in.
_ALLOW_PRIVATE_URLS = os.getenv("GILLIE_WORKFLOW_ALLOW_PRIVATE_URLS", "").lower() in ("1", "true", "yes")

_PLACEHOLDER = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")

_DATE_KEYWORDS = (
    "check_in", "check_out", "fecha", "date", "inicio", "fin",
    "start_date", "end_date", "booking_date", "reservation_date",
)


class WorkflowError(Exception):
    """A workflow step failed and the run cannot meaningfully continue."""


class WorkflowExecutor:
    """Executes multi-step workflows sequentially, passing context between steps.

    Holds no per-execution state: one instance is shared by every request, so
    the execution context, the auth token and the workflow definition all
    travel as arguments. Keeping them on `self` leaked one tenant's token into
    another tenant's concurrent run.
    """

    def __init__(self, config_service=None):
        self.config_service = config_service

    async def execute_workflow(
        self,
        workflow: Dict[str, Any],
        input_params: Dict[str, Any],
        profile=None,
        auth_token: str = None,
    ) -> Dict[str, Any]:
        """Execute a complete workflow step by step."""
        if not isinstance(workflow, dict):
            raise ValueError(f"Workflow definition must be a dict, got {type(workflow).__name__}")

        workflow_name = workflow.get("name") or "workflow"
        steps = workflow.get("steps") or []
        self._validate_steps(workflow_name, steps)

        context: Dict[str, Any] = dict(input_params or {})
        if profile is not None:
            if getattr(profile, "user_id", None):
                context.setdefault("user_id", profile.user_id)
            if getattr(profile, "id", None):
                context.setdefault("profile_id", profile.id)
        if auth_token:
            context.setdefault("auth_token", auth_token)

        results: Dict[str, Any] = {}
        status = "completed"
        stopped_at: Optional[str] = None
        failure: Optional[str] = None

        logger.info(f"[WORKFLOW] Starting '{workflow_name}' with {len(steps)} steps")

        async with aiohttp.ClientSession() as session:
            for idx, step in enumerate(steps):
                step_name = step["name"]

                # The condition guards the step: the editor draws it as a gate,
                # and evaluating it afterwards meant a false condition still ran
                # the request it was supposed to prevent.
                condition = step.get("condition")
                if condition and not self._evaluate_condition(condition, context):
                    logger.info(f"[WORKFLOW] Condition '{condition}' not met, stopping before '{step_name}'")
                    status = "stopped"
                    stopped_at = step_name
                    break

                logger.info(
                    f"[WORKFLOW] Step {idx + 1}: {step_name} "
                    f"({str(step.get('method', 'GET')).upper()} {step.get('url', '')})"
                )

                try:
                    step_result = await self._execute_step(session, step, context)
                except Exception as e:
                    # A failed step leaves the context without the values the
                    # later steps interpolate, so carrying on just fires
                    # malformed requests at the user's API.
                    if step.get("continue_on_error"):
                        logger.warning(f"[WORKFLOW] Step '{step_name}' failed, continuing as configured: {e}")
                        continue
                    logger.error(f"[WORKFLOW] Step '{step_name}' failed, aborting '{workflow_name}': {e}")
                    status = "failed"
                    stopped_at = step_name
                    failure = str(e)
                    break

                results[step_name] = step_result
                self._update_context(context, step_result, step.get("response_mapping") or {})

        logger.info(f"[WORKFLOW] {status} '{workflow_name}', steps executed: {list(results.keys())}")

        outcome: Dict[str, Any] = {
            "workflow_name": workflow_name,
            "status": status,
            "steps_executed": list(results.keys()),
            "final_result": results,
            "context": context,
        }
        if stopped_at:
            outcome["stopped_at"] = stopped_at
        if failure:
            outcome["error"] = failure
        return outcome

    async def execute_single_step(
        self,
        step: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Run one step on its own, for the editor's 'test this step' button."""
        self._validate_steps("test", [step])
        async with aiohttp.ClientSession() as session:
            return await self._execute_step(session, step, context or {})

    @staticmethod
    def _validate_steps(workflow_name: str, steps: List[Dict[str, Any]]) -> None:
        seen = set()
        for step in steps:
            name = step.get("name")
            if not name:
                raise ValueError(f"Workflow '{workflow_name}' has a step without a name")
            if name in seen:
                raise ValueError(
                    f"Workflow '{workflow_name}' has duplicate step name '{name}'; "
                    "results are keyed by name and would overwrite each other"
                )
            seen.add(name)
            if not step.get("url"):
                raise ValueError(f"Step '{name}' of workflow '{workflow_name}' has no url")

    async def _execute_step(
        self,
        session: aiohttp.ClientSession,
        step: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute a single workflow step. Raises on failure."""
        url = self._substitute_url(step["url"], context)
        if not url.startswith(("http://", "https://")):
            url = f"http://{url}"
        await self._assert_url_allowed(url)

        body: Optional[Any] = None
        if step.get("body_template"):
            body = self._build_body(step["body_template"], context)

        headers = {
            key: self._substitute_header(value, context)
            for key, value in (step.get("headers") or {}).items()
        }

        method = str(step.get("method", "GET")).upper()
        timeout = float(step.get("timeout") or _DEFAULT_STEP_TIMEOUT)

        result = await self._request(session, method, url, headers, body, timeout)
        logger.info(f"[STEP] '{step['name']}' completed")
        return result

    async def _request(
        self,
        session: aiohttp.ClientSession,
        method: str,
        url: str,
        headers: Dict[str, str],
        body: Optional[Any],
        timeout: float = _DEFAULT_STEP_TIMEOUT,
    ) -> Dict[str, Any]:
        """Generic HTTP request helper, supports GET/POST/PUT/PATCH/DELETE."""
        kwargs: Dict[str, Any] = {}
        if body is not None and method not in ("GET", "DELETE"):
            kwargs["json"] = body

        async with session.request(
            method=method,
            url=url,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=timeout),
            **kwargs,
        ) as response:
            text = await response.text()
            response.raise_for_status()
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                # Not every endpoint answers JSON; the body is still worth
                # keeping so response_mapping can reach it.
                return {"raw": text}

    @staticmethod
    async def _assert_url_allowed(url: str) -> None:
        """Reject requests aimed at infrastructure the user should not reach."""
        host = urlparse(url).hostname
        if not host:
            raise WorkflowError(f"Step url has no host: {url}")

        try:
            infos = await asyncio.get_running_loop().getaddrinfo(host, None)
        except OSError as e:
            raise WorkflowError(f"Could not resolve '{host}': {e}")

        for info in infos:
            address = ipaddress.ip_address(info[4][0])
            if address.is_loopback:
                continue  # the built-in workflows call this API back
            if address.is_link_local or address.is_multicast or address.is_reserved:
                raise WorkflowError(
                    f"Blocked workflow request to link-local or reserved address {address} ({host})"
                )
            if address.is_private and not _ALLOW_PRIVATE_URLS:
                raise WorkflowError(
                    f"Blocked workflow request to private address {address} ({host}). "
                    "Set GILLIE_WORKFLOW_ALLOW_PRIVATE_URLS=1 to allow internal endpoints."
                )

    # ── Template substitution ────────────────────────────────────────────────

    @classmethod
    def _resolve(cls, param: str, context: Dict[str, Any]) -> Any:
        value = context[param]
        if any(kw in param.lower() for kw in _DATE_KEYWORDS):
            return cls._normalize_date(str(value))
        return value

    @classmethod
    def _substitute_url(cls, template: str, context: Dict[str, Any]) -> str:
        """Fill {param} placeholders in a URL, encoding the values.

        Values reach here straight from an LLM reading a user message, so an
        unencoded '?' or '&' would rewrite the endpoint being called.
        """
        def replace(match: "re.Match") -> str:
            param = match.group(1)
            if param not in context:
                return match.group(0)
            return quote(str(cls._resolve(param, context)), safe="/")

        return _PLACEHOLDER.sub(replace, template)

    @classmethod
    def _substitute_header(cls, template: str, context: Dict[str, Any]) -> str:
        """Fill {param} placeholders in a header value, stripping newlines."""
        def replace(match: "re.Match") -> str:
            param = match.group(1)
            if param not in context:
                return match.group(0)
            return str(cls._resolve(param, context)).replace("\r", "").replace("\n", "")

        return _PLACEHOLDER.sub(replace, template)

    @classmethod
    def _build_body(cls, body_template: str, context: Dict[str, Any]) -> Any:
        """Build the request body from its template.

        The template is parsed as JSON *before* substitution whenever it can
        be, so a value containing a quote lands inside a string instead of
        breaking the document. Interpolating first and parsing after used to
        produce an empty body and send the request anyway.
        """
        try:
            parsed = json.loads(body_template)
        except json.JSONDecodeError:
            # Placeholder sitting in a non-string position, e.g. {"n": {count}}.
            escaped = cls._substitute_escaped(body_template, context)
            try:
                return json.loads(escaped)
            except json.JSONDecodeError as e:
                raise WorkflowError(f"Body template is not valid JSON after substitution: {e}")
        return cls._substitute_structure(parsed, context)

    @classmethod
    def _substitute_structure(cls, node: Any, context: Dict[str, Any]) -> Any:
        if isinstance(node, dict):
            return {key: cls._substitute_structure(value, context) for key, value in node.items()}
        if isinstance(node, list):
            return [cls._substitute_structure(item, context) for item in node]
        if not isinstance(node, str):
            return node

        whole = _PLACEHOLDER.fullmatch(node)
        if whole and whole.group(1) in context:
            # "{count}" alone keeps the value's real type instead of stringifying it.
            return cls._resolve(whole.group(1), context)

        def replace(match: "re.Match") -> str:
            param = match.group(1)
            if param not in context:
                return match.group(0)
            return str(cls._resolve(param, context))

        return _PLACEHOLDER.sub(replace, node)

    @classmethod
    def _substitute_escaped(cls, template: str, context: Dict[str, Any]) -> str:
        """Substitute into raw JSON text, escaping each value as a JSON string."""
        def replace(match: "re.Match") -> str:
            param = match.group(1)
            if param not in context:
                return match.group(0)
            value = cls._resolve(param, context)
            if isinstance(value, (int, float, bool)) or value is None:
                return json.dumps(value)
            return json.dumps(str(value))[1:-1]

        return _PLACEHOLDER.sub(replace, template)

    # ── Context and conditions ───────────────────────────────────────────────

    @classmethod
    def _update_context(
        cls,
        context: Dict[str, Any],
        step_result: Dict[str, Any],
        response_mapping: Dict[str, str],
    ) -> None:
        """Map response fields into the execution context using dot-paths."""
        for context_key, response_path in response_mapping.items():
            try:
                context[context_key] = cls._get_nested(step_result, response_path)
            except Exception as e:
                logger.warning(f"Could not extract '{response_path}': {e}")

    @staticmethod
    def _get_nested(data: Dict[str, Any], path: str) -> Any:
        """Navigate a dot-separated path through a nested dict."""
        current = data
        for key in path.split("."):
            if isinstance(current, dict) and key in current:
                current = current[key]
            elif isinstance(current, list) and key.isdigit() and int(key) < len(current):
                current = current[int(key)]
            else:
                raise KeyError(f"Path '{path}' not found in response")
        return current

    @staticmethod
    def _evaluate_condition(condition: str, context: Dict[str, Any]) -> bool:
        """Evaluate a workflow condition against the current context.

        Fails closed: a condition nobody can parse stops the workflow rather
        than waving every remaining step through.
        """
        try:
            if "==" in condition:
                key, expected = (p.strip().strip("'\"") for p in condition.split("==", 1))
                actual = context.get(key)
                if expected.lower() in ("true", "false"):
                    return actual == (expected.lower() == "true")
                return str(actual) == expected

            if "!=" in condition:
                key, expected = (p.strip().strip("'\"") for p in condition.split("!=", 1))
                actual = context.get(key)
                if expected.lower() == "null":
                    return actual is not None
                return str(actual) != expected

            if condition.startswith("exists:"):
                key = condition.split(":", 1)[1].strip()
                return context.get(key) is not None

            if condition.startswith("greater_than:"):
                key, threshold = condition.split(":", 1)[1].split("=", 1)
                actual = context.get(key.strip())
                return bool(actual is not None and float(actual) > float(threshold.strip()))

            logger.warning(f"Unrecognized condition, stopping workflow: {condition}")
            return False

        except Exception as e:
            logger.error(f"Error evaluating condition '{condition}', stopping workflow: {e}")
            return False

    @staticmethod
    def _normalize_date(value: str) -> str:
        """
        Normalize common date formats to ISO 8601 (YYYY-MM-DD).

        Supported input formats:
        - DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY
        - YYYY/MM/DD, YYYY-MM-DD
        """
        if not isinstance(value, str):
            return str(value)

        value = value.strip()
        patterns = [
            (r"^(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})$", "DMY"),
            (r"^(\d{4})[/\-.](\d{1,2})[/\-.](\d{1,2})$", "YMD"),
        ]

        for pattern, fmt in patterns:
            m = re.match(pattern, value)
            if m:
                try:
                    if fmt == "DMY":
                        day, month, year = m.groups()
                    else:
                        year, month, day = m.groups()
                    return datetime(int(year), int(month), int(day)).strftime("%Y-%m-%d")
                except (ValueError, TypeError):
                    continue

        return value
