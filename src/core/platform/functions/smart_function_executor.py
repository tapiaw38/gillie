import json
import logging
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from langchain_community.chat_models import ChatOpenAI
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_core.tools import BaseTool

from src.core.platform.functions.workflow_executor import (
    WorkflowExecutor,
    WorkflowDefinition,
    WorkflowStep,
)
from src.core.platform.functions.function_executor import (
    GenericHTTPTool,
    FunctionDefinition,
)
from src.core.services.configuration_service import ConfigurationService
from src.core.domain.model import Profile

logger = logging.getLogger(__name__)


@dataclass
class FunctionConfig:
    """Configuración de una función individual"""

    type: str  # "simple" or "workflow"
    sequential: bool = False
    sequential_number: Optional[int] = None
    name: str = ""
    method: str = "GET"
    body: Optional[str] = None
    headers: str = ""
    url: str = ""


class SmartFunctionExecutor:
    """Ejecutor inteligente que analiza preguntas del usuario y ejecuta funciones o workflows"""

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

    def _setup_prompt(self):
        """Configurar prompt para análisis de intención"""
        system_message = """You are an AI assistant that analyzes user questions to determine if they match any available functions.

Your task is to:
1. Analyze the user's question
2. Check if it matches any function names from the available list
3. If there's a match, identify which function and what parameters are needed
4. If no match, respond that no suitable function was found

Available functions: {available_functions}

Respond in this exact JSON format:
{
    "match_found": true/false,
    "function_name": "name_of_matched_function",
    "confidence": 0.0-1.0,
    "reasoning": "explanation of why this function matches",
    "missing_params": ["param1", "param2"],
    "extracted_params": {"param1": "value1"}
}

If no match is found, set match_found to false and provide reasoning."""

        self.intent_prompt = ChatPromptTemplate.from_messages(
            [("system", system_message), ("human", "User question: {user_question}")]
        )

    def _parse_functions_config(self, functions_string: str) -> List[FunctionConfig]:
        """Parsear la configuración de funciones desde string JSON"""
        try:
            if isinstance(functions_string, str):
                functions_list = json.loads(functions_string)
            else:
                functions_list = functions_string

            # Asegurar que sea una lista
            if isinstance(functions_list, dict):
                functions_list = [functions_list]

            parsed_functions = []
            for func in functions_list:
                config = FunctionConfig(
                    type=func.get("type", "simple"),
                    sequential=func.get("sequential", False),
                    sequential_number=func.get("sequential_number"),
                    name=func.get("name", ""),
                    method=func.get("method", "GET"),
                    body=func.get("body"),
                    headers=func.get("headers", ""),
                    url=func.get("url", ""),
                )
                parsed_functions.append(config)

            return parsed_functions

        except Exception as e:
            logger.error(f"Error parsing functions configuration: {e}")
            return []

    async def _analyze_user_intent(
        self, user_question: str, available_functions: List[FunctionConfig]
    ) -> Dict[str, Any]:
        """Usar IA para analizar la intención del usuario y encontrar coincidencias"""
        try:
            # Preparar lista de funciones disponibles para el prompt
            functions_info = []
            for func in available_functions:
                functions_info.append(
                    {
                        "name": func.name,
                        "description": f"{func.type} function - {func.url}",
                        "type": func.type,
                        "sequential": func.sequential,
                    }
                )

            # Crear prompt con funciones disponibles
            prompt = self.intent_prompt.format(
                available_functions=json.dumps(functions_info, indent=2),
                user_question=user_question,
            )

            # Obtener respuesta de la IA
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])

            # Parsear respuesta JSON
            try:
                intent_analysis = json.loads(response.content)
                return intent_analysis
            except json.JSONDecodeError:
                logger.error(f"Failed to parse AI response as JSON: {response.content}")
                return {"match_found": False, "reasoning": "Error parsing AI response"}

        except Exception as e:
            logger.error(f"Error analyzing user intent: {e}")
            return {
                "match_found": False,
                "reasoning": f"Error in intent analysis: {str(e)}",
            }

    def _extract_url_params(self, url: str) -> List[str]:
        """Extraer parámetros requeridos de la URL template"""
        return re.findall(r"\{(\w+)\}", url)

    async def _get_missing_params_from_user(
        self, missing_params: List[str], function_name: str
    ) -> Dict[str, str]:
        """Solicitar parámetros faltantes al usuario usando IA"""
        try:
            param_prompt = f"""The user needs to provide parameters for function '{function_name}'.

Missing parameters: {', '.join(missing_params)}

Please ask the user for each missing parameter in a natural, conversational way in Spanish.
Ask one parameter at a time and wait for the user's response.

Start by asking for the first parameter: {missing_params[0]}"""

            response = await self.llm.ainvoke([HumanMessage(content=param_prompt)])
            return {
                "message": response.content,
                "next_param": missing_params[0] if missing_params else None,
                "remaining_params": (
                    missing_params[1:] if len(missing_params) > 1 else []
                ),
            }

        except Exception as e:
            logger.error(f"Error getting missing params: {e}")
            return {
                "message": f"Necesito que me proporciones los siguientes parámetros para {function_name}: {', '.join(missing_params)}",
                "next_param": missing_params[0] if missing_params else None,
                "remaining_params": (
                    missing_params[1:] if len(missing_params) > 1 else []
                ),
            }

    def _build_complete_url(self, url_template: str, params: Dict[str, str]) -> str:
        """Construir URL completa reemplazando parámetros"""
        final_url = url_template
        for param, value in params.items():
            final_url = final_url.replace(f"{{{param}}}", str(value))
        return final_url

    async def _execute_simple_function(
        self, function_config: FunctionConfig, params: Dict[str, str]
    ) -> Dict[str, Any]:
        """Ejecutar función simple"""
        try:
            # Construir URL completa
            final_url = self._build_complete_url(function_config.url, params)

            # Crear herramienta LangChain
            function_def = FunctionDefinition(
                name=function_config.name,
                description=f"Execute {function_config.name}",
                url_template=final_url,
                method=function_config.method,
                required_params=list(params.keys()),
            )

            tool = GenericHTTPTool(function_def)

            # Ejecutar función
            result = tool._run(**params)

            return {
                "success": True,
                "result": result,
                "url_executed": final_url,
                "type": "simple_function",
            }

        except Exception as e:
            logger.error(f"Error executing simple function {function_config.name}: {e}")
            return {"success": False, "error": str(e), "type": "simple_function"}

    async def _execute_workflow(
        self, function_config: FunctionConfig, params: Dict[str, str]
    ) -> Dict[str, Any]:
        """Ejecutar workflow"""
        try:
            # Crear definición de workflow desde la configuración
            workflow_steps = []

            # Por ahora, asumimos que el workflow tiene un solo paso
            # En el futuro, esto se puede expandir para manejar workflows complejos
            step = WorkflowStep(
                name=function_config.name,
                description=f"Execute {function_config.name}",
                url=function_config.url,
                method=function_config.method,
                required_params=list(params.keys()),
            )
            workflow_steps.append(step)

            workflow_def = WorkflowDefinition(
                name=function_config.name,
                description=f"Workflow for {function_config.name}",
                steps=workflow_steps,
                input_params=list(params.keys()),
            )

            # Ejecutar workflow
            result = await self.workflow_executor.execute_workflow(
                workflow=workflow_def, user_params=params, context={}
            )

            return {"success": True, "result": result, "type": "workflow"}

        except Exception as e:
            logger.error(f"Error executing workflow {function_config.name}: {e}")
            return {"success": False, "error": str(e), "type": "workflow"}

    async def execute_function(
        self, user_message: str, profile: Profile, chat_history: List[str] = None
    ) -> str:
        """Ejecutar función basada en el mensaje del usuario"""
        try:
            if not profile.functions:
                return "No hay funciones configuradas para tu perfil."

            # Parsear configuración de funciones
            available_functions = self._parse_functions_config(profile.functions)
            if not available_functions:
                return "Error al parsear la configuración de funciones."

            # Analizar intención del usuario con IA
            intent_analysis = await self._analyze_user_intent(
                user_message, available_functions
            )

            if not intent_analysis.get("match_found", False):
                return f"No encontré una función que coincida con tu solicitud. {intent_analysis.get('reasoning', '')}"

            # Encontrar la función coincidente
            matched_function_name = intent_analysis.get("function_name")
            matched_function = None

            for func in available_functions:
                if func.name == matched_function_name:
                    matched_function = func
                    break

            if not matched_function:
                return f"Error: No se pudo encontrar la función '{matched_function_name}' en la configuración."

            # Verificar parámetros faltantes
            missing_params = intent_analysis.get("missing_params", [])
            extracted_params = intent_analysis.get("extracted_params", {})

            if missing_params:
                # Solicitar parámetros faltantes
                param_request = await self._get_missing_params_from_user(
                    missing_params, matched_function.name
                )
                return param_request["message"]

            # Ejecutar función según su tipo
            if matched_function.type == "simple":
                execution_result = await self._execute_simple_function(
                    matched_function, extracted_params
                )
            elif matched_function.type == "workflow":
                execution_result = await self._execute_workflow(
                    matched_function, extracted_params
                )
            else:
                return f"Tipo de función no soportado: {matched_function.type}"

            if not execution_result.get("success", False):
                return f"Error ejecutando {matched_function.name}: {execution_result.get('error', 'Error desconocido')}"

            # Generar respuesta amigable
            if matched_function.type == "simple":
                return f"✅ Función '{matched_function.name}' ejecutada exitosamente.\n\nResultado: {execution_result.get('result', 'Sin resultado')}"
            else:
                return f"✅ Workflow '{matched_function.name}' ejecutado exitosamente.\n\nResultado: {execution_result.get('result', 'Sin resultado')}"

        except Exception as e:
            logger.error(f"Error in smart function execution: {e}")
            return (
                f"Lo siento, tuve un problema al procesar tu solicitud. Error: {str(e)}"
            )

    def get_available_functions(self, profile: Profile) -> List[Dict[str, Any]]:
        """Obtener información sobre funciones disponibles"""
        try:
            if not profile.functions:
                return []

            available_functions = self._parse_functions_config(profile.functions)
            functions_info = []

            for func in available_functions:
                info = {
                    "name": func.name,
                    "type": func.type,
                    "sequential": func.sequential,
                    "sequential_number": func.sequential_number,
                    "method": func.method,
                    "url": func.url,
                }
                functions_info.append(info)

            return functions_info

        except Exception as e:
            logger.error(f"Error getting available functions: {e}")
            return []
