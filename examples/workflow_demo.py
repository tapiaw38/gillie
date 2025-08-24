#!/usr/bin/env python3
"""
Demo del Sistema de Flujos de Trabajo Secuenciales

Este script demuestra cómo usar el nuevo sistema de flujos de trabajo que permite
ejecutar múltiples endpoints en secuencia, donde cada paso depende del anterior.
"""

import asyncio
import json
from unittest.mock import Mock
from src.core.platform.functions.workflow_executor import WorkflowExecutor, WorkflowDefinition, WorkflowStep
from src.core.platform.functions.workflow_examples import (
    HOTEL_BOOKING_WORKFLOW,
    PRODUCT_ANALYSIS_WORKFLOW,
    CREDIT_APPROVAL_WORKFLOW
)


class MockConfigService:
    """Mock del servicio de configuración para demostración"""
    class OpenAIConfig:
        api_key = "demo_key"
        base_url = "https://api.openai.com"
        model = "gpt-3.5-turbo"
    
    openai_config = OpenAIConfig()


async def demo_hotel_booking_workflow():
    """Demo del flujo de trabajo de reserva de hotel"""
    print("🏨 Demo: Flujo de Trabajo de Reserva de Hotel")
    print("=" * 60)
    
    # Crear ejecutor de flujos de trabajo
    config_service = MockConfigService()
    executor = WorkflowExecutor(config_service)
    
    # Crear definición del flujo de trabajo
    workflow = WorkflowDefinition(
        name=HOTEL_BOOKING_WORKFLOW["name"],
        description=HOTEL_BOOKING_WORKFLOW["description"],
        steps=[
            WorkflowStep(
                name=step["name"],
                description=step["description"],
                url=step["url"],
                method=step["method"],
                required_params=step["required_params"],
                response_mapping=step["response_mapping"],
                condition=step.get("condition"),
                body_template=step.get("body_template")
            )
            for step in HOTEL_BOOKING_WORKFLOW["steps"]
        ],
        input_params=HOTEL_BOOKING_WORKFLOW["input_params"]
    )
    
    print("📋 Flujo de trabajo configurado:")
    print(f"   Nombre: {workflow.name}")
    print(f"   Descripción: {workflow.description}")
    print(f"   Pasos: {len(workflow.steps)}")
    print(f"   Parámetros de entrada: {', '.join(workflow.input_params)}")
    print()
    
    # Mostrar pasos del flujo
    print("🔧 Pasos del flujo de trabajo:")
    for i, step in enumerate(workflow.steps, 1):
        print(f"   {i}. {step.name}")
        print(f"      Descripción: {step.description}")
        print(f"      URL: {step.url}")
        print(f"      Método: {step.method}")
        print(f"      Parámetros requeridos: {', '.join(step.required_params)}")
        if step.response_mapping:
            print(f"      Mapeo de respuesta: {step.response_mapping}")
        if step.condition:
            print(f"      Condición: {step.condition}")
        print()
    
    # Simular ejecución del flujo
    print("💬 Ejecución simulada del flujo:")
    user_params = {
        "destination": "Madrid",
        "check_in": "2024-12-15",
        "check_out": "2024-12-20",
        "guests": "2"
    }
    
    print("   Parámetros del usuario:")
    for param, value in user_params.items():
        print(f"      {param}: {value}")
    print()
    
    print("   [Simulado] Ejecutando flujo de trabajo...")
    print("   [Simulado] Paso 1: Buscando hoteles en Madrid...")
    print("   [Simulado] Paso 2: Verificando disponibilidad...")
    print("   [Simulado] Paso 3: Creando reserva...")
    print("   [Simulado] Flujo completado exitosamente")


async def demo_product_analysis_workflow():
    """Demo del flujo de trabajo de análisis de productos"""
    print("📱 Demo: Flujo de Trabajo de Análisis de Productos")
    print("=" * 60)
    
    workflow = WorkflowDefinition(
        name=PRODUCT_ANALYSIS_WORKFLOW["name"],
        description=PRODUCT_ANALYSIS_WORKFLOW["description"],
        steps=[
            WorkflowStep(
                name=step["name"],
                description=step["description"],
                url=step["url"],
                method=step["method"],
                required_params=step["required_params"],
                response_mapping=step["response_mapping"],
                condition=step.get("condition"),
                body_template=step.get("body_template")
            )
            for step in PRODUCT_ANALYSIS_WORKFLOW["steps"]
        ],
        input_params=PRODUCT_ANALYSIS_WORKFLOW["input_params"]
    )
    
    print("📋 Flujo de trabajo configurado:")
    print(f"   Nombre: {workflow.name}")
    print(f"   Descripción: {workflow.description}")
    print(f"   Pasos: {len(workflow.steps)}")
    print()
    
    # Mostrar flujo de datos entre pasos
    print("🔄 Flujo de datos entre pasos:")
    print("   Usuario → Paso 1: Obtener info del producto")
    print("   Paso 1 → Paso 2: product_id, brand, model")
    print("   Paso 2 → Paso 3: product_id")
    print("   Paso 3 → Paso 4: product_id")
    print("   Paso 4 → Paso 5: Todos los precios")
    print("   Paso 5 → Usuario: Recomendación final")
    print()
    
    # Simular ejecución
    user_params = {
        "product_name": "iPhone 15",
        "category": "smartphones"
    }
    
    print("💬 Ejecución simulada:")
    print(f"   Producto: {user_params['product_name']}")
    print(f"   Categoría: {user_params['category']}")
    print()
    print("   [Simulado] Paso 1: Obteniendo información del iPhone 15...")
    print("   [Simulado] Paso 2: Buscando precios en Amazon...")
    print("   [Simulado] Paso 3: Buscando precios en eBay...")
    print("   [Simulado] Paso 4: Buscando precios en tiendas locales...")
    print("   [Simulado] Paso 5: Generando comparación y recomendación...")
    print("   [Simulado] Flujo completado exitosamente")


