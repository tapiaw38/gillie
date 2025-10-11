"""
Function Calling Prompt Templates

Templates for function/tool calling scenarios.
"""

FUNCTION_CALLING_SYSTEM = """You are an AI assistant with access to specific tools and functions.

When appropriate, use the available tools to help answer user questions or perform tasks.

Available Functions:
{functions_description}

Guidelines:
- Use tools when they can provide accurate, real-time information
- Call functions with correct parameters
- Explain what you're doing when using tools
- Combine function results with your knowledge to provide comprehensive answers"""


FUNCTION_DESCRIPTION_TEMPLATE = """Function: {name}
Description: {description}
Parameters: {parameters}
"""


def build_function_calling_system_prompt(functions: list) -> str:
    """
    Build system prompt for function calling.

    Args:
        functions: List of available functions

    Returns:
        System prompt with function descriptions
    """
    functions_desc = []

    for func in functions:
        func_desc = FUNCTION_DESCRIPTION_TEMPLATE.format(
            name=func.get("name", "Unknown"),
            description=func.get("description", "No description"),
            parameters=func.get("parameters", {}),
        )
        functions_desc.append(func_desc)

    return FUNCTION_CALLING_SYSTEM.format(
        functions_description="\n".join(functions_desc)
    )
