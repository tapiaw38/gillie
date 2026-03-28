"""This module provides a context for the OpenAPI integration with the assistant."""

CONTEXT_INFORMATION = (
    "Eres {assistant_name}. "
    "Funciones disponibles: {functions}. "
    "Contexto adicional: {product_context}. "
    "Responde basándote en la información disponible y los archivos adjuntos.\n"
)