async def demo_credit_approval_workflow():
    """Demo del flujo de trabajo de aprobación de crédito"""
    print("💳 Demo: Flujo de Trabajo de Aprobación de Crédito")
    print("=" * 60)
    
    workflow = WorkflowDefinition(
        name=CREDIT_APPROVAL_WORKFLOW["name"],
        description=CREDIT_APPROVAL_WORKFLOW["description"],
        steps=[
            WorkflowStep(
                name=step["name"],
                description=step["description"],
                url=step["url"],
                method=step["method"],
                required_params=step["required_params"],
                response_mapping=step["response_mapping"],
                condition=step.get("condition"),
                body_template=step.get("body_template")
            )
            for step in CREDIT_APPROVAL_WORKFLOW["steps"]
        ],
        input_params=CREDIT_APPROVAL_WORKFLOW["input_params"]
    )
    
    print("📋 Flujo de trabajo configurado:")
    print(f"   Nombre: {workflow.name}")
    print(f"   Descripción: {workflow.description}")
    print(f"   Pasos: {len(workflow.steps)}")
    print()
    
    # Mostrar condiciones y dependencias
    print("🔍 Condiciones y dependencias:")
    for i, step in enumerate(workflow.steps, 1):
        if step.condition:
            print(f"   Paso {i} ({step.name}): {step.condition}")
        else:
            print(f"   Paso {i} ({step.name}): Sin condiciones")
    print()
    
    # Simular ejecución con diferentes escenarios
    print("💬 Escenarios de ejecución:")
    
    # Escenario 1: Cliente válido
    print("   Escenario 1 - Cliente válido:")
    user_params = {
        "customer_id": "CUST123",
        "loan_amount": "50000",
        "purpose": "Compra de auto"
    }
    
    print(f"      Cliente: {user_params['customer_id']}")
    print(f"      Monto: ${user_params['loan_amount']}")
    print(f"      Propósito: {user_params['purpose']}")
    print("      [Simulado] Todos los pasos se ejecutan en secuencia")
    print()
    
    # Escenario 2: Cliente con identidad no verificada
    print("   Escenario 2 - Cliente con identidad no verificada:")
    print("      [Simulado] Paso 1: Verificación de identidad falla")
    print("      [Simulado] Flujo se detiene en el paso 1")
    print("      [Simulado] Pasos 2-5 no se ejecutan")
    print()


def demo_workflow_creation():
    """Demo de creación de flujos de trabajo personalizados"""
    print("🔨 Demo: Creación de Flujos de Trabajo Personalizados")
    print("=" * 60)
    
    # Crear un flujo de trabajo simple paso a paso
    print("📝 Creando flujo de trabajo personalizado...")
    
    # Paso 1: Obtener datos del usuario
    step1 = WorkflowStep(
        name="obtener_datos_usuario",
        description="Obtener información básica del usuario",
        url="https://api.users.com/profile?user_id={user_id}",
        method="GET",
        required_params=["user_id"],
        response_mapping={
            "user_name": "profile.name",
            "user_email": "profile.email",
            "user_preferences": "profile.preferences"
        }
    )
    
    # Paso 2: Procesar preferencias
    step2 = WorkflowStep(
        name="procesar_preferencias",
        description="Procesar preferencias del usuario",
        url="https://api.preferences.com/process",
        method="POST",
        required_params=["user_preferences"],
        condition="exists:user_preferences",
        body_template="""{
            "preferences": "{user_preferences}",
            "user_id": "{user_id}"
        }""",
        response_mapping={
            "processed_preferences": "result.preferences",
            "recommendations": "result.recommendations"
        }
    )
    
    # Paso 3: Generar recomendaciones personalizadas
    step3 = WorkflowStep(
        name="generar_recomendaciones",
        description="Generar recomendaciones basadas en preferencias",
        url="https://api.recommendations.com/generate",
        method="POST",
        required_params=["processed_preferences", "user_name"],
        condition="exists:processed_preferences",
        body_template="""{
            "user_name": "{user_name}",
            "preferences": "{processed_preferences}",
            "type": "personalized"
        }""",
        response_mapping={
            "final_recommendations": "recommendations.list",
            "confidence_score": "recommendations.confidence"
        }
    )
    
    # Crear definición del flujo de trabajo
    custom_workflow = WorkflowDefinition(
        name="recomendaciones_personalizadas",
        description="Genera recomendaciones personalizadas para el usuario",
        steps=[step1, step2, step3],
        input_params=["user_id"],
        examples=[
            "Genera recomendaciones personalizadas para mi perfil",
            "¿Qué me recomiendas basado en mis preferencias?"
        ],
        keywords=["recomendaciones", "personalizado", "preferencias", "usuario"]
    )
    
    print("✅ Flujo de trabajo creado exitosamente:")
    print(f"   Nombre: {custom_workflow.name}")
    print(f"   Descripción: {custom_workflow.description}")
    print(f"   Pasos: {len(custom_workflow.steps)}")
    print(f"   Parámetros de entrada: {', '.join(custom_workflow.input_params)}")
    print()
    
    # Mostrar estructura del flujo
    print("🏗️ Estructura del flujo:")
    for i, step in enumerate(custom_workflow.steps, 1):
        print(f"   {i}. {step.name}")
        print(f"      → {step.description}")
        if step.condition:
            print(f"      → Condición: {step.condition}")
        if step.response_mapping:
            print(f"      → Extrae: {', '.join(step.response_mapping.keys())}")


