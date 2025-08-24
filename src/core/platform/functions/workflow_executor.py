import logging
import json
import aiohttp
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

        if workflow_name not in self.workflows:
            raise ValueError(f"Workflow '{workflow_name}' no encontrado")

        workflow = self.workflows[workflow_name]
        self.execution_context = input_params.copy()
        results = {}

        logger.info(f"Ejecutando workflow: {workflow_name}")

        try:
            for step in workflow["steps"]:
                step_result = await self._execute_step(step)
                if step_result:
                    results[step["name"]] = step_result
                    # Actualizar contexto con resultados del paso
                    self._update_context(step_result, step.get("response_mapping", {}))

                # Verificar condición para continuar
                if step.get("condition") and not self._evaluate_condition(
                    step["condition"], results
                ):
                    logger.info(f"Condición no cumplida en paso: {step['name']}")
                    break

        except Exception as e:
            logger.error(f"Error ejecutando workflow {workflow_name}: {e}")
            raise e

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
            # Preparar parámetros para la URL
            url = step["url"]
            for param, value in self.execution_context.items():
                url = url.replace(f"{{{param}}}", str(value))

            # Preparar body si es necesario
            body = None
            if step.get("body_template"):
                body = self._prepare_body(step["body_template"])

            # Ejecutar request HTTP
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
                    raise ValueError(f"Método HTTP no soportado: {step['method']}")

            logger.info(f"Paso '{step['name']}' ejecutado exitosamente")
            return result

        except Exception as e:
            logger.error(f"Error ejecutando paso '{step['name']}': {e}")
            return None

    def _prepare_body(self, body_template: str) -> Dict[str, Any]:
        """Prepara el body del request reemplazando variables del contexto"""
        try:
            body_str = body_template
            for param, value in self.execution_context.items():
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
            if condition.startswith("equals:"):
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
