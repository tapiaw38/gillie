#!/usr/bin/env python3
"""
Demostración del Sistema Inteligente de Funciones

Este script muestra cómo funciona el nuevo sistema que:
1. Analiza preguntas del usuario con IA
2. Encuentra coincidencias con funciones disponibles
3. Solicita parámetros faltantes
4. Ejecuta funciones simples o workflows
5. Maneja ejecución secuencial
"""

import asyncio
import json
from typing import Dict, Any

# Mock de las dependencias para la demostración
class MockConfigService:
    class OpenAIConfig:
        api_key = "mock-api-key"
        base_url = "https://api.openai.com/v1"
        model = "gpt-3.5-turbo"
    
    openai_config = OpenAIConfig()

class MockProfile:
    def __init__(self, functions_config: str):
        self.functions = functions_config

class MockSmartFunctionExecutor:
    """Mock del ejecutor inteligente para demostración"""
    
    def __init__(self):
        self.functions_config = self._load_example_config()
    
    def _load_example_config(self) -> str:
        """Cargar configuración de ejemplo"""
        config = [
            {
                "type": "simple",
                "sequential": False,
                "sequential_number": None,
                "name": "consultar_clima",
                "method": "GET",
                "body": None,
                "headers": "",
                "url": "https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current=temperature_2m"
            },
            {
                "type": "simple",
                "sequential": False,
                "sequential_number": None,
                "name": "buscar_productos",
                "method": "GET",
                "body": None,
                "headers": "",
                "url": "https://api.ejemplo.com/products?query={query}&category={category}&price_min={price_min}"
            },
            {
                "type": "workflow",
                "sequential": True,
                "sequential_number": 1,
                "name": "reserva_hotel",
                "method": "POST",
                "body": '{"city": "{city}", "check_in": "{check_in}", "check_out": "{check_out}", "guests": "{guests}"}',
                "headers": "Content-Type: application/json",
                "url": "https://api.ejemplo.com/hotels/search"
            }
        ]
        return json.dumps(config, indent=2, ensure_ascii=False)
    
    async def _analyze_user_intent(self, user_question: str) -> Dict[str, Any]:
        """Mock del análisis de intención del usuario"""
        print(f"🔍 Analizando pregunta del usuario: '{user_question}'")
        
        # Simular análisis de IA
        if "clima" in user_question.lower() or "temperatura" in user_question.lower():
            return {
                "match_found": True,
                "function_name": "consultar_clima",
                "confidence": 0.95,
                "reasoning": "La pregunta menciona clima o temperatura",
                "missing_params": ["latitude", "longitude"],
                "extracted_params": {}
            }
        elif "producto" in user_question.lower() or "buscar" in user_question.lower():
            return {
                "match_found": True,
                "function_name": "buscar_productos",
                "confidence": 0.90,
                "reasoning": "La pregunta menciona productos o búsqueda",
                "missing_params": ["query", "category"],
                "extracted_params": {}
            }
        elif "hotel" in user_question.lower() or "reserva" in user_question.lower():
            return {
                "match_found": True,
                "function_name": "reserva_hotel",
                "confidence": 0.88,
                "reasoning": "La pregunta menciona hotel o reserva",
                "missing_params": ["city", "check_in", "check_out", "guests"],
                "extracted_params": {}
            }
        else:
            return {
                "match_found": False,
                "reasoning": "No se encontró una función que coincida con la solicitud"
            }
    
    async def _get_missing_params_from_user(self, missing_params: list, function_name: str) -> Dict[str, Any]:
        """Mock de solicitud de parámetros faltantes"""
        print(f"❓ Función '{function_name}' requiere parámetros: {', '.join(missing_params)}")
        
        # Simular solicitud de parámetros
        param_request = f"Para ejecutar '{function_name}', necesito que me proporciones: {', '.join(missing_params)}"
        
        return {
            "message": param_request,
            "next_param": missing_params[0] if missing_params else None,
            "remaining_params": missing_params[1:] if len(missing_params) > 1 else []
        }
    
    async def _execute_simple_function(self, function_config: Dict[str, Any], params: Dict[str, str]) -> Dict[str, Any]:
        """Mock de ejecución de función simple"""
        print(f"🚀 Ejecutando función simple: {function_config['name']}")
        print(f"   URL: {function_config['url']}")
        print(f"   Parámetros: {params}")
        
        # Simular respuesta exitosa
        return {
            "success": True,
            "result": f"Resultado simulado de {function_config['name']}",
            "url_executed": function_config['url'],
            "type": "simple_function"
        }
    
    async def _execute_workflow(self, function_config: Dict[str, Any], params: Dict[str, str]) -> Dict[str, Any]:
        """Mock de ejecución de workflow"""
        print(f"🔄 Ejecutando workflow: {function_config['name']}")
        print(f"   Secuencial: {function_config['sequential']}")
        print(f"   Número: {function_config['sequential_number']}")
        print(f"   Parámetros: {params}")
        
        # Simular respuesta exitosa
        return {
            "success": True,
            "result": f"Workflow {function_config['name']} completado exitosamente",
            "type": "workflow"
        }
    
    async def execute_function(self, user_message: str, profile: MockProfile, chat_history: list = None) -> str:
        """Ejecutar función basada en el mensaje del usuario"""
        print(f"\n📝 Usuario dice: {user_message}")
        print("=" * 60)
        
        try:
            # Parsear configuración de funciones
            available_functions = json.loads(profile.functions)
            print(f"📋 Funciones disponibles: {len(available_functions)}")
            
            # Analizar intención del usuario con IA
            intent_analysis = await self._analyze_user_intent(user_message)
            
            if not intent_analysis.get("match_found", False):
                return f"❌ {intent_analysis.get('reasoning', 'No se encontró función')}"
            
            # Encontrar la función coincidente
            matched_function_name = intent_analysis.get("function_name")
            matched_function = None
            
            for func in available_functions:
                if func["name"] == matched_function_name:
                    matched_function = func
                    break
            
            if not matched_function:
                return f"❌ Error: No se pudo encontrar la función '{matched_function_name}'"
            
            print(f"✅ Función encontrada: {matched_function['name']} (tipo: {matched_function['type']})")
            
            # Verificar parámetros faltantes
            missing_params = intent_analysis.get("missing_params", [])
            extracted_params = intent_analysis.get("extracted_params", {})
            
            if missing_params:
                # Solicitar parámetros faltantes
                param_request = await self._get_missing_params_from_user(missing_params, matched_function["name"])
                return param_request["message"]
            
            # Ejecutar función según su tipo
            if matched_function["type"] == "simple":
                execution_result = await self._execute_simple_function(matched_function, extracted_params)
            elif matched_function["type"] == "workflow":
                execution_result = await self._execute_workflow(matched_function, extracted_params)
            else:
                return f"❌ Tipo de función no soportado: {matched_function['type']}"
            
            if not execution_result.get("success", False):
                return f"❌ Error ejecutando {matched_function['name']}: {execution_result.get('error', 'Error desconocido')}"
            
            # Generar respuesta amigable
            if matched_function["type"] == "simple":
                return f"✅ Función '{matched_function['name']}' ejecutada exitosamente.\n\nResultado: {execution_result.get('result', 'Sin resultado')}"
            else:
                return f"✅ Workflow '{matched_function['name']}' ejecutado exitosamente.\n\nResultado: {execution_result.get('result', 'Sin resultado')}"
                
        except Exception as e:
            print(f"❌ Error en ejecución: {e}")
            return f"❌ Lo siento, tuve un problema al procesar tu solicitud. Error: {str(e)}"
    
    def get_available_functions(self, profile: MockProfile) -> list:
        """Obtener información sobre funciones disponibles"""
        try:
            available_functions = json.loads(profile.functions)
            functions_info = []
            
            for func in available_functions:
                info = {
                    "name": func["name"],
                    "type": func["type"],
                    "sequential": func["sequential"],
                    "sequential_number": func["sequential_number"],
                    "method": func["method"],
                    "url": func["url"]
                }
                functions_info.append(info)
            
            return functions_info
            
        except Exception as e:
            print(f"❌ Error obteniendo funciones: {e}")
            return []

