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
from src.core.domain import Profile

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
    keywords: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    param_descriptions: Dict[str, str] = field(default_factory=dict)


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
        # Almacenamiento simple para parámetros de funciones
        self.function_params_storage = {}

    def _setup_prompt(self):
        """Configurar prompt para análisis de intención"""
        system_message = """You are an AI assistant that analyzes user questions to determine if they match any available functions.

Your task is to:
1. Analyze the user's question
2. Check if it matches any function names, descriptions, or keywords from the available list
3. If there's a match, identify which function and what parameters are needed
4. If no match, respond that no suitable function was found

Available functions: {available_functions}

IMPORTANT: You must respond ONLY with valid JSON in this exact format:
{{
    "match_found": true/false,
    "function_name": "name_of_matched_function",
    "confidence": 0.0-1.0,
    "reasoning": "explanation of why this function matches",
    "missing_params": ["param1", "param2"],
    "extracted_params": {{"param1": "value1"}}
}}

ANALYSIS GUIDELINES:
- Look for exact matches in function names first
- Check if user's question contains keywords from the function
- Consider the function description and examples
- If the user asks about location, coordinates, or maps, look for location-related functions
- If the user asks about weather or climate, look for weather-related functions

CRITICAL RULES:
- Respond ONLY with the JSON, no additional text before or after
- Use double quotes for all strings
- Use true/false (not "true"/"false") for boolean values
- If no match is found, set match_found to false and provide reasoning
- Do not include any explanations outside the JSON structure"""

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
                # Log para debugging
                logger.debug(f"Parsing function: {func.get('name', 'unnamed')}")

                config = FunctionConfig(
                    type=func.get("type", "simple"),
                    sequential=func.get("sequential", False),
                    sequential_number=func.get("sequential_number"),
                    name=func.get("name", ""),
                    method=func.get("method", "GET"),
                    body=func.get("body"),
                    headers=func.get("headers", ""),
                    url=func.get(
                        "url_template", func.get("url", "")
                    ),  # Usar url_template si está disponible
                )

                # Agregar campos adicionales que podrían ser útiles
                if hasattr(config, "keywords"):
                    config.keywords = func.get("keywords", [])
                if hasattr(config, "examples"):
                    config.examples = func.get("examples", [])
                if hasattr(config, "param_descriptions"):
                    config.param_descriptions = func.get("param_descriptions", {})

                parsed_functions.append(config)

                logger.debug(f"Successfully parsed function: {config.name}")

            return parsed_functions

        except Exception as e:
            logger.error(f"Error parsing functions configuration: {e}")
            logger.error(f"Functions string: {functions_string}")
            return []

    async def _analyze_user_intent(
        self, user_question: str, available_functions: List[FunctionConfig]
    ) -> Dict[str, Any]:
        """Usar IA para analizar la intención del usuario y encontrar coincidencias"""
        try:
            # Preparar lista de funciones disponibles para el prompt
            functions_info = []
            for func in available_functions:
                function_info = {
                    "name": func.name,
                    "description": f"{func.type} function - {func.url}",
                    "type": func.type,
                    "sequential": func.sequential,
                }

                # Agregar información adicional si está disponible
                if hasattr(func, "keywords") and func.keywords:
                    function_info["keywords"] = func.keywords
                if hasattr(func, "examples") and func.examples:
                    function_info["examples"] = func.examples[
                        :2
                    ]  # Solo los primeros 2 ejemplos

                functions_info.append(function_info)

            # Crear prompt con funciones disponibles
            prompt = self.intent_prompt.format(
                available_functions=json.dumps(functions_info, indent=2),
                user_question=user_question,
            )

            # Obtener respuesta de la IA
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])

            # Log de la respuesta para debugging
            logger.debug(f"AI Response: {response.content}")

            # Limpiar y parsear respuesta JSON
            try:
                # Limpiar la respuesta para extraer solo el JSON
                content = response.content.strip()

                # Buscar el inicio y fin del JSON
                start_idx = content.find("{")
                end_idx = content.rfind("}") + 1

                if start_idx != -1 and end_idx > start_idx:
                    json_content = content[start_idx:end_idx]
                    intent_analysis = json.loads(json_content)

                    # Validar que tenga los campos requeridos
                    if "match_found" not in intent_analysis:
                        intent_analysis["match_found"] = False
                    if "reasoning" not in intent_analysis:
                        intent_analysis["reasoning"] = "Respuesta incompleta del modelo"

                    return intent_analysis
                else:
                    logger.error(
                        f"No se encontró JSON válido en la respuesta: {content}"
                    )
                    return {
                        "match_found": False,
                        "reasoning": "No se encontró JSON válido en la respuesta",
                    }

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse AI response as JSON: {response.content}")
                logger.error(f"JSON parsing error: {e}")

                # Intentar extraer información útil de la respuesta
                content = response.content.lower()
                if "match_found" in content and "true" in content:
                    return {
                        "match_found": True,
                        "reasoning": "Coincidencia detectada pero respuesta malformada",
                    }
                elif "match_found" in content and "false" in content:
                    return {
                        "match_found": False,
                        "reasoning": "No se encontró coincidencia",
                    }
                else:
                    return {
                        "match_found": False,
                        "reasoning": "Error parsing AI response - formato inesperado",
                    }

        except Exception as e:
            logger.error(f"Error analyzing user intent: {e}")

            # Intentar análisis de fallback simple
            try:
                fallback_result = self._fallback_intent_analysis(
                    user_question, available_functions
                )
                if fallback_result:
                    return fallback_result
            except Exception as fallback_error:
                logger.error(f"Fallback analysis also failed: {fallback_error}")

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
            # Crear un prompt más específico y útil
            param_prompt = f"""El usuario necesita proporcionar parámetros para la función '{function_name}'.

Parámetros faltantes: {', '.join(missing_params)}

Por favor, pide al usuario que proporcione los parámetros faltantes de una manera natural y conversacional en español.
Pide TODOS los parámetros faltantes de una vez para evitar múltiples interacciones.

Función: {function_name}
Parámetros faltantes: {missing_params}

Responde de manera amigable y útil, explicando qué información necesitas."""

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
                "message": f"Para ejecutar la función '{function_name}', necesito que me proporciones los siguientes parámetros: {', '.join(missing_params)}. Por favor, proporciona todos los valores necesarios.",
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

            # Ejecutar función HTTP directamente usando aiohttp
            import aiohttp

            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method=function_config.method,
                    url=final_url,
                    headers={"User-Agent": "Assistant-IA-API/1.0"},
                ) as response:
                    response.raise_for_status()
                    result = await response.json()

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

            # Usar user_id del perfil para almacenamiento
            user_id = profile.user_id or "default_user"

            # Verificar si el usuario está proporcionando parámetros para una función en progreso
            ongoing_function = self._detect_ongoing_function(user_id, user_message)
            if ongoing_function:
                # El usuario está proporcionando parámetros, procesarlos
                return await self._process_ongoing_function(
                    user_id, ongoing_function, user_message, available_functions
                )

            # Analizar intención del usuario con IA
            intent_analysis = await self._analyze_user_intent(
                user_message, available_functions
            )

            # Verificar que el análisis de intención sea válido
            if not isinstance(intent_analysis, dict):
                logger.error(f"Invalid intent analysis result: {intent_analysis}")
                return "Lo siento, tuve un problema al analizar tu solicitud. Por favor, intenta reformular tu pregunta."

            if not intent_analysis.get("match_found", False):
                reasoning = intent_analysis.get(
                    "reasoning",
                    "No se encontró una función que coincida con tu solicitud.",
                )
                return f"No encontré una función que coincida con tu solicitud. {reasoning}"

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

            # Combinar parámetros extraídos con los almacenados previamente
            stored_params = self._get_stored_function_params(
                user_id, matched_function.name
            )
            all_params = {**stored_params, **extracted_params}

            # Verificar si tenemos todos los parámetros requeridos
            if missing_params:
                # Almacenar los parámetros que ya tenemos
                if extracted_params:
                    self._store_function_params(
                        user_id, matched_function.name, extracted_params
                    )

                # Solicitar parámetros faltantes
                param_request = await self._get_missing_params_from_user(
                    missing_params, matched_function.name
                )
                return param_request["message"]

            # Ejecutar función según su tipo
            if matched_function.type == "simple":
                execution_result = await self._execute_simple_function(
                    matched_function, all_params
                )
            elif matched_function.type == "workflow":
                execution_result = await self._execute_workflow(
                    matched_function, all_params
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

    def _fallback_intent_analysis(
        self, user_question: str, available_functions: List[FunctionConfig]
    ) -> Optional[Dict[str, Any]]:
        """Análisis de intención de fallback usando búsqueda simple de palabras clave"""
        try:
            user_question_lower = user_question.lower()

            # Buscar coincidencias por nombre de función
            for func in available_functions:
                if func.name.lower() in user_question_lower:
                    # Intentar extraer parámetros básicos
                    extracted_params = self._extract_basic_params(user_question, func)

                    return {
                        "match_found": True,
                        "function_name": func.name,
                        "confidence": 0.7,
                        "reasoning": f"Coincidencia encontrada por nombre de función: {func.name}",
                        "missing_params": [],
                        "extracted_params": extracted_params,
                    }

                # Buscar por palabras clave
                if hasattr(func, "keywords") and func.keywords:
                    for keyword in func.keywords:
                        if keyword.lower() in user_question_lower:
                            # Intentar extraer parámetros básicos
                            extracted_params = self._extract_basic_params(
                                user_question, func
                            )

                            return {
                                "match_found": True,
                                "function_name": func.name,
                                "confidence": 0.6,
                                "reasoning": f"Coincidencia encontrada por palabra clave: {keyword}",
                                "missing_params": [],
                                "extracted_params": extracted_params,
                            }

                # Buscar por descripción
                if hasattr(func, "description") and func.description:
                    description_lower = func.description.lower()
                    if any(
                        word in description_lower
                        for word in user_question_lower.split()
                    ):
                        return {
                            "match_found": True,
                            "function_name": func.name,
                            "confidence": 0.5,
                            "reasoning": f"Coincidencia encontrada por descripción de la función",
                            "missing_params": [],
                            "extracted_params": {},
                        }

            return None

        except Exception as e:
            logger.error(f"Error in fallback intent analysis: {e}")
            return None

    def _detect_ongoing_function(
        self, user_id: str, user_message: str
    ) -> Optional[str]:
        """Detecta si el usuario está proporcionando parámetros para una función en progreso"""
        if user_id in self.function_params_storage:
            for function_name in self.function_params_storage[user_id]:
                # Verificar si el mensaje contiene números que podrían ser coordenadas
                import re

                numbers = re.findall(r"-?\d+\.?\d*", user_message)
                if len(numbers) >= 2:  # Al menos 2 números (lat, lon)
                    return function_name
        return None

    async def _process_ongoing_function(
        self,
        user_id: str,
        function_name: str,
        user_message: str,
        available_functions: List[FunctionConfig],
    ) -> str:
        """Procesa parámetros proporcionados para una función en progreso"""
        try:
            # Encontrar la función
            matched_function = None
            for func in available_functions:
                if func.name == function_name:
                    matched_function = func
                    break

            if not matched_function:
                return f"Error: No se pudo encontrar la función '{function_name}'"

            # Extraer parámetros del mensaje
            extracted_params = self._extract_basic_params(
                user_message, matched_function
            )

            # Combinar con parámetros almacenados previamente
            stored_params = self._get_stored_function_params(user_id, function_name)
            all_params = {**stored_params, **extracted_params}

            # Almacenar los nuevos parámetros
            if extracted_params:
                self._store_function_params(user_id, function_name, extracted_params)

            # Verificar si tenemos todos los parámetros requeridos
            required_params = self._extract_url_params(matched_function.url)
            missing_params = [
                param for param in required_params if param not in all_params
            ]

            if missing_params:
                # Aún faltan parámetros
                return f"Gracias por proporcionar esa información. Aún necesito: {', '.join(missing_params)}"
            else:
                # Tenemos todos los parámetros, ejecutar la función
                if matched_function.type == "simple":
                    execution_result = await self._execute_simple_function(
                        matched_function, all_params
                    )
                elif matched_function.type == "workflow":
                    execution_result = await self._execute_workflow(
                        matched_function, all_params
                    )
                else:
                    return f"Tipo de función no soportado: {matched_function.type}"

                if execution_result.get("success", False):
                    # Limpiar parámetros almacenados después de ejecutar exitosamente
                    self._clear_function_params(user_id, function_name)
                    return f"✅ Función '{function_name}' ejecutada exitosamente.\n\nResultado: {execution_result.get('result', 'Sin resultado')}"
                else:
                    return f"Error ejecutando {function_name}: {execution_result.get('error', 'Error desconocido')}"

        except Exception as e:
            logger.error(f"Error processing ongoing function: {e}")
            return (
                f"Lo siento, tuve un problema al procesar la función. Error: {str(e)}"
            )

    def _extract_basic_params(
        self, user_question: str, function_config: FunctionConfig
    ) -> Dict[str, str]:
        """Extrae parámetros básicos de la pregunta del usuario usando patrones simples"""
        try:
            extracted_params = {}
            user_question_lower = user_question.lower()

            # Buscar coordenadas en formato lat,lon o latitud,longitud
            import re

            # Patrón para coordenadas decimales
            coord_pattern = r"(-?\d+\.?\d*)\s*[,]\s*(-?\d+\.?\d*)"
            coord_match = re.search(coord_pattern, user_question)
            if coord_match:
                extracted_params["lat"] = coord_match.group(1)
                extracted_params["lon"] = coord_match.group(2)

            # Patrón para números individuales que podrían ser coordenadas
            numbers = re.findall(r"-?\d+\.?\d*", user_question)
            if len(numbers) >= 2 and "lat" not in extracted_params:
                # Asumir que los dos primeros números son lat y lon
                extracted_params["lat"] = numbers[0]
                extracted_params["lon"] = numbers[1]

            # Buscar idioma
            if "español" in user_question_lower or "spanish" in user_question_lower:
                extracted_params["accept-language"] = "es"
            elif "inglés" in user_question_lower or "english" in user_question_lower:
                extracted_params["accept-language"] = "en"
            elif "francés" in user_question_lower or "french" in user_question_lower:
                extracted_params["accept-language"] = "fr"

            # Buscar nivel de zoom
            if "detalle" in user_question_lower or "detail" in user_question_lower:
                extracted_params["addressdetails"] = "1"

            return extracted_params

        except Exception as e:
            logger.error(f"Error extracting basic params: {e}")
            return {}

    def _store_function_params(
        self, user_id: str, function_name: str, params: Dict[str, str]
    ):
        """Almacena parámetros de una función para un usuario específico"""
        if user_id not in self.function_params_storage:
            self.function_params_storage[user_id] = {}
        if function_name not in self.function_params_storage[user_id]:
            self.function_params_storage[user_id][function_name] = {}

        # Actualizar parámetros existentes
        self.function_params_storage[user_id][function_name].update(params)
        logger.debug(f"Stored params for {function_name}: {params}")

    def _get_stored_function_params(
        self, user_id: str, function_name: str
    ) -> Dict[str, str]:
        """Obtiene parámetros almacenados de una función para un usuario específico"""
        if (
            user_id in self.function_params_storage
            and function_name in self.function_params_storage[user_id]
        ):
            return self.function_params_storage[user_id][function_name].copy()
        return {}

    def _clear_function_params(self, user_id: str, function_name: str):
        """Limpia parámetros almacenados de una función para un usuario específico"""
        if (
            user_id in self.function_params_storage
            and function_name in self.function_params_storage[user_id]
        ):
            del self.function_params_storage[user_id][function_name]
            logger.debug(f"Cleared params for {function_name}")
