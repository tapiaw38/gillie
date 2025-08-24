#!/usr/bin/env python3
"""
Demo del Sistema de Funciones Genérico con LangChain

Este script demuestra cómo usar el nuevo sistema de funciones genérico.
"""

import asyncio
import json
from unittest.mock import Mock
from src.core.platform.functions.function_executor import GenericFunctionExecutor
from src.core.platform.config.service import ConfigurationService
from src.core.domain.model import Profile


class MockConfigService:
    """Mock del servicio de configuración para demostración"""
    class OpenAIConfig:
        api_key = "demo_key"
        base_url = "https://api.openai.com"
        model = "gpt-3.5-turbo"
    
    openai_config = OpenAIConfig()


async def demo_basic_function():
    """Demo básico de ejecución de función"""
    print("🚀 Demo: Ejecución Básica de Función")
    print("=" * 50)
    
    # Crear configuración de función de clima
    weather_config = {
        "name": "consultar_clima",
        "description": "Obtiene información del clima actual para una ubicación específica",
        "url": "https://api.openweathermap.org/data/2.5/weather?lat={latitude}&lon={longitude}&appid=DEMO_KEY&units=metric&lang=es",
        "method": "GET",
        "examples": [
            "¿Qué tiempo hace en Madrid?",
            "¿Cuál es la temperatura en Barcelona?",
            "Clima en 40.4168, -3.7038"
        ],
        "keywords": ["clima", "tiempo", "temperatura", "pronóstico"]
    }
    
    # Crear perfil de usuario con la función
    profile = Mock(spec=Profile)
    profile.user_id = "demo_user"
    profile.functions = [weather_config]
    
    # Crear ejecutor de funciones
    config_service = MockConfigService()
    executor = GenericFunctionExecutor(config_service)
    
    # Mostrar información de la función
    print("📋 Función configurada:")
    print(f"   Nombre: {weather_config['name']}")
    print(f"   Descripción: {weather_config['description']}")
    print(f"   URL: {weather_config['url']}")
    print(f"   Parámetros requeridos: {executor._extract_params_from_url(weather_config['url'])}")
    print()
    
    # Ejecutar función (simulado)
    print("💬 Ejemplos de uso:")
    test_messages = [
        "¿Qué tiempo hace en Madrid?",
        "¿Cuál es la temperatura en Barcelona?",
        "Clima en 40.4168, -3.7038",
        "Hola, ¿cómo estás?"  # No debería activar la función
    ]
    
    for message in test_messages:
        print(f"   Usuario: {message}")
        # En un entorno real, esto ejecutaría la función
        print(f"   Sistema: [Simulado] Análisis de intención y ejecución de función")
        print()


async def demo_multiple_functions():
    """Demo de múltiples funciones"""
    print("🔧 Demo: Múltiples Funciones")
    print("=" * 50)
    
    # Configurar múltiples funciones
    functions_config = [
        {
            "name": "consultar_clima",
            "description": "Obtiene información del clima actual",
            "url": "https://api.weather.com/weather?lat={latitude}&lon={longitude}",
            "method": "GET"
        },
        {
            "name": "obtener_noticias",
            "description": "Obtiene las últimas noticias de una categoría",
            "url": "https://api.news.com/headlines?category={category}&country={country}",
            "method": "GET"
        },
        {
            "name": "traducir_texto",
            "description": "Traduce texto entre idiomas",
            "url": "https://api.translate.com/translate?text={text}&from={source_lang}&to={target_lang}",
            "method": "POST"
        }
    ]
    
    # Crear perfil con múltiples funciones
    profile = Mock(spec=Profile)
    profile.user_id = "demo_user"
    profile.functions = functions_config
    
    # Crear ejecutor
    config_service = MockConfigService()
    executor = GenericFunctionExecutor(config_service)
    
    # Mostrar funciones disponibles
    print("📚 Funciones disponibles:")
    for i, func in enumerate(functions_config, 1):
        params = executor._extract_params_from_url(func['url'])
        print(f"   {i}. {func['name']}")
        print(f"      Descripción: {func['description']}")
        print(f"      Parámetros: {', '.join(params)}")
        print(f"      Método: {func['method']}")
        print()
    
    # Ejemplos de uso
    print("💬 Ejemplos de uso para diferentes funciones:")
    examples = [
        ("¿Qué tiempo hace en Madrid?", "consultar_clima"),
        ("¿Cuáles son las últimas noticias de tecnología?", "obtener_noticias"),
        ("Traduce 'Hello world' al español", "traducir_texto"),
        ("¿Cómo estás hoy?", "Ninguna función")
    ]
    
    for message, expected_function in examples:
        print(f"   Usuario: {message}")
        print(f"   Función esperada: {expected_function}")
        print()


