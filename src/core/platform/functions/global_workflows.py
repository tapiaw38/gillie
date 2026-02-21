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


# ============================================================================
# GLOBAL WORKFLOW REGISTRY
# Add your workflows here.
# ============================================================================

GLOBAL_WORKFLOWS: List[Dict[str, Any]] = [
    # Example:
    # MY_WORKFLOW,
]


# ============================================================================
# HELPERS
# ============================================================================

def has_active_integration(profile, integration_name: str) -> bool:
    """Return True if the profile has an active, connected integration by name."""
    if not profile or not hasattr(profile, "integrations") or not profile.integrations:
        return False

    for integration in profile.integrations:
        if (
            integration.name == integration_name
            and integration.activated is True
            and integration.config.get("is_connected", False) is True
        ):
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
