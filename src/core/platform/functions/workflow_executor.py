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
    """Ejecuta workflows complejos paso a paso"""

    def __init__(self, config_service=None):
        self.config_service = config_service
        self.execution_context = {}
        # Inicializar workflows vacíos por defecto
        self.workflows = {}

    def get_available_workflows(self) -> List[str]:
        """Retorna lista de workflows disponibles"""
        return list(self.workflows.keys())
    
    def register_workflow(self, name: str, workflow: Dict[str, Any]):
        """Registra un nuevo workflow"""
        self.workflows[name] = workflow

    def get_workflow_info(self, workflow_name: str) -> Optional[Dict[str, Any]]:
        """Obtiene información de un workflow específico"""
        if workflow_name in self.workflows:
            workflow = self.workflows[workflow_name]
            return {
                "name": workflow["name"],
                "description": workflow["description"],
                "input_params": workflow["input_params"],
                "examples": workflow["examples"],
                "keywords": workflow["keywords"],
            }
        return None

    async def execute_workflow(
        self, workflow_name: str, input_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Ejecuta un workflow completo paso a paso"""

        logger.info(f"[WORKFLOW] Starting workflow execution: {workflow_name}")
        logger.info(f"[WORKFLOW] Input params: {input_params}")

        if workflow_name not in self.workflows:
            logger.error(f"[WORKFLOW] Workflow '{workflow_name}' not found in registry")
            logger.error(f"[WORKFLOW] Available workflows: {list(self.workflows.keys())}")
            raise ValueError(f"Workflow '{workflow_name}' no encontrado")

        workflow = self.workflows[workflow_name]
        logger.info(f"[WORKFLOW] Workflow found with {len(workflow.get('steps', []))} steps")
        self.execution_context = input_params.copy()
        results = {}

        logger.info(f"[WORKFLOW] Ejecutando workflow: {workflow_name}")
        logger.info(f"[WORKFLOW] Execution context: {self.execution_context}")

        try:
            for idx, step in enumerate(workflow["steps"]):
                logger.info(f"[WORKFLOW] Executing step {idx + 1}/{len(workflow['steps'])}: {step['name']}")
                logger.info(f"[WORKFLOW] Step URL: {step['url']}, Method: {step['method']}")

                step_result = await self._execute_step(step)

                if step_result:
                    logger.info(f"[WORKFLOW] Step '{step['name']}' completed successfully")
                    logger.info(f"[WORKFLOW] Step result: {step_result}")
                    results[step["name"]] = step_result
                    # Actualizar contexto con resultados del paso
                    self._update_context(step_result, step.get("response_mapping", {}))
                    logger.info(f"[WORKFLOW] Updated context: {self.execution_context}")
                else:
                    logger.warning(f"[WORKFLOW] Step '{step['name']}' returned no result")

                # Verificar condición para continuar
                if step.get("condition"):
                    logger.info(f"[WORKFLOW] Evaluating condition: {step['condition']}")
                    condition_met = self._evaluate_condition(step["condition"], results)
                    logger.info(f"[WORKFLOW] Condition result: {condition_met}")

                    if not condition_met:
                        logger.info(f"[WORKFLOW] Condición no cumplida en paso: {step['name']}, stopping workflow")
                        break

        except Exception as e:
            logger.error(f"[WORKFLOW] Error ejecutando workflow {workflow_name}: {e}", exc_info=True)
            raise e

        logger.info(f"[WORKFLOW] Workflow completed: {workflow_name}")
        logger.info(f"[WORKFLOW] Steps executed: {list(results.keys())}")

        return {
            "workflow_name": workflow_name,
            "status": "completed",
            "steps_executed": list(results.keys()),
            "final_result": results,
            "context": self.execution_context,
        }

    async def _execute_step(self, step: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Ejecuta un paso individual del workflow"""

        try:
            logger.info(f"[STEP] Preparing step execution: {step['name']}")
            # Preparar parámetros para la URL
            url = step["url"]
            logger.info(f"[STEP] Original URL template: {url}")

            for param, value in self.execution_context.items():
                # Detectar y convertir fechas también en URLs si es necesario
                date_params = ['check_in', 'check_out', 'fecha', 'date', 'inicio', 'fin',
                              'start_date', 'end_date', 'booking_date', 'reservation_date']

                if any(date_param in param.lower() for date_param in date_params):
                    converted_value = self._detect_and_convert_date(str(value))
                    url = url.replace(f"{{{param}}}", converted_value)
                    logger.debug(f"[STEP] Replaced date param {{{param}}} with {converted_value}")
                else:
                    url = url.replace(f"{{{param}}}", str(value))
                    logger.debug(f"[STEP] Replaced param {{{param}}} with {value}")

            # Reemplazar localhost con host.docker.internal para acceder al host desde Docker
            url = url.replace('localhost:', 'host.docker.internal:')
            logger.debug(f"[STEP] Replaced localhost with host.docker.internal if present")

            # Asegurar que la URL tenga esquema HTTP/HTTPS
            if not url.startswith(('http://', 'https://')):
                url = f"http://{url}"
                logger.info(f"[STEP] Added http:// scheme to URL: {url}")

            logger.info(f"[STEP] Final URL: {url}")

            # Preparar body si es necesario
            body = None
            if step.get("body_template"):
                logger.info(f"[STEP] Preparing body from template")
                body = self._prepare_body(step["body_template"])
                logger.info(f"[STEP] Request body: {body}")

            # Ejecutar request HTTP
            logger.info(f"[STEP] Making HTTP {step['method'].upper()} request to {url}")
            async with aiohttp.ClientSession() as session:
                if step["method"].upper() == "GET":
                    async with session.get(url) as response:
                        logger.info(f"[STEP] GET response status: {response.status}")
                        response.raise_for_status()
                        result = await response.json()
                        logger.info(f"[STEP] GET response: {result}")
                elif step["method"].upper() == "POST":
                    async with session.post(url, json=body) as response:
                        logger.info(f"[STEP] POST response status: {response.status}")
                        response.raise_for_status()
                        result = await response.json()
                        logger.info(f"[STEP] POST response: {result}")
                elif step["method"].upper() == "PUT":
                    async with session.put(url, json=body) as response:
                        logger.info(f"[STEP] PUT response status: {response.status}")
                        response.raise_for_status()
                        result = await response.json()
                        logger.info(f"[STEP] PUT response: {result}")
                elif step["method"].upper() == "DELETE":
                    async with session.delete(url) as response:
                        logger.info(f"[STEP] DELETE response status: {response.status}")
                        response.raise_for_status()
                        result = await response.json()
                        logger.info(f"[STEP] DELETE response: {result}")
                else:
                    logger.error(f"[STEP] Unsupported HTTP method: {step['method']}")
                    raise ValueError(f"Método HTTP no soportado: {step['method']}")

            logger.info(f"[STEP] Paso '{step['name']}' ejecutado exitosamente")
            return result

        except Exception as e:
            logger.error(f"[STEP] Error ejecutando paso '{step['name']}': {e}", exc_info=True)
            return None

    @staticmethod
    def _detect_and_convert_date(value: str) -> str:
        """
        Detecta y convierte diferentes formatos de fecha a ISO 8601 (YYYY-MM-DD)

        Formatos soportados:
        - DD/MM/YYYY o DD-MM-YYYY (ej: 01/01/2026, 15-03-2025)
        - MM/DD/YYYY o MM-DD-YYYY (ej: 01/15/2026, 03-15-2025)
        - YYYY/MM/DD o YYYY-MM-DD (ej: 2026/01/01, 2025-03-15)
        - DD.MM.YYYY (ej: 01.01.2026)
        """
        if not isinstance(value, str):
            return str(value)

        value_stripped = value.strip()

        # Patrones de fecha comunes
        patterns = [
            # DD/MM/YYYY o DD-MM-YYYY (día 01-31, mes 01-12)
            (r'^(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})$', 'DMY'),
            # YYYY/MM/DD o YYYY-MM-DD
            (r'^(\d{4})[/\-.](\d{1,2})[/\-.](\d{1,2})$', 'YMD'),
        ]

        for pattern, format_type in patterns:
            match = re.match(pattern, value_stripped)
            if match:
                try:
                    if format_type == 'DMY':
                        day, month, year = match.groups()
                        # Validar que sea una fecha válida
                        date_obj = datetime(int(year), int(month), int(day))
                        return date_obj.strftime('%Y-%m-%d')
                    elif format_type == 'YMD':
                        year, month, day = match.groups()
                        # Validar que sea una fecha válida
                        date_obj = datetime(int(year), int(month), int(day))
                        return date_obj.strftime('%Y-%m-%d')
                except (ValueError, TypeError):
                    # Si falla la conversión, intentar con el siguiente patrón
                    continue

        # Si no coincide con ningún patrón, devolver el valor original
        return value_stripped

    def _prepare_body(self, body_template: str) -> Dict[str, Any]:
        """Prepara el body del request reemplazando variables del contexto"""
        try:
            body_str = body_template
            for param, value in self.execution_context.items():
                # Detectar parámetros de fecha y convertirlos
                # Parámetros comunes que contienen fechas
                date_params = ['check_in', 'check_out', 'fecha', 'date', 'inicio', 'fin',
                              'start_date', 'end_date', 'booking_date', 'reservation_date']

                if any(date_param in param.lower() for date_param in date_params):
                    # Intentar convertir el valor a formato ISO
                    converted_value = self._detect_and_convert_date(str(value))
                    body_str = body_str.replace(f"{{{param}}}", converted_value)
                    logger.debug(f"Converted date parameter '{param}': {value} -> {converted_value}")
                else:
                    body_str = body_str.replace(f"{{{param}}}", str(value))

            return json.loads(body_str)
        except Exception as e:
            logger.error(f"Error preparando body: {e}")
            return {}

    def _update_context(
        self, step_result: Dict[str, Any], response_mapping: Dict[str, str]
    ):
        """Actualiza el contexto de ejecución con los resultados del paso"""
        for context_key, response_path in response_mapping.items():
            try:
                # Extraer valor del resultado usando el path (ej: "customer.name")
                value = self._extract_nested_value(step_result, response_path)
                self.execution_context[context_key] = value
            except Exception as e:
                logger.warning(f"No se pudo extraer {response_path}: {e}")

    def _extract_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """Extrae valor anidado usando path con puntos (ej: 'customer.name')"""
        keys = path.split(".")
        current = data

        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                raise KeyError(f"Path '{path}' no válido en datos")

        return current

    def _evaluate_condition(self, condition: str, results: Dict[str, Any]) -> bool:
        """Evalúa una condición del workflow"""
        try:
            # Soportar formato simple con operadores: "key == value", "key != value"
            if "==" in condition:
                parts = condition.split("==", 1)
                key = parts[0].strip()
                expected_value = parts[1].strip().strip("'\"")
                actual_value = self.execution_context.get(key)

                # Manejar booleanos
                if expected_value.lower() in ("true", "false"):
                    expected_value = expected_value.lower() == "true"
                    return actual_value == expected_value

                return str(actual_value) == expected_value

            elif "!=" in condition:
                parts = condition.split("!=", 1)
                key = parts[0].strip()
                expected_value = parts[1].strip().strip("'\"")
                actual_value = self.execution_context.get(key)

                # Manejar null
                if expected_value.lower() == "null":
                    return actual_value is not None

                return str(actual_value) != expected_value

            # Formatos antiguos con prefijos
            elif condition.startswith("equals:"):
                # Formato: "equals:key=value"
                key_value = condition.split(":", 1)[1]
                key, expected_value = key_value.split("=", 1)
                actual_value = self.execution_context.get(key)
                return str(actual_value) == expected_value

            elif condition.startswith("exists:"):
                # Formato: "exists:key"
                key = condition.split(":", 1)[1]
                return (
                    key in self.execution_context
                    and self.execution_context[key] is not None
                )

            elif condition.startswith("greater_than:"):
                # Formato: "greater_than:key=value"
                key_value = condition.split(":", 1)[1]
                key, threshold = key_value.split("=", 1)
                actual_value = self.execution_context.get(key)
                return actual_value and float(actual_value) > float(threshold)

            else:
                logger.warning(f"Condición no reconocida: {condition}")
                return True

        except Exception as e:
            logger.error(f"Error evaluando condición '{condition}': {e}")
            return True

    def convert_workflow_to_function(self, workflow_name: str) -> Dict[str, Any]:
        """Convierte un workflow en una función compatible con el sistema"""

        if workflow_name not in self.workflows:
            raise ValueError(f"Workflow '{workflow_name}' no encontrado")

        workflow = self.workflows[workflow_name]

        return {
            "name": workflow["name"],
            "description": workflow["description"],
            "url": f"workflow://{workflow_name}",
            "method": "WORKFLOW",
            "param_types": {param: "string" for param in workflow["input_params"]},
            "param_descriptions": {
                param: f"Parámetro de entrada: {param}"
                for param in workflow["input_params"]
            },
            "examples": workflow["examples"],
            "keywords": workflow["keywords"],
            "workflow_type": workflow_name,
        }


# Instancia global del ejecutor de workflows
workflow_executor = WorkflowExecutor()
