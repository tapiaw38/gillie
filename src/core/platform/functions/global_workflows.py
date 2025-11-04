"""
Global Workflows - Workflows predefinidos que se cargan dinámicamente

Este módulo contiene workflows globales que están disponibles automáticamente
para todos los usuarios que tienen las integraciones requeridas activas.

VENTAJAS:
- No se guardan en la BD (ahorra espacio)
- Se actualizan centralmente (cambias aquí y afecta a todos)
- Fácil mantenimiento
- Se cargan dinámicamente según integraciones activas

USO:
    from src.core.platform.functions.global_workflows import get_available_workflows

    workflows = get_available_workflows(profile)
"""

from typing import List, Dict, Any, Optional


# ============================================================================
# WORKFLOWS DE GOOGLE CALENDAR
# ============================================================================

CREAR_EVENTO_CALENDARIO = {
    "type": "workflow",
    "name": "crear_evento_calendario",
    "description": "Crea un evento en Google Calendar del usuario. Requiere: título y fecha/hora de inicio. Opcionalmente puede incluir descripción. La duración por defecto es 1 hora.",
    "requires_integration": "google_calendar",  # NUEVO CAMPO
    "input_params": [
        "title",
        "start_time"
    ],
    "optional_params": [
        "description",
        "location",
        "end_time",
        "time_zone",
        "attendees",
        "reminders"
    ],
    "examples": [
        "Usuario: 'agendar reunión mañana 10am' → AI extrae: title='Reunión', start_time='2025-11-04T10:00:00'",
        "Usuario: 'crear evento consulta médica el viernes 15:00' → AI extrae: title='Consulta médica', start_time='2025-11-08T15:00:00'",
        "Usuario: 'recordarme dentista 20 de noviembre 9am' → AI extrae: title='Dentista', start_time='2025-11-20T09:00:00'",
        "Usuario: 'agendar llamada con María el 5 de diciembre a las 2pm' → AI extrae: title='Llamada con María', start_time='2025-12-05T14:00:00'",
        "Usuario: 'nueva reunión proyecto X martes 11hs' → AI extrae: title='Reunión proyecto X', start_time='[próximo martes]T11:00:00'"
    ],
    "keywords": [
        "evento",
        "calendario",
        "reunión",
        "cita",
        "agendar",
        "recordatorio",
        "meeting",
        "appointment",
        "schedule",
        "crear evento",
        "nueva reunión",
        "agendar cita",
        "programar",
        "recordarme"
    ],
    "steps": [
        {
            "name": "verificar_integracion_calendario",
            "description": "Verifica que Google Calendar esté conectado",
            "url": "http://localhost:8084/api/v1/calendar/oauth/status?user_id={user_id}&profile_id={profile_id}",
            "method": "GET",
            "required_params": ["user_id", "profile_id"],
            "response_mapping": {
                "is_connected": "is_active"
            },
            "condition": "is_connected == true"
        },
        {
            "name": "crear_evento",
            "description": "Crea el evento en Google Calendar",
            "url": "http://localhost:8084/api/v1/calendar/events?user_id={user_id}&profile_id={profile_id}",
            "method": "POST",
            "required_params": [
                "profile_id",
                "title",
                "start_time",
                "end_time"
            ],
            "body_template": "{\"profile_id\": \"{profile_id}\", \"title\": \"{title}\", \"description\": \"{description}\", \"location\": \"{location}\", \"start_time\": \"{start_time}\", \"end_time\": \"{end_time}\", \"time_zone\": \"{time_zone}\"}",
            "headers": {
                "Content-Type": "application/json",
                "Authorization": "Bearer {auth_token}"
            },
            "response_mapping": {
                "event_id": "data.id",
                "google_id": "data.google_id",
                "event_title": "data.title",
                "event_start": "data.start_time",
                "event_end": "data.end_time",
                "is_synced": "data.google_id"
            }
        }
    ]
}

LISTAR_EVENTOS_CALENDARIO = {
    "type": "workflow",
    "name": "listar_eventos_calendario",
    "description": "Lista los próximos eventos de Google Calendar",
    "requires_integration": "google_calendar",
    "input_params": [
        "limit",
        "start_date",
        "end_date"
    ],
    "examples": [
        "cuáles son mis próximos eventos",
        "qué tengo agendado para mañana",
        "mostrar mi calendario de la semana",
        "eventos de hoy",
        "reuniones pendientes"
    ],
    "keywords": [
        "listar eventos",
        "mis eventos",
        "calendario",
        "próximos eventos",
        "reuniones pendientes",
        "qué tengo agendado",
        "mostrar calendario",
        "eventos de hoy",
        "eventos de mañana",
        "agenda"
    ],
    "steps": [
        {
            "name": "listar_eventos",
            "description": "Obtiene los eventos del calendario",
            "url": "http://localhost:8084/api/v1/calendar/events?user_id={user_id}&profile_id={profile_id}&limit={limit}",
            "method": "GET",
            "required_params": ["user_id", "profile_id"],
            "response_mapping": {
                "events": "data",
                "event_count": "pagination.total"
            }
        }
    ]
}