async def main():
    """Función principal de demostración"""
    print("🚀 DEMOSTRACIÓN DEL SISTEMA INTELIGENTE DE FUNCIONES")
    print("=" * 60)
    
    # Crear ejecutor mock
    executor = MockSmartFunctionExecutor()
    
    # Crear perfil de ejemplo
    profile = MockProfile(executor.functions_config)
    
    # Mostrar funciones disponibles
    print("\n📋 FUNCIONES DISPONIBLES:")
    functions = executor.get_available_functions(profile)
    for i, func in enumerate(functions, 1):
        print(f"   {i}. {func['name']} ({func['type']}) - {func['method']}")
        print(f"      Secuencial: {func['sequential']}")
        print(f"      URL: {func['url']}")
        print()
    
    # Ejemplos de preguntas del usuario
    test_questions = [
        "¿Cómo está el clima hoy?",
        "Quiero buscar productos de tecnología",
        "Necesito reservar un hotel en Madrid",
        "¿Qué hora es?"
    ]
    
    print("🧪 PRUEBAS DEL SISTEMA:")
    print("=" * 60)
    
    for question in test_questions:
        print(f"\n❓ Pregunta: {question}")
        response = await executor.execute_function(question, profile)
        print(f"🤖 Respuesta: {response}")
        print("-" * 40)
    
    print("\n✅ Demostración completada!")

if __name__ == "__main__":
    # Ejecutar demo
    asyncio.run(main())





