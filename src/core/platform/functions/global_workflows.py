"""
Global Workflows — Pre-defined workflows loaded dynamically.

This module registers workflows that are available to all users who have the
required integrations active. Workflows are NOT stored in the database; they
live here so that changes are centrally applied.

Usage:
    from src.core.platform.functions.global_workflows import get_available_workflows

    workflows = get_available_workflows(profile)

To add a new workflow:
1. Define a workflow dict following the standard schema:
   {
       "type": "workflow",
       "name": "...",
       "description": "...",
       "requires_integration": "...",   # optional
       "input_params": [...],
       "optional_params": [...],        # optional
       "examples": [...],
       "keywords": [...],
       "steps": [
           {
               "name": "...",
               "description": "...",
               "url": "...",            # supports {param} placeholders
               "method": "GET|POST|PUT|DELETE",
               "required_params": [...],
               "body_template": "...",  # optional JSON string with {param} placeholders
               "headers": {...},        # optional, values support {param} placeholders
               "response_mapping": {...},   # maps context keys to response dot-paths
               "condition": "...",      # optional, stops workflow if false
           }
       ]
   }
2. Append it to GLOBAL_WORKFLOWS below.
"""

from typing import List, Dict, Any, Optional


_CALENDAR_BASE = "http://localhost:8000/api/v1/calendar"
_CALENDAR_HEADERS = {"Authorization": "Bearer {auth_token}", "Content-Type": "application/json"}

CALENDAR_LIST_EVENTS = {
    "type": "workflow",
    "name": "calendar_list_events",
    "requires_integration": "google_calendar",
    "description": "List calendar events for the user. Optionally filter by start and end date.",
    "input_params": [],
    "optional_params": ["start_date", "end_date", "limit"],
    "keywords": [
        "eventos", "calendario", "agenda", "citas", "reuniones",
        "calendar", "events", "schedule", "meetings", "appointments",
        "que tengo", "mis eventos", "mis reuniones", "ver agenda",
    ],
    "examples": [
        "¿Qué tengo en el calendario esta semana?",
        "Muéstrame mis eventos de hoy",
        "¿Tengo reuniones mañana?",
        "Show my calendar events",
        "What's on my agenda for next week?",
    ],
    "steps": [
        {
            "name": "list_events",
            "description": "Fetch calendar events from the API",
            "url": _CALENDAR_BASE + "/events",
            "method": "GET",
            "required_params": [],
            "headers": _CALENDAR_HEADERS,
            "response_mapping": {"events": "data"},
        }
    ],
}

CALENDAR_CREATE_EVENT = {
    "type": "workflow",
    "name": "calendar_create_event",
    "requires_integration": "google_calendar",
    "description": (
        "Create a new calendar event. Requires title, start_time and end_time "
        "(ISO 8601 format, e.g. 2025-06-10T10:00:00). "
        "Optional: description, location."
    ),
    "input_params": ["title", "start_time", "end_time"],
    "optional_params": ["description", "location"],
    "keywords": [
        "crear evento", "nuevo evento", "agendar", "agregar al calendario",
        "create event", "add event", "schedule meeting", "book appointment",
        "reservar", "programar reunión",
    ],
    "examples": [
        "Crea un evento llamado Reunión de equipo el 10 de junio a las 10am",
        "Agrega al calendario: Dentista el 15 de julio de 3pm a 4pm",
        "Schedule a meeting tomorrow at 2pm",
        "Create a calendar event for the project review on Friday at 9am",
    ],
    "steps": [
        {
            "name": "create_event",
            "description": "Create the calendar event",
            "url": _CALENDAR_BASE + "/events",
            "method": "POST",
            "required_params": ["title", "start_time", "end_time"],
            "body_template": '{"title": "{title}", "start_time": "{start_time}", "end_time": "{end_time}", "description": "{description}", "location": "{location}"}',
            "headers": _CALENDAR_HEADERS,
            "response_mapping": {"created_event": ""},
        }
    ],
}