async def demo_workflow_execution():
    """Demo de ejecución de flujos de trabajo"""
    print("🚀 Demo: Ejecución de Flujos de Trabajo")
    print("=" * 60)
    
    # Crear un flujo de trabajo simple para demostración
    simple_step1 = WorkflowStep(
        name="obtener_datos",
        description="Obtener datos iniciales",
        url="https://api.example.com/data?param={input_param}",
        method="GET",
        required_params=["input_param"],
        response_mapping={
            "data_id": "response.id",
            "data_value": "response.value"
        }
    )
    
    simple_step2 = WorkflowStep(
        name="procesar_datos",
        description="Procesar los datos obtenidos",
        url="https://api.example.com/process",
        method="POST",
        required_params=["data_id", "data_value"],
        condition="exists:data_id",
        body_template="""{
            "id": "{data_id}",
            "value": "{data_value}",
            "timestamp": "{{context.timestamp}}"
        }""",
        response_mapping={
            "processed_result": "result.processed",
            "status": "result.status"
        }
    )
    
    simple_workflow = WorkflowDefinition(
        name="flujo_simple_demo",
        description="Flujo de trabajo simple para demostración",
        steps=[simple_step1, simple_step2],
        input_params=["input_param"]
    )
    
    print("📋 Flujo de trabajo simple configurado:")
    print(f"   Nombre: {simple_workflow.name}")
    print(f"   Pasos: {len(simple_workflow.steps)}")
    print()
    
    # Simular ejecución
    print("💬 Simulación de ejecución:")
    user_params = {"input_param": "valor_ejemplo"}
    context = {"timestamp": "2024-01-01T00:00:00Z"}
    
    print(f"   Parámetros del usuario: {user_params}")
    print(f"   Contexto: {context}")
    print()
    
    print("   [Simulado] Iniciando ejecución del flujo...")
    print("   [Simulado] Paso 1: Obteniendo datos...")
    print("   [Simulado] → URL: https://api.example.com/data?param=valor_ejemplo")
    print("   [Simulado] → Respuesta: {'id': '123', 'value': 'datos_ejemplo'}")
    print("   [Simulado] → Parámetros extraídos: data_id=123, data_value=datos_ejemplo")
    print()
    
    print("   [Simulado] Paso 2: Procesando datos...")
    print("   [Simulado] → URL: https://api.example.com/process")
    print("   [Simulado] → Body: {'id': '123', 'value': 'datos_ejemplo', 'timestamp': '2024-01-01T00:00:00Z'}")
    print("   [Simulado] → Respuesta: {'result': {'processed': 'datos_procesados', 'status': 'success'}}")
    print()
    
    print("   [Simulado] Flujo completado exitosamente")
    print("   [Simulado] Resumen: 2 pasos ejecutados, 0 errores")


async def main():
    """Función principal del demo"""
    print("🎯 DEMO: Sistema de Flujos de Trabajo Secuenciales")
    print("=" * 70)
    print()
    
    # Ejecutar demos
    await demo_hotel_booking_workflow()
    print()
    
    await demo_product_analysis_workflow()
    print()
    
    await demo_credit_approval_workflow()
    print()
    
    demo_workflow_creation()
    print()
    
    await demo_workflow_execution()
    print()
    
    print("🎉 Demo completado!")
    print("Para usar el sistema en producción:")
    print("   1. Configurar flujos de trabajo en el perfil del usuario")
    print("   2. El sistema se integra automáticamente con LangChain")
    print("   3. Los flujos se ejecutan secuencialmente")
    print("   4. Cada paso puede depender de respuestas anteriores")
    print("   5. ¡Disfrutar de flujos de trabajo complejos e inteligentes!")


if __name__ == "__main__":
    # Ejecutar demo
    asyncio.run(main())





