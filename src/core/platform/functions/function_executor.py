from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from langchain_core.tools import BaseTool
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_community.chat_models import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage, HumanMessage
from src.core.platform.config.service import ConfigurationService
from src.core.domain import Profile
from src.core.platform.functions.workflow_executor import workflow_executor
import json
import logging
import aiohttp
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


@dataclass
class FunctionDefinition:
    name: str
    description: str
    url_template: str
    method: str = "GET"
    required_params: List[str] = field(default_factory=list)
    optional_params: List[str] = field(default_factory=list)
    param_types: Dict[str, str] = field(default_factory=dict)
    param_descriptions: Dict[str, str] = field(default_factory=dict)
    examples: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    validation_rules: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowStepDefinition:
    name: str
    description: str
    url_template: str
    method: str = "GET"
    required_params: List[str] = field(default_factory=list)
    body_template: Optional[str] = None
    response_mapping: Dict[str, str] = field(default_factory=dict)
    condition: Optional[str] = None


@dataclass
class WorkflowDefinition:
    name: str
    description: str
    input_params: List[str]
    examples: List[str]
    keywords: List[str]
    steps: List[WorkflowStepDefinition]
    param_types: Dict[str, str] = field(default_factory=dict)
    param_descriptions: Dict[str, str] = field(default_factory=dict)


class GenericHTTPTool(BaseTool):
    name: str
    description: str
    url_template: str
    method: str = "GET"
    required_params: List[str] = []
    param_types: Dict[str, str] = {}
    param_descriptions: Dict[str, str] = {}

    def __init__(self, function_def: FunctionDefinition, **kwargs):
        super().__init__(
            name=function_def.name, description=function_def.description, **kwargs
        )
        self.url_template = function_def.url_template
        self.method = function_def.method
        self.required_params = function_def.required_params
        self.param_types = function_def.param_types
        self.param_descriptions = function_def.param_descriptions


class WorkflowTool(BaseTool):
    name: str
    description: str
    required_params: List[str] = []
    param_types: Dict[str, str] = {}
    param_descriptions: Dict[str, str] = {}
    workflow_type: str = ""

    def __init__(self, function_def: FunctionDefinition, workflow_type: str, **kwargs):
        super().__init__(
            name=function_def.name, description=function_def.description, **kwargs
        )
        self.required_params = function_def.required_params
        self.param_types = function_def.param_types
        self.param_descriptions = function_def.param_descriptions
        self.workflow_type = workflow_type

    def _run(self, **kwargs) -> str:
        """Execute the workflow synchronously (fallback)"""
        try:
            # For LangChain compatibility, we execute synchronously
            import asyncio

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            result = loop.run_until_complete(
                workflow_executor.execute_workflow(self.workflow_type, kwargs)
            )
            loop.close()

            return f"Workflow executed successfully. Result: {json.dumps(result, indent=2)}"

        except Exception as e:
            logger.error(f"Error executing workflow {self.workflow_type}: {e}")
            return f"Error executing workflow: {str(e)}"

    async def _arun(self, **kwargs) -> str:
        """Execute the workflow asynchronously"""
        try:
            result = await workflow_executor.execute_workflow(
                self.workflow_type, kwargs
            )
            return f"Workflow executed successfully. Result: {json.dumps(result, indent=2)}"

        except Exception as e:
            logger.error(f"Error executing workflow {self.workflow_type}: {e}")
            return f"Error executing workflow: {str(e)}"


