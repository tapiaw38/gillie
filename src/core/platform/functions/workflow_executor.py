import logging
import json
import aiohttp
import re
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class WorkflowStep:
    name: str
    description: str
    url: str
    method: str
    required_params: List[str]
    condition: Optional[str] = None
    body_template: Optional[str] = None
    response_mapping: Dict[str, str] = None


@dataclass
class WorkflowDefinition:
    name: str
    description: str
    input_params: List[str]
    examples: List[str]
    keywords: List[str]
    steps: List[WorkflowStep]


class WorkflowExecutor:
    """Executes multi-step workflows sequentially, passing context between steps."""

    def __init__(self, config_service=None):
        self.config_service = config_service
        self.execution_context: Dict[str, Any] = {}
        self.workflows: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Registry
    # ------------------------------------------------------------------

    def get_available_workflows(self) -> List[str]:
        return list(self.workflows.keys())

    def register_workflow(self, name: str, workflow: Dict[str, Any]):
        self.workflows[name] = workflow

    def get_workflow_info(self, workflow_name: str) -> Optional[Dict[str, Any]]:
        if workflow_name not in self.workflows:
            return None
        workflow = self.workflows[workflow_name]
        return {
            "name": workflow["name"],
            "description": workflow["description"],
            "input_params": workflow["input_params"],
            "examples": workflow["examples"],
            "keywords": workflow["keywords"],
        }

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    async def execute_workflow(
        self,
        workflow_name: str,
        input_params: Dict[str, Any],
        profile=None,
        auth_token: str = None,
    ) -> Dict[str, Any]:
        """Execute a complete workflow step by step."""

        if workflow_name not in self.workflows:
            raise ValueError(f"Workflow '{workflow_name}' not found. Available: {list(self.workflows.keys())}")

        workflow = self.workflows[workflow_name]
        self.execution_context = input_params.copy()

        # Auto-inject profile identifiers
        if profile:
            if hasattr(profile, "user_id") and profile.user_id:
                self.execution_context.setdefault("user_id", profile.user_id)
            if hasattr(profile, "id") and profile.id:
                self.execution_context.setdefault("profile_id", profile.id)

        if auth_token:
            self.execution_context.setdefault("auth_token", auth_token)

        results: Dict[str, Any] = {}

        logger.info(f"[WORKFLOW] Starting '{workflow_name}' with {len(workflow.get('steps', []))} steps")

        try:
            for idx, step in enumerate(workflow["steps"]):
                logger.info(f"[WORKFLOW] Step {idx + 1}: {step['name']} ({step['method'].upper()} {step['url']})")

                step_result = await self._execute_step(step)

                if step_result is not None:
                    results[step["name"]] = step_result
                    self._update_context(step_result, step.get("response_mapping", {}))
                else:
                    logger.warning(f"[WORKFLOW] Step '{step['name']}' returned no result")

                if step.get("condition"):
                    if not self._evaluate_condition(step["condition"], results):
                        logger.info(f"[WORKFLOW] Condition not met at step '{step['name']}', stopping")
                        break

        except Exception as e:
            logger.error(f"[WORKFLOW] Error in '{workflow_name}': {e}", exc_info=True)
            raise

        logger.info(f"[WORKFLOW] Completed '{workflow_name}', steps executed: {list(results.keys())}")

        return {
            "workflow_name": workflow_name,
            "status": "completed",
            "steps_executed": list(results.keys()),
            "final_result": results,
            "context": self.execution_context,
        }

    async def _execute_step(self, step: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Execute a single workflow step."""
        try:
            # Build the URL from the template
            url = self._substitute(step["url"])

            if not url.startswith(("http://", "https://")):
                url = f"http://{url}"

            # Build the body (if any)
            body: Optional[Dict[str, Any]] = None
            if step.get("body_template"):
                body = self._prepare_body(step["body_template"])

            # Build headers (if any)
            headers: Dict[str, str] = {}
            for key, value in (step.get("headers") or {}).items():
                headers[key] = self._substitute(value)

            logger.info(f"[STEP] {step['method'].upper()} {url}")

            result = await self._request(step["method"], url, headers, body)

            logger.info(f"[STEP] '{step['name']}' completed")
            return result

        except Exception as e:
            logger.error(f"[STEP] Error in '{step['name']}': {e}", exc_info=True)
            return None

    async def _request(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
        body: Optional[Dict[str, Any]],
        timeout: float = 30.0,
    ) -> Dict[str, Any]:
        """Generic HTTP request helper, supports GET/POST/PUT/DELETE/PATCH."""
        timeout_cfg = aiohttp.ClientTimeout(total=timeout)
        kwargs: Dict[str, Any] = {}
        if body is not None and method.upper() not in ("GET", "DELETE"):
            kwargs["json"] = body

        async with aiohttp.ClientSession() as session:
            async with session.request(
                method=method.upper(),
                url=url,
                headers=headers,
                timeout=timeout_cfg,
                **kwargs,
            ) as response:
                response.raise_for_status()
                return await response.json()

    # ------------------------------------------------------------------
    # Context helpers
    # ------------------------------------------------------------------

    def _substitute(self, template: str) -> str:
        """Replace {param} placeholders in a string using the execution context."""
        for param, value in self.execution_context.items():
            date_keywords = ["check_in", "check_out", "fecha", "date", "inicio", "fin",
                             "start_date", "end_date", "booking_date", "reservation_date"]
            if any(kw in param.lower() for kw in date_keywords):
                value = self._normalize_date(str(value))
            template = template.replace(f"{{{param}}}", str(value))
        return template

    def _prepare_body(self, body_template: str) -> Dict[str, Any]:
        """Build the request body by substituting context variables."""
        try:
            return json.loads(self._substitute(body_template))
        except Exception as e:
            logger.error(f"Error preparing body: {e}")
            return {}

    def _update_context(self, step_result: Dict[str, Any], response_mapping: Dict[str, str]):
        """Map response fields into the execution context using dot-paths."""
        for context_key, response_path in response_mapping.items():
            try:
                self.execution_context[context_key] = self._get_nested(step_result, response_path)
            except Exception as e:
                logger.warning(f"Could not extract '{response_path}': {e}")

    @staticmethod
    def _get_nested(data: Dict[str, Any], path: str) -> Any:
        """Navigate a dot-separated path through a nested dict."""
        current = data
        for key in path.split("."):
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                raise KeyError(f"Path '{path}' not found in response")
        return current

    # ------------------------------------------------------------------
    # Condition evaluation
    # ------------------------------------------------------------------

    def _evaluate_condition(self, condition: str, results: Dict[str, Any]) -> bool:
        """Evaluate a simple workflow condition against the current context."""
        try:
            if "==" in condition:
                key, expected = (p.strip().strip("'\"") for p in condition.split("==", 1))
                actual = self.execution_context.get(key)
                if expected.lower() in ("true", "false"):
                    return actual == (expected.lower() == "true")
                return str(actual) == expected

            if "!=" in condition:
                key, expected = (p.strip().strip("'\"") for p in condition.split("!=", 1))
                actual = self.execution_context.get(key)
                if expected.lower() == "null":
                    return actual is not None
                return str(actual) != expected

            if condition.startswith("exists:"):
                key = condition.split(":", 1)[1].strip()
                return key in self.execution_context and self.execution_context[key] is not None

            if condition.startswith("greater_than:"):
                key, threshold = condition.split(":", 1)[1].split("=", 1)
                actual = self.execution_context.get(key.strip())
                return bool(actual and float(actual) > float(threshold.strip()))

            logger.warning(f"Unrecognized condition: {condition}")
            return True

        except Exception as e:
            logger.error(f"Error evaluating condition '{condition}': {e}")
            return True

    # ------------------------------------------------------------------
    # Date normalization
    # ------------------------------------------------------------------

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
                        return datetime(int(year), int(month), int(day)).strftime("%Y-%m-%d")
                    else:
                        year, month, day = m.groups()
                        return datetime(int(year), int(month), int(day)).strftime("%Y-%m-%d")
                except (ValueError, TypeError):
                    continue

        return value

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def convert_workflow_to_function(self, workflow_name: str) -> Dict[str, Any]:
        """Convert a registered workflow to a function-compatible descriptor."""
        if workflow_name not in self.workflows:
            raise ValueError(f"Workflow '{workflow_name}' not found")

        workflow = self.workflows[workflow_name]
        return {
            "name": workflow["name"],
            "description": workflow["description"],
            "url": f"workflow://{workflow_name}",
            "method": "WORKFLOW",
            "param_types": {p: "string" for p in workflow["input_params"]},
            "param_descriptions": {p: f"Input parameter: {p}" for p in workflow["input_params"]},
            "examples": workflow["examples"],
            "keywords": workflow["keywords"],
            "workflow_type": workflow_name,
        }


workflow_executor = WorkflowExecutor()