CALENDAR_UPDATE_EVENT = {
    "type": "workflow",
    "name": "calendar_update_event",
    "requires_integration": "google_calendar",
    "description": (
        "Update an existing calendar event by its ID. "
        "Can change title, start_time, end_time, description or location."
    ),
    "input_params": ["event_id"],
    "optional_params": ["title", "start_time", "end_time", "description", "location"],
    "keywords": [
        "actualizar evento", "editar evento", "modificar evento", "cambiar evento",
        "update event", "edit event", "modify event", "reschedule",
        "mover reunión", "cambiar hora",
    ],
    "examples": [
        "Cambia la reunión de equipo al miércoles a las 3pm",
        "Update event abc123 title to 'Sprint Review'",
        "Reschedule my meeting to next Friday at 10am",
    ],
    "steps": [
        {
            "name": "update_event",
            "description": "Update the calendar event",
            "url": _CALENDAR_BASE + "/events/{event_id}",
            "method": "PUT",
            "required_params": ["event_id"],
            "body_template": '{"title": "{title}", "start_time": "{start_time}", "end_time": "{end_time}", "description": "{description}", "location": "{location}"}',
            "headers": _CALENDAR_HEADERS,
            "response_mapping": {"updated_event": ""},
        }
    ],
}

CALENDAR_DELETE_EVENT = {
    "type": "workflow",
    "name": "calendar_delete_event",
    "requires_integration": "google_calendar",
    "description": "Delete a calendar event by its ID.",
    "input_params": ["event_id"],
    "optional_params": [],
    "keywords": [
        "eliminar evento", "borrar evento", "cancelar evento",
        "delete event", "remove event", "cancel meeting",
    ],
    "examples": [
        "Elimina el evento con ID abc123",
        "Borra la reunión del lunes",
        "Delete event abc123",
        "Cancel the dentist appointment",
    ],
    "steps": [
        {
            "name": "delete_event",
            "description": "Delete the calendar event",
            "url": _CALENDAR_BASE + "/events/{event_id}",
            "method": "DELETE",
            "required_params": ["event_id"],
            "headers": _CALENDAR_HEADERS,
            "response_mapping": {},
        }
    ],
}


_DRIVE_BASE = "http://localhost:8000/api/v1/drive"
_DRIVE_HEADERS = {"Authorization": "Bearer {auth_token}", "Content-Type": "application/json"}

DRIVE_LIST_FILES = {
    "type": "workflow",
    "name": "drive_list_files",
    "requires_integration": "google_drive",
    "description": "List files and folders in Google Drive. Optionally filter by folder.",
    "input_params": [],
    "optional_params": ["folder_id"],
    "keywords": [
        "archivos drive", "mis archivos", "documentos drive", "listar drive",
        "drive files", "list drive", "carpetas drive",
    ],
    "examples": [
        "¿Qué archivos tengo en Google Drive?",
        "Lista mis archivos de Drive",
        "List my Drive files",
    ],
    "steps": [
        {
            "name": "list_files",
            "description": "List Drive files",
            "url": _DRIVE_BASE + "/files",
            "method": "GET",
            "required_params": [],
            "headers": _DRIVE_HEADERS,
            "response_mapping": {"files": "files"},
        }
    ],
}

DRIVE_DOWNLOAD_FILE = {
    "type": "workflow",
    "name": "drive_download_file",
    "requires_integration": "google_drive",
    "description": "Download a file from Google Drive by its ID.",
    "input_params": ["file_id"],
    "optional_params": [],
    "keywords": [
        "descargar archivo", "download file", "bajar archivo", "obtener archivo",
    ],
    "examples": [
        "Descarga el archivo con ID abc123",
        "Download file abc123 from Drive",
    ],
    "steps": [
        {
            "name": "download_file",
            "description": "Download the file",
            "url": _DRIVE_BASE + "/files/{file_id}/download",
            "method": "GET",
            "required_params": ["file_id"],
            "headers": _DRIVE_HEADERS,
            "response_mapping": {"file_content": ""},
        }
    ],
}

DRIVE_CREATE_FOLDER = {
    "type": "workflow",
    "name": "drive_create_folder",
    "requires_integration": "google_drive",
    "description": "Create a new folder in Google Drive. Optionally specify a parent folder.",
    "input_params": ["name"],
    "optional_params": ["parent_id"],
    "keywords": [
        "crear carpeta", "nueva carpeta", "create folder", "nueva carpeta drive",
    ],
    "examples": [
        "Crea una carpeta llamada Proyectos en Drive",
        "Create a folder named Reports in Drive",
    ],
    "steps": [
        {
            "name": "create_folder",
            "description": "Create the folder",
            "url": _DRIVE_BASE + "/folders",
            "method": "POST",
            "required_params": ["name"],
            "body_template": '{"name": "{name}", "parent_id": "{parent_id}"}',
            "headers": _DRIVE_HEADERS,
            "response_mapping": {"folder": ""},
        }
    ],
}

