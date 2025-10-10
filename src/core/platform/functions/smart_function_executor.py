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

            if isinstance(functions_list, dict):
                functions_list = [functions_list]

            parsed_functions = []
            for func in functions_list:

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
                    ),
                )

                if hasattr(config, "keywords"):
                    config.keywords = func.get("keywords", [])
                if hasattr(config, "examples"):
                    config.examples = func.get("examples", [])
                if hasattr(config, "param_descriptions"):
                    config.param_descriptions = func.get("param_descriptions", {})

                parsed_functions.append(config)

                # Si es un workflow, registrarlo en el WorkflowExecutor
                if config.type == "workflow":
                    self.workflow_executor.register_workflow(config.name, func)
                    logger.info(f"Registered workflow: {config.name}")

                logger.debug(f"Successfully parsed function: {config.name}")

            return parsed_functions

        except Exception as e:
            logger.error(f"Error parsing functions configuration: {e}")
            logger.error(f"Functions string: {functions_string}")
            return []

    async def _analyze_user_intent(
        self, user_question: str, available_functions: List[FunctionConfig], chat_history: List[str] = None
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

            # Preparar contexto del historial si está disponible
            history_context = ""
            if chat_history and len(chat_history) > 0:
                # Tomar los últimos 4 mensajes para contexto
                recent_messages = chat_history[-4:] if len(chat_history) > 4 else chat_history
                history_context = "\n\nCONVERSATION HISTORY (recent messages):\n" + "\n".join(recent_messages)
                history_context += "\n\nIMPORTANT: Use the conversation history to understand context. For example:"
                history_context += "\n- If a booking was just created and user says a number, it might be the booking_id"
                history_context += "\n- If user says 'confirmar' or 'confirm', look for booking_id in previous messages"
                history_context += "\n- Extract any relevant IDs, dates, or parameters from the history"

            # Crear prompt con funciones disponibles
            prompt = self.intent_prompt.format(
                available_functions=json.dumps(functions_info, indent=2),
                user_question=user_question,
            ) + history_context

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
            # Ejecutar workflow usando el nombre y parámetros
            # El workflow ya debería estar registrado en workflow_executor
            logger.info(f"Executing workflow: {function_config.name} with params: {params}")

            result = await self.workflow_executor.execute_workflow(
                workflow_name=function_config.name,
                input_params=params
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
                logger.info(f"Ongoing function detected: {ongoing_function}, processing user response")
                # El usuario está proporcionando parámetros, procesarlos
                return await self._process_ongoing_function(
                    user_id, ongoing_function, user_message, available_functions
                )
            else:
                logger.info("No ongoing function detected, analyzing as new request")

            # Analizar intención del usuario con IA
            logger.info(f"Analyzing user intent for message: {user_message[:100]}...")
            intent_analysis = await self._analyze_user_intent(
                user_message, available_functions, chat_history
            )

            logger.info(f"Intent analysis result: {intent_analysis}")

            # Verificar que el análisis de intención sea válido
            if not isinstance(intent_analysis, dict):
                logger.error(f"Invalid intent analysis result: {intent_analysis}")
                return "Lo siento, tuve un problema al analizar tu solicitud. Por favor, intenta reformular tu pregunta."

            if not intent_analysis.get("match_found", False):
                reasoning = intent_analysis.get(
                    "reasoning",
                    "No se encontró una función que coincida con tu solicitud.",
                )
                logger.info(f"No function match found. Reasoning: {reasoning}")
                return f"No encontré una función que coincida con tu solicitud. {reasoning}"

            # Encontrar la función coincidente
            matched_function_name = intent_analysis.get("function_name")
            logger.info(f"Matched function name: {matched_function_name}")
            matched_function = None

            for func in available_functions:
                if func.name == matched_function_name:
                    matched_function = func
                    logger.info(f"Found matched function: {func.name}, type: {func.type}")
                    break

            if not matched_function:
                logger.error(f"Function '{matched_function_name}' not found in configuration")
                return f"Error: No se pudo encontrar la función '{matched_function_name}' en la configuración."

            # Verificar parámetros faltantes
            missing_params = intent_analysis.get("missing_params", [])
            extracted_params = intent_analysis.get("extracted_params", {})

            logger.info(f"Missing params: {missing_params}, Extracted params: {extracted_params}")

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
            logger.info(f"Executing function type: {matched_function.type}, name: {matched_function.name}")
            if matched_function.type == "simple":
                logger.info(f"Calling _execute_simple_function with params: {all_params}")
                execution_result = await self._execute_simple_function(
                    matched_function, all_params
                )
            elif matched_function.type == "workflow":
                logger.info(f"Calling _execute_workflow with params: {all_params}")
                execution_result = await self._execute_workflow(
                    matched_function, all_params
                )
                logger.info(f"Workflow execution result: {execution_result}")
            else:
                logger.error(f"Unsupported function type: {matched_function.type}")
                return f"Tipo de función no soportado: {matched_function.type}"

            if not execution_result.get("success", False):
                logger.error(f"Function execution failed: {execution_result}")
                return f"Error ejecutando {matched_function.name}: {execution_result.get('error', 'Error desconocido')}"

            logger.info(f"Function executed successfully: {matched_function.name}")

            # Generar respuesta amigable usando IA
            friendly_response = await self._generate_friendly_response(
                matched_function.name,
                matched_function.type,
                execution_result,
                all_params
            )
            return friendly_response

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
            # Si hay parámetros almacenados, significa que hay una función en progreso
            # Retornar la primera función que tenga parámetros almacenados
            for function_name, params in self.function_params_storage[user_id].items():
                if params:  # Si hay parámetros almacenados
                    logger.info(f"Detected ongoing function: {function_name} with stored params: {params}")
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
            logger.info(f"Processing ongoing function: {function_name}")
            # Encontrar la función
            matched_function = None
            for func in available_functions:
                if func.name == function_name:
                    matched_function = func
                    break

            if not matched_function:
                logger.error(f"Function {function_name} not found in available functions")
                return f"Error: No se pudo encontrar la función '{function_name}'"

            # Obtener parámetros almacenados
            stored_params = self._get_stored_function_params(user_id, function_name)
            logger.info(f"Stored params for {function_name}: {stored_params}")

            # Extraer parámetros del mensaje
            extracted_params = self._extract_basic_params(
                user_message, matched_function
            )
            logger.info(f"Extracted params from message: {extracted_params}")

            # Determinar parámetros requeridos según el tipo de función
            if matched_function.type == "workflow":
                # Para workflows, obtener del registro
                if function_name in self.workflow_executor.workflows:
                    workflow = self.workflow_executor.workflows[function_name]
                    required_params = workflow.get("input_params", [])
                else:
                    required_params = []
            else:
                required_params = self._extract_url_params(matched_function.url)

            logger.info(f"Required params: {required_params}")

            # Combinar parámetros
            all_params = {**stored_params, **extracted_params}

            # Calcular parámetros faltantes
            missing_params = [
                param for param in required_params if param not in all_params
            ]
            logger.info(f"Missing params: {missing_params}, All params: {all_params}")

            # Si solo falta un parámetro y no se extrajo nada, asumir que el mensaje es ese parámetro
            if len(missing_params) == 1 and not extracted_params:
                missing_param = missing_params[0]
                # Intentar usar el mensaje como valor del parámetro faltante
                extracted_params[missing_param] = user_message.strip()
                all_params[missing_param] = user_message.strip()
                logger.info(f"Assumed message is for missing param '{missing_param}': {user_message.strip()}")
                missing_params = []

            # Almacenar los nuevos parámetros
            if extracted_params:
                self._store_function_params(user_id, function_name, extracted_params)
                logger.info(f"Stored new params: {extracted_params}")

            if missing_params:
                # Aún faltan parámetros
                logger.info(f"Still missing params: {missing_params}")
                return f"Gracias por proporcionar esa información. Aún necesito: {', '.join(missing_params)}"
            else:
                logger.info(f"All params collected, executing {matched_function.type}: {function_name}")
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

            # Buscar fechas - múltiples formatos
            # Patrón para check-in / checkin / entrada / llegada
            checkin_patterns = [
                r'check[\s-]?in[:\s]+(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{4})',
                r'entrada[:\s]+(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{4})',
                r'llegada[:\s]+(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{4})',
            ]
            for pattern in checkin_patterns:
                match = re.search(pattern, user_question_lower)
                if match:
                    extracted_params["check_in"] = match.group(1)
                    logger.debug(f"Extracted check_in date: {match.group(1)}")
                    break

            # Patrón para check-out / checkout / salida
            checkout_patterns = [
                r'check[\s-]?out[:\s]+(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{4})',
                r'salida[:\s]+(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{4})',
            ]
            for pattern in checkout_patterns:
                match = re.search(pattern, user_question_lower)
                if match:
                    extracted_params["check_out"] = match.group(1)
                    logger.debug(f"Extracted check_out date: {match.group(1)}")
                    break

            # Buscar número de huéspedes / guests
            guests_patterns = [
                r'hu[eé]spedes?[:\s]+(\d+)',
                r'guests?[:\s]+(\d+)',
                r'personas?[:\s]+(\d+)',
                r'(\d+)\s+hu[eé]spedes?',
                r'(\d+)\s+guests?',
                r'(\d+)\s+personas?',
            ]
            for pattern in guests_patterns:
                match = re.search(pattern, user_question_lower)
                if match:
                    extracted_params["guests"] = match.group(1)
                    logger.debug(f"Extracted guests: {match.group(1)}")
                    break

            # Buscar room_id / habitación
            room_patterns = [
                r'habitaci[oó]n[:\s]+n[uú]mero[:\s]+(\d+)',
                r'habitaci[oó]n[:\s]+(\d+)',
                r'room[:\s]+(\d+)',
                r'room[\s_]id[:\s]+(\d+)',
            ]
            for pattern in room_patterns:
                match = re.search(pattern, user_question_lower)
                if match:
                    extracted_params["room_id"] = match.group(1)
                    logger.debug(f"Extracted room_id: {match.group(1)}")
                    break

            # Buscar nombre (guest_name) - extraer palabras antes del email o teléfono
            # Patrón simple: nombre apellido seguido de email o teléfono
            name_patterns = [
                r'^([A-ZÑÁÉÍÓÚ][a-zñáéíóú]+(?:\s+[A-ZÑÁÉÍÓÚ][a-zñáéíóú]+)+)',  # Nombre Apellido capitalizado
                r'nombre[:\s]+([A-ZÑÁÉÍÓÚ][a-zñáéíóú]+(?:\s+[A-ZÑÁÉÍÓÚ][a-zñáéíóú]+)*)',
                r'llamo[:\s]+([A-ZÑÁÉÍÓÚ][a-zñáéíóú]+(?:\s+[A-ZÑÁÉÍÓÚ][a-zñáéíóú]+)*)',
            ]
            for pattern in name_patterns:
                match = re.search(pattern, user_question)
                if match:
                    extracted_params["guest_name"] = match.group(1).strip()
                    logger.debug(f"Extracted guest_name: {match.group(1)}")
                    break

            # Buscar email
            email_pattern = r'\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b'
            email_match = re.search(email_pattern, user_question)
            if email_match:
                extracted_params["email"] = email_match.group(1)
                logger.debug(f"Extracted email: {email_match.group(1)}")

            # Buscar teléfono
            phone_pattern = r'(\+?\d{1,3}[\s-]?\d{3,4}[\s-]?\d{6,7})'
            phone_match = re.search(phone_pattern, user_question)
            if phone_match:
                extracted_params["phone"] = phone_match.group(1).replace(" ", "").replace("-", "")
                logger.debug(f"Extracted phone: {phone_match.group(1)}")

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

            # Buscar booking_id / reserva id
            booking_id_patterns = [
                r'reserva[:\s]+n[uú]mero[:\s]+(\d+)',
                r'reserva[:\s]+(\d+)',
                r'booking[:\s]+(\d+)',
                r'booking[\s_]id[:\s]+(\d+)',
                r'id[:\s]+(\d+)',
            ]
            for pattern in booking_id_patterns:
                match = re.search(pattern, user_question_lower)
                if match:
                    extracted_params["booking_id"] = match.group(1)
                    logger.debug(f"Extracted booking_id: {match.group(1)}")
                    break

            return extracted_params

        except Exception as e:
            logger.error(f"Error extracting basic params: {e}")
            return {}

    async def _generate_friendly_response(
        self,
        function_name: str,
        function_type: str,
        execution_result: Dict[str, Any],
        params: Dict[str, str]
    ) -> str:
        """Genera una respuesta amigable y natural usando IA basada en el resultado de la ejecución"""
        try:
            logger.info(f"[FRIENDLY_RESPONSE] Generating friendly response for {function_name}")

            # Preparar el contexto de ejecución para el LLM
            result_data = execution_result.get('result', {})

            # Si es un workflow, extraer información relevante
            if function_type == "workflow":
                context_data = result_data.get('context', {})
                steps_executed = result_data.get('steps_executed', [])
                status = result_data.get('status', 'unknown')
                final_result = result_data.get('final_result', {})

                # Determinar si hubo un error real
                has_error = not steps_executed or len(final_result) == 0

                context_str = f"""
Tipo: Workflow
Nombre: {function_name}
Estado: {status}
Pasos ejecutados exitosamente: {', '.join(steps_executed) if steps_executed else 'NINGUNO - ERROR'}
Resultados de pasos: {json.dumps(final_result, indent=2, ensure_ascii=False) if final_result else 'VACÍO - ERROR'}
Parámetros utilizados: {json.dumps(params, indent=2, ensure_ascii=False)}
Error detectado: {'SÍ - No se ejecutaron pasos correctamente' if has_error else 'NO - Ejecución exitosa'}
"""
            else:
                # Función simple
                context_str = f"""
Tipo: Función simple
Nombre: {function_name}
Parámetros utilizados: {json.dumps(params, indent=2, ensure_ascii=False)}
Resultado: {json.dumps(result_data, indent=2, ensure_ascii=False)}
"""

            # Crear prompt para generar respuesta amigable
            prompt = f"""Eres un asistente que genera respuestas naturales y amigables basadas en los resultados de operaciones técnicas.

Operación ejecutada:
{context_str}

INSTRUCCIONES CRÍTICAS:
1. PRIMERO revisa si dice "Error detectado: SÍ" o si "Pasos ejecutados" es "NINGUNO - ERROR"
2. Si hay error: Genera una respuesta que informe al usuario que hubo un problema técnico y no se pudo completar la operación
3. Si NO hay error y hay pasos ejecutados exitosos: Confirma el éxito de manera clara y concisa
4. Incluye los detalles más relevantes de forma conversacional
5. No incluyas JSON ni datos técnicos crudos
6. La respuesta debe ser directa, sin introducciones innecesarias

EJEMPLOS DE RESPUESTAS PARA ÉXITO:
- "¡Reserva confirmada! He procesado tu reserva para Walter Tapia del 1 al 3 de enero de 2026 en la habitación 2 para 2 huéspedes."
- "He buscado la ubicación de San Salvador de Jujuy. Se encuentra en las coordenadas -24.1857, -65.2995."

EJEMPLOS DE RESPUESTAS PARA ERROR:
- "Lo siento, hubo un problema técnico al intentar procesar la reserva. Por favor intenta nuevamente en unos momentos."
- "No pude completar la operación debido a un error de conexión. Por favor verifica los datos e intenta nuevamente."

Genera la respuesta amigable ahora:"""

            # Generar respuesta usando el LLM
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            friendly_text = response.content.strip()

            logger.info(f"[FRIENDLY_RESPONSE] Generated: {friendly_text}")
            return friendly_text

        except Exception as e:
            logger.error(f"[FRIENDLY_RESPONSE] Error generating friendly response: {e}", exc_info=True)
            # Fallback a respuesta básica
            if function_type == "workflow":
                return f"✅ Operación '{function_name}' completada exitosamente."
            else:
                return f"✅ Función '{function_name}' ejecutada exitosamente."

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