ELIMINAR_EVENTO_CALENDARIO = {
    "type": "workflow",
    "name": "eliminar_evento_calendario",
    "description": "Elimina un evento de Google Calendar",
    "requires_integration": "google_calendar",
    "input_params": [
        "event_id"
    ],
    "examples": [
        "cancelar mi reunión de mañana",
        "eliminar evento de las 10am",
        "borrar la cita con el dentista"
    ],
    "keywords": [
        "cancelar evento",
        "eliminar evento",
        "borrar evento",
        "cancelar reunión",
        "eliminar cita",
        "borrar cita"
    ],
    "steps": [
        {
            "name": "eliminar_evento",
            "description": "Elimina el evento del calendario",
            "url": "http://localhost:8084/api/v1/calendar/events/{event_id}?user_id={user_id}&profile_id={profile_id}",
            "method": "DELETE",
            "required_params": ["event_id", "user_id", "profile_id"],
            "response_mapping": {
                "deleted": "success",
                "message": "message"
            }
        }
    ]
}


# ============================================================================
# REGISTRO DE WORKFLOWS GLOBALES
# ============================================================================

GLOBAL_WORKFLOWS = [
    CREAR_EVENTO_CALENDARIO,
    LISTAR_EVENTOS_CALENDARIO,
    ELIMINAR_EVENTO_CALENDARIO,
]


# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def has_active_integration(profile, integration_name: str) -> bool:
    """
    Verifica si el perfil tiene una integración activa

    Args:
        profile: Objeto Profile del dominio
        integration_name: Nombre de la integración (ej: "google_calendar")

    Returns:
        True si la integración está activa y conectada, False en caso contrario
    """
    if not profile or not hasattr(profile, 'integrations') or not profile.integrations:
        return False

    for integration in profile.integrations:
        if (integration.name == integration_name and
            integration.activated is True and
            integration.config.get("is_connected", False) is True):
            return True

    return False


def get_available_workflows(profile) -> List[Dict[str, Any]]:
    """
    Obtiene los workflows globales disponibles para un perfil según sus integraciones

    Args:
        profile: Objeto Profile del dominio

    Returns:
        Lista de workflows disponibles para el perfil
    """
    available = []

    for workflow in GLOBAL_WORKFLOWS:
        # Si el workflow requiere una integración
        required_integration = workflow.get("requires_integration")

        if required_integration:
            # Solo agregar si el usuario tiene esa integración activa
            if has_active_integration(profile, required_integration):
                # Crear copia sin el campo requires_integration
                workflow_copy = workflow.copy()
                workflow_copy.pop("requires_integration", None)
                available.append(workflow_copy)
        else:
            # Workflow sin requisitos, siempre disponible
            available.append(workflow)

    return available


def get_workflow_by_name(workflow_name: str) -> Optional[Dict[str, Any]]:
    """
    Obtiene un workflow global por nombre

    Args:
        workflow_name: Nombre del workflow

    Returns:
        Workflow o None si no existe
    """
    for workflow in GLOBAL_WORKFLOWS:
        if workflow.get("name") == workflow_name:
            return workflow

    return None


def get_workflows_requiring_integration(integration_name: str) -> List[Dict[str, Any]]:
    """
    Obtiene todos los workflows que requieren una integración específica

    Args:
        integration_name: Nombre de la integración

    Returns:
        Lista de workflows que requieren esa integración
    """
    return [
        w for w in GLOBAL_WORKFLOWS
        if w.get("requires_integration") == integration_name
    ]


# ============================================================================
# INFORMACIÓN Y ESTADÍSTICAS
# ============================================================================

def get_workflows_info() -> Dict[str, Any]:
    """
    Obtiene información sobre todos los workflows globales

    Returns:
        Diccionario con estadísticas de workflows
    """
    integrations_count = {}

    for workflow in GLOBAL_WORKFLOWS:
        integration = workflow.get("requires_integration", "none")
        integrations_count[integration] = integrations_count.get(integration, 0) + 1

    return {
        "total_workflows": len(GLOBAL_WORKFLOWS),
        "by_integration": integrations_count,
        "workflow_names": [w["name"] for w in GLOBAL_WORKFLOWS]
    }


if __name__ == "__main__":
    # Test: Mostrar información de workflows
    import json

    print("=" * 80)
    print("GLOBAL WORKFLOWS DISPONIBLES")
    print("=" * 80)

    info = get_workflows_info()
    print(f"\nTotal de workflows: {info['total_workflows']}")
    print(f"\nPor integración:")
    for integration, count in info['by_integration'].items():
        print(f"  - {integration}: {count} workflow(s)")

    print(f"\nWorkflows:")
    for name in info['workflow_names']:
        workflow = get_workflow_by_name(name)
        integration = workflow.get('requires_integration', 'ninguna')
        print(f"  - {name} (requiere: {integration})")

    print("\n" + "=" * 80)

    class MockIntegration:
        def __init__(self, name, activated, config):
            self.name = name
            self.activated = activated
            self.config = config

    class MockProfile:
        def __init__(self):
            self.integrations = [
                MockIntegration(
                    "google_calendar",
                    True,
                    {"is_connected": True}
                )
            ]

    profile = MockProfile()
    available = get_available_workflows(profile)

    print("\nWORKFLOWS DISPONIBLES PARA PERFIL CON GOOGLE CALENDAR:")
    print("=" * 80)
    for workflow in available:
        print(f"\n{workflow['name']}:")
        print(f"  Descripción: {workflow['description']}")
        print(f"  Keywords: {', '.join(workflow['keywords'][:5])}...")