DRIVE_MOVE_FILE = {
    "type": "workflow",
    "name": "drive_move_file",
    "requires_integration": "google_drive",
    "description": "Move a file to a different folder in Google Drive.",
    "input_params": ["file_id", "new_folder_id"],
    "optional_params": [],
    "keywords": [
        "mover archivo", "move file", "mover a carpeta", "cambiar carpeta",
    ],
    "examples": [
        "Mueve el archivo abc123 a la carpeta xyz",
        "Move file abc123 to folder xyz",
    ],
    "steps": [
        {
            "name": "move_file",
            "description": "Move the file",
            "url": _DRIVE_BASE + "/files/{file_id}/move",
            "method": "PATCH",
            "required_params": ["file_id", "new_folder_id"],
            "body_template": '{"new_folder_id": "{new_folder_id}"}',
            "headers": _DRIVE_HEADERS,
            "response_mapping": {"moved_file": ""},
        }
    ],
}


GLOBAL_WORKFLOWS: List[Dict[str, Any]] = [
    CALENDAR_LIST_EVENTS,
    CALENDAR_CREATE_EVENT,
    CALENDAR_UPDATE_EVENT,
    CALENDAR_DELETE_EVENT,
    DRIVE_LIST_FILES,
    DRIVE_DOWNLOAD_FILE,
    DRIVE_CREATE_FOLDER,
    DRIVE_MOVE_FILE,
]


def has_active_integration(profile, integration_name: str) -> bool:
    """Return True if the profile has an active, connected integration by name.

    For integrations that store OAuth tokens in the profile config (e.g. google_drive),
    we also verify access_token is present. For integrations that store tokens in a
    separate collection (e.g. google_calendar), activated=True is sufficient — the
    workflow HTTP call will fail gracefully if there is no valid session.
    """
    _PROFILE_TOKEN_INTEGRATIONS = {"google_drive"}

    if not profile or not hasattr(profile, "integrations") or not profile.integrations:
        return False

    for integration in profile.integrations:
        if integration.name == integration_name and integration.activated is True:
            if integration_name in _PROFILE_TOKEN_INTEGRATIONS:
                config = integration.config or {}
                if config.get("access_token"):
                    return True
            else:
                return True

    return False


def get_available_workflows(profile) -> List[Dict[str, Any]]:
    """Return global workflows available for *profile* based on active integrations."""
    available = []

    for workflow in GLOBAL_WORKFLOWS:
        required_integration = workflow.get("requires_integration")

        if required_integration:
            if has_active_integration(profile, required_integration):
                workflow_copy = workflow.copy()
                workflow_copy.pop("requires_integration", None)
                available.append(workflow_copy)
        else:
            available.append(workflow)

    return available


def get_workflow_by_name(workflow_name: str) -> Optional[Dict[str, Any]]:
    """Return a global workflow by name, or None if not found."""
    for workflow in GLOBAL_WORKFLOWS:
        if workflow.get("name") == workflow_name:
            return workflow
    return None


def get_workflows_requiring_integration(integration_name: str) -> List[Dict[str, Any]]:
    """Return all workflows that require a specific integration."""
    return [
        w for w in GLOBAL_WORKFLOWS
        if w.get("requires_integration") == integration_name
    ]


def get_workflows_info() -> Dict[str, Any]:
    """Return summary statistics about registered global workflows."""
    integrations_count: Dict[str, int] = {}

    for workflow in GLOBAL_WORKFLOWS:
        integration = workflow.get("requires_integration", "none")
        integrations_count[integration] = integrations_count.get(integration, 0) + 1

    return {
        "total_workflows": len(GLOBAL_WORKFLOWS),
        "by_integration": integrations_count,
        "workflow_names": [w["name"] for w in GLOBAL_WORKFLOWS],
    }