def demo_function_config_creation():
    """Demo de creación de configuraciones de funciones"""
    print("⚙️ Demo: Creación de Configuraciones de Funciones")
    print("=" * 50)
    
    # Función helper para crear configuraciones
    def create_function_config(name, description, url, method="GET", examples=None, keywords=None):
        return {
            "name": name,
            "description": description,
            "url": url,
            "method": method.upper(),
            "examples": examples or [],
            "keywords": keywords or []
        }
    
    # Crear diferentes tipos de funciones
    functions = [
        create_function_config(
            name="buscar_productos",
            description="Busca productos en un catálogo",
            url="https://api.store.com/search?query={query}&category={category}&price_min={min_price}",
            examples=["Busca laptops gaming", "Encuentra zapatos deportivos"],
            keywords=["buscar", "encontrar", "productos", "catálogo"]
        ),
        create_function_config(
            name="hacer_reserva",
            description="Realiza una reserva en un restaurante o hotel",
            url="https://api.booking.com/reserve?service={service}&date={date}&guests={num_guests}",
            method="POST",
            examples=["Reserva una mesa para 4 personas", "Reserva un hotel en Madrid"],
            keywords=["reservar", "cita", "agendar", "mesa", "hotel"]
        )
    ]
    
    print("🔨 Funciones creadas dinámicamente:")
    for i, func in enumerate(functions, 1):
        print(f"   {i}. {func['name']}")
        print(f"      URL: {func['url']}")
        print(f"      Método: {func['method']}")
        print(f"      Ejemplos: {len(func['examples'])}")
        print(f"      Keywords: {len(func['keywords'])}")
        print()


async def demo_error_handling():
    """Demo del manejo de errores"""
    print("⚠️ Demo: Manejo de Errores")
    print("=" * 50)
    
    # Configuración de función con parámetros faltantes
    incomplete_config = {
        "name": "funcion_incompleta",
        "description": "Función con configuración incompleta",
        "url": "https://api.example.com/endpoint?param1={param1}&param2={param2}",
        "method": "GET"
    }
    
    profile = Mock(spec=Profile)
    profile.user_id = "demo_user"
    profile.functions = [incomplete_config]
    
    config_service = MockConfigService()
    executor = GenericFunctionExecutor(config_service)
    
    print("🔍 Análisis de configuración:")
    print(f"   Función: {incomplete_config['name']}")
    print(f"   URL: {incomplete_config['url']}")
    
    # Extraer parámetros requeridos
    params = executor._extract_params_from_url(incomplete_config['url'])
    print(f"   Parámetros requeridos: {params}")
    
    # Simular diferentes escenarios de error
    error_scenarios = [
        "Mensaje sin parámetros",
        "Mensaje con solo param1",
        "Mensaje con parámetros incorrectos"
    ]
    
    print("\n🚨 Escenarios de error:")
    for scenario in error_scenarios:
        print(f"   {scenario}: [Simulado] Validación y manejo de error")
    
    print("\n✅ El sistema maneja automáticamente:")
    print("   - Parámetros faltantes")
    print("   - Tipos de datos incorrectos")
    print("   - Errores de API")
    print("   - Fallbacks a respuestas normales")


def demo_migration_from_old_system():
    """Demo de migración desde el sistema anterior"""
    print("🔄 Demo: Migración desde Sistema Anterior")
    print("=" * 50)
    
    print("📋 Sistema Anterior (Hardcodeado):")
    print("   - Solo función de clima")
    print("   - Lógica específica para coordenadas")
    print("   - Código difícil de mantener")
    print("   - No escalable")
    print()
    
    print("✨ Sistema Nuevo (LangChain):")
    print("   - Cualquier función HTTP")
    print("   - Análisis inteligente de intención")
    print("   - Extracción automática de parámetros")
    print("   - Código limpio y mantenible")
    print("   - Fácil de escalar")
    print()
    
    print("🔄 Pasos de Migración:")
    print("   1. Convertir configuración hardcodeada a JSON")
    print("   2. El código se actualiza automáticamente")
    print("   3. Verificar funcionamiento")
    print("   4. Agregar nuevas funciones fácilmente")
    print()
    
    # Ejemplo de migración
    print("📝 Ejemplo de Migración:")
    print("   Antes: profile.functions = 'consultar_clima'")
    print("   Ahora: profile.functions = [WEATHER_FUNCTION_CONFIG]")


async def main():
    """Función principal del demo"""
    print("🎯 DEMO: Sistema de Funciones Genérico con LangChain")
    print("=" * 60)
    print()
    
    # Ejecutar demos
    await demo_basic_function()
    print()
    
    await demo_multiple_functions()
    print()
    
    demo_function_config_creation()
    print()
    
    await demo_error_handling()
    print()
    
    demo_migration_from_old_system()
    print()
    
    print("🎉 Demo completado!")
    print("Para usar el sistema en producción:")
    print("   1. Instalar dependencias: pip install langchain aiohttp requests")
    print("   2. Configurar funciones en el perfil del usuario")
    print("   3. El sistema se integra automáticamente")
    print("   4. ¡Disfrutar de funciones genéricas e inteligentes!")


if __name__ == "__main__":
    # Ejecutar demo
    asyncio.run(main())