class CustomWorkflowTool(BaseTool):
    name: str
    description: str
    required_params: List[str] = []
    param_types: Dict[str, str] = {}
    param_descriptions: Dict[str, str] = {}
    workflow_config: dict = {}

    def __init__(
        self, function_def: FunctionDefinition, workflow_config: dict, **kwargs
    ):
        super().__init__(
            name=function_def.name, description=function_def.description, **kwargs
        )
        self.required_params = function_def.required_params
        self.param_types = function_def.param_types
        self.param_descriptions = function_def.param_descriptions
        self.workflow_config = workflow_config

    def _run(self, **kwargs) -> str:
        """Execute the custom workflow synchronously"""
        try:
            import asyncio

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            result = loop.run_until_complete(self._execute_custom_workflow(kwargs))
            loop.close()

            return f"Custom workflow executed successfully. Result: {json.dumps(result, indent=2)}"

        except Exception as e:
            logger.error(f"Error executing custom workflow: {e}")
            return f"Error executing workflow: {str(e)}"

    async def _arun(self, **kwargs) -> str:
        """Execute the custom workflow asynchronously"""
        try:
            result = await self._execute_custom_workflow(kwargs)
            return f"Custom workflow executed successfully. Result: {json.dumps(result, indent=2)}"

        except Exception as e:
            logger.error(f"Error executing custom workflow: {e}")
            return f"Error executing workflow: {str(e)}"

    async def _execute_custom_workflow(self, input_params: dict) -> dict:
        """Execute a custom workflow step by step"""
        execution_context = input_params.copy()
        results = {}

        try:
            for step in self.workflow_config["steps"]:
                step_result = await self._execute_custom_step(step, execution_context)
                if step_result:
                    results[step["name"]] = step_result

                    self._update_custom_context(
                        step_result, step.get("response_mapping", {}), execution_context
                    )

                if step.get("condition") and not self._evaluate_custom_condition(
                    step["condition"], execution_context
                ):
                    logger.info(f"Condition not met in step: {step['name']}")
                    break

        except Exception as e:
            logger.error(f"Error executing custom workflow: {e}")
            raise e

        return {
            "workflow_name": self.workflow_config["name"],
            "status": "completed",
            "steps_executed": list(results.keys()),
            "final_result": results,
            "context": execution_context,
        }

    async def _execute_custom_step(
        self, step: dict, execution_context: dict
    ) -> Optional[dict]:
        """Execute an individual step of the custom workflow"""
        try:
            url = step["url"]
            for param, value in execution_context.items():
                url = url.replace(f"{{{param}}}", str(value))

            body = None
            if step.get("body_template"):
                body = self._prepare_custom_body(
                    step["body_template"], execution_context
                )

            async with aiohttp.ClientSession() as session:
                if step["method"].upper() == "GET":
                    async with session.get(url) as response:
                        response.raise_for_status()
                        result = await response.json()
                elif step["method"].upper() == "POST":
                    async with session.post(url, json=body) as response:
                        response.raise_for_status()
                        result = await response.json()
                else:
                    raise ValueError(f"Unsupported HTTP method: {step['method']}")

            logger.info(f"Step '{step['name']}' executed successfully")
            return result

        except Exception as e:
            logger.error(f"Error executing step '{step['name']}': {e}")
            return None

    def _prepare_custom_body(self, body_template: str, execution_context: dict) -> dict:
        """Prepare the request body by replacing context variables"""
        try:
            body_str = body_template
            for param, value in execution_context.items():
                body_str = body_str.replace(f"{{{param}}}", str(value))

            return json.loads(body_str)
        except Exception as e:
            logger.error(f"Error preparing body: {e}")
            return {}

    def _update_custom_context(
        self, step_result: dict, response_mapping: dict, execution_context: dict
    ):
        """Update the execution context with step results"""
        for context_key, response_path in response_mapping.items():
            try:
                value = self._extract_nested_value(step_result, response_path)
                execution_context[context_key] = value
            except Exception as e:
                logger.warning(f"Could not extract {response_path}: {e}")

    def _extract_nested_value(self, data: dict, path: str) -> Any:
        """Extract nested value using dot path (e.g. 'customer.name')"""
        keys = path.split(".")
        current = data

        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                raise KeyError(f"Path '{path}' not valid in data")

        return current

    def _evaluate_custom_condition(
        self, condition: str, execution_context: dict
    ) -> bool:
        """Evaluate a custom workflow condition"""
        try:
            if condition.startswith("equals:"):
                key_value = condition.split(":", 1)[1]
                key, expected_value = key_value.split("=", 1)
                actual_value = execution_context.get(key)
                return str(actual_value) == expected_value

            elif condition.startswith("exists:"):
                key = condition.split(":", 1)[1]
                return key in execution_context and execution_context[key] is not None

            elif condition.startswith("greater_than:"):
                key_value = condition.split(":", 1)[1]
                key, threshold = key_value.split("=", 1)
                actual_value = execution_context.get(key)
                return actual_value and float(actual_value) > float(threshold)

            else:
                logger.warning(f"Unrecognized condition: {condition}")
                return True

        except Exception as e:
            logger.error(f"Error evaluating condition '{condition}': {e}")
            return True

    def _run(self, **kwargs) -> str:
        try:
            missing_params = [
                param for param in self.required_params if param not in kwargs
            ]
            if missing_params:
                return (
                    f"Error: Missing required parameters: {', '.join(missing_params)}"
                )

            final_url = self.url_template
            for param, value in kwargs.items():
                final_url = final_url.replace(f"{{{param}}}", str(value))

            import requests

            response = requests.request(method=self.method, url=final_url, timeout=30)
            response.raise_for_status()

            result = response.json() if response.content else "Request successful"
            return f"Function executed successfully. Result: {json.dumps(result, indent=2)}"

        except Exception as e:
            logger.error(f"Error executing function {self.name}: {e}")
            return f"Error executing function: {str(e)}"

    async def _arun(self, **kwargs) -> str:
        try:
            missing_params = [
                param for param in self.required_params if param not in kwargs
            ]
            if missing_params:
                return (
                    f"Error: Missing required parameters: {', '.join(missing_params)}"
                )

            final_url = self.url_template
            for param, value in kwargs.items():
                final_url = final_url.replace(f"{{{param}}}", str(value))

            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method=self.method,
                    url=final_url,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as response:
                    response.raise_for_status()
                    result = (
                        await response.json()
                        if response.content_type == "application/json"
                        else await response.text()
                    )

            return f"Function executed successfully. Result: {json.dumps(result, indent=2) if isinstance(result, dict) else result}"

        except Exception as e:
            logger.error(f"Error executing function {self.name}: {e}")
            return f"Error executing function: {str(e)}"


