"""This module provides a context for the OpenAPI integration with the assistant."""

CONTEXT_INFORMATION = (
    "You are {assistant_name}. "
    "Available functions: {functions}. "
    "Additional context: {product_context}. "
    "Answer based on the available information and attached files.\n"
    "{language_instruction}"
)

LANGUAGE_INSTRUCTIONS = {
    "en": "Always respond in English.",
    "es": "Responde siempre en español.",
}


def get_language_instruction(language: str) -> str:
    return LANGUAGE_INSTRUCTIONS.get(language, LANGUAGE_INSTRUCTIONS["en"])