class GenericFunctionExecutor:
    def __init__(self, config_service: ConfigurationService):
        self.config_service = config_service
        self.llm = ChatOpenAI(
            api_key=config_service.openai_config.api_key,
            base_url=config_service.openai_config.base_url,
            model=config_service.openai_config.model,
            temperature=0.1,
        )
        self.tools = []
        self.agent = None
        self.executor = None
        self._setup_prompt()

    def _setup_prompt(self):
        system_message = """You are a helpful AI assistant that can execute various functions based on user requests.

Your role is to:
1. Understand what the user is asking for
2. Determine if any available functions can help
3. Extract the necessary parameters from the user's message
4. Execute the appropriate function
5. Provide a friendly, helpful response in Spanish

Always be conversational and helpful. If you need more information, ask for it clearly.
If a function fails, explain what went wrong and suggest alternatives."""

        self.prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_message),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        )

    def _extract_params_from_url(self, url: str) -> List[str]:
        """Extract required parameters from URL template"""
        import re

        return re.findall(r"\{(\w+)\}", url)

    def _create_tools_from_profile(self, profile: Profile) -> List[BaseTool]:
        tools = []

        if not profile.functions:
            return tools

        try:
            if isinstance(profile.functions, str):
                functions_config = json.loads(profile.functions)
            else:
                functions_config = profile.functions

            if isinstance(functions_config, dict):
                functions_list = [functions_config]
            elif isinstance(functions_config, list):
                functions_list = functions_config
            else:
                logger.warning(
                    f"Invalid functions configuration format: {type(functions_config)}"
                )
                return tools

            for item_config in functions_list:
                try:
                    tool = self._create_tool_from_item(item_config)
                    if tool:
                        tools.append(tool)
                        logger.info(f"Created tool: {tool.name}")
                except Exception as e:
                    logger.error(f"Error creating tool from item {item_config}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error parsing functions configuration: {e}")

        return tools

    def _create_tool_from_item(self, item_config: dict) -> Optional[BaseTool]:
        """Create tool from function or workflow item"""
        try:
            item_type = item_config.get("type", "function")

            if item_type == "workflow":
                return self._create_workflow_tool(item_config)
            elif item_type == "function":
                return self._create_function_tool(item_config)
            else:
                logger.warning(f"Unrecognized item type: {item_type}")
                return None

        except Exception as e:
            logger.error(f"Error creating tool from item: {e}")
            return None

    def _create_function_tool(self, config: dict) -> Optional[GenericHTTPTool]:
        """Create a tool for common HTTP functions"""
        try:
            import re

            url_template = config.get("url", "")
            required_params = re.findall(r"\{(\w+)\}", url_template)

            custom_param_types = config.get("param_types", {})
            custom_param_descriptions = config.get("param_descriptions", {})

            inferred_types = self._infer_param_types(required_params, config)
            param_types = {**inferred_types, **custom_param_types}

            inferred_descriptions = self._create_param_descriptions(
                required_params, config
            )
            param_descriptions = {**inferred_descriptions, **custom_param_descriptions}

            function_def = FunctionDefinition(
                name=config.get("name", "unknown_function"),
                description=config.get("description", "No description available"),
                url_template=url_template,
                method=config.get("method", "GET"),
                required_params=required_params,
                param_types=param_types,
                param_descriptions=param_descriptions,
                examples=config.get("examples", []),
                keywords=config.get("keywords", []),
                validation_rules=config.get("validation_rules", {}),
            )

            return GenericHTTPTool(function_def)

        except Exception as e:
            logger.error(f"Error creating function tool: {e}")
            return None

    def _create_workflow_tool(self, config: dict) -> Optional[WorkflowTool]:
        """Create a tool for executing workflows"""
        try:
            if "steps" in config:
                return self._create_custom_workflow_tool(config)

            workflow_type = config.get("workflow_type")
            if not workflow_type:
                logger.error("Could not determine workflow type")
                return None

            workflow_info = workflow_executor.get_workflow_info(workflow_type)
            if not workflow_info:
                logger.error(f"Workflow '{workflow_type}' not found")
                return None

            function_def = FunctionDefinition(
                name=config.get("name", workflow_info["name"]),
                description=config.get("description", workflow_info["description"]),
                url_template=f"workflow://{workflow_type}",
                method="WORKFLOW",
                required_params=workflow_info["input_params"],
                param_types=config.get(
                    "param_types",
                    {param: "string" for param in workflow_info["input_params"]},
                ),
                param_descriptions=config.get(
                    "param_descriptions",
                    {
                        param: f"Input parameter: {param}"
                        for param in workflow_info["input_params"]
                    },
                ),
                examples=config.get("examples", workflow_info["examples"]),
                keywords=config.get("keywords", workflow_info["keywords"]),
                validation_rules=config.get("validation_rules", {}),
            )

            return WorkflowTool(function_def, workflow_type)

        except Exception as e:
            logger.error(f"Error creating workflow tool: {e}")
            return None

    def _create_custom_workflow_tool(self, config: dict) -> Optional[WorkflowTool]:
        """Create a tool for custom workflows"""
        try:
            function_def = FunctionDefinition(
                name=config.get("name", "custom_workflow"),
                description=config.get("description", "Custom workflow"),
                url_template="workflow://custom",
                method="WORKFLOW",
                required_params=config.get("input_params", []),
                param_types=config.get("param_types", {}),
                param_descriptions=config.get("param_descriptions", {}),
                examples=config.get("examples", []),
                keywords=config.get("keywords", []),
                validation_rules=config.get("validation_rules", {}),
            )

            return CustomWorkflowTool(function_def, config)

        except Exception as e:
            logger.error(f"Error creating custom workflow tool: {e}")
            return None

    def _infer_param_types(self, params: List[str], config: dict) -> Dict[str, str]:
        """Infer parameter types generically based on common patterns and context"""
        param_types = {}

        for param in params:
            param_lower = param.lower()

            if param_lower in [
                "price",
                "amount",
                "quantity",
                "count",
                "number",
                "limit",
                "offset",
                "page",
                "size",
            ]:
                param_types[param] = "number"
            elif param_lower in [
                "date",
                "fecha",
                "time",
                "hora",
                "datetime",
                "created_at",
                "updated_at",
                "start_date",
                "end_date",
            ]:
                param_types[param] = "datetime"
            elif param_lower in [
                "id",
                "user_id",
                "customer_id",
                "order_id",
                "product_id",
                "category_id",
                "tag_id",
            ]:
                param_types[param] = "string"
            elif param_lower in ["email", "mail", "username", "login"]:
                param_types[param] = "string"
            elif param_lower in [
                "url",
                "link",
                "website",
                "endpoint",
                "callback_url",
                "redirect_url",
            ]:
                param_types[param] = "string"
            elif param_lower in [
                "name",
                "title",
                "description",
                "content",
                "message",
                "comment",
                "note",
            ]:
                param_types[param] = "string"
            elif param_lower in [
                "enabled",
                "active",
                "status",
                "is_public",
                "is_verified",
                "is_approved",
            ]:
                param_types[param] = "boolean"
            elif param_lower in ["tags", "categories", "keywords", "labels"]:
                param_types[param] = "array"
            elif param_lower in ["metadata", "config", "settings", "options"]:
                param_types[param] = "object"
            else:
                param_types[param] = "string"

        return param_types

    def _create_param_descriptions(
        self, params: List[str], config: dict
    ) -> Dict[str, str]:
        """Create generic parameter descriptions based on common patterns"""
        descriptions = {}

        for param in params:
            param_lower = param.lower()

            if param_lower in [
                "price",
                "amount",
                "quantity",
                "count",
                "number",
                "limit",
                "offset",
                "page",
                "size",
            ]:
                descriptions[param] = "Numeric value"
            elif param_lower in [
                "date",
                "fecha",
                "time",
                "hora",
                "datetime",
                "created_at",
                "updated_at",
                "start_date",
                "end_date",
            ]:
                descriptions[param] = "Date/time value (YYYY-MM-DD format recommended)"
            elif param_lower in [
                "id",
                "user_id",
                "customer_id",
                "order_id",
                "product_id",
                "category_id",
                "tag_id",
            ]:
                descriptions[param] = "Unique identifier"
            elif param_lower in ["email", "mail", "username", "login"]:
                descriptions[param] = "Email address or username"
            elif param_lower in [
                "url",
                "link",
                "website",
                "endpoint",
                "callback_url",
                "redirect_url",
            ]:
                descriptions[param] = "URL or web link"
            elif param_lower in [
                "name",
                "title",
                "description",
                "content",
                "message",
                "comment",
                "note",
            ]:
                descriptions[param] = "Text content"
            elif param_lower in [
                "enabled",
                "active",
                "status",
                "is_public",
                "is_verified",
                "is_approved",
            ]:
                descriptions[param] = "Boolean value (true/false, yes/no, 1/0)"
            elif param_lower in ["tags", "categories", "keywords", "labels"]:
                descriptions[param] = "Comma-separated list or array of values"
            elif param_lower in ["metadata", "config", "settings", "options"]:
                descriptions[param] = "JSON object with configuration data"
            else:
                descriptions[param] = f"Value for parameter {param}"

        return descriptions

    def setup_for_profile(self, profile: Profile):
        """Setup the executor for a specific profile"""
        self.tools = self._create_tools_from_profile(profile)

        if self.tools:
            self.agent = create_openai_functions_agent(
                llm=self.llm, tools=self.tools, prompt=self.prompt
            )
            self.executor = AgentExecutor(
                agent=self.agent,
                tools=self.tools,
                verbose=True,
                handle_parsing_errors=True,
            )
            logger.info(
                f"Setup complete for profile {profile.user_id} with {len(self.tools)} tools"
            )
        else:
            logger.info(f"No tools available for profile {profile.user_id}")

    async def execute_function(
        self, user_message: str, profile: Profile, chat_history: List[str] = None
    ) -> str:
        """Execute function based on user message"""
        try:
            if not self.tools or not self.executor:
                self.setup_for_profile(profile)

            if not self.tools:
                return "No functions are currently available for your profile."

            history_messages = []
            if chat_history:
                for msg in chat_history[-5:]:
                    history_messages.append(HumanMessage(content=msg))

            result = await self.executor.ainvoke(
                {"input": user_message, "chat_history": history_messages}
            )

            return result.get("output", "Function executed successfully")

        except Exception as e:
            logger.error(f"Error executing function: {e}")
            return (
                f"Sorry, I had a problem processing your request. Error: {str(e)}"
            )

    def get_available_functions(self) -> List[Dict[str, Any]]:
        """Get information about available functions"""
        functions_info = []

        for tool in self.tools:
            if isinstance(tool, GenericHTTPTool):
                functions_info.append(
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "required_params": tool.required_params,
                        "param_types": tool.param_types,
                        "param_descriptions": tool.param_descriptions,
                    }
                )

        return functions_info
