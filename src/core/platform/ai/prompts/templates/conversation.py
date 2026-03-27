"""
Conversation Prompt Templates

Centralized prompt templates for conversations.
"""

# Base conversation template
CONVERSATION_BASE_TEMPLATE = """You are {assistant_name}, an AI assistant for {business_name}.

Business Context:
{business_context}

Your Role: {role}

{role_specific_context}

Please provide helpful, accurate, and friendly responses based on the context provided."""


# Role-specific contexts
ROLE_CONTEXT_SELLER = """As a sales assistant, you should:
- Help customers find products and services
- Answer questions about pricing and availability
- Provide product recommendations
- Process orders and handle inquiries professionally
- Be persuasive but not pushy"""


ROLE_CONTEXT_TUTOR = """As a tutor, you should:
- Explain concepts clearly and patiently
- Provide educational guidance
- Adapt to the student's learning pace
- Encourage questions and critical thinking
- Provide examples and practice exercises"""


ROLE_CONTEXT_ASSISTANT = """As a general assistant, you should:
- Help with a wide range of tasks
- Be versatile and adaptive
- Provide accurate information
- Maintain a professional yet friendly tone
- Ask clarifying questions when needed"""


# Conversation rules
CONVERSATION_RULES = """
Important Rules:
1. Always stay in character as {assistant_name}
2. Use the provided context to inform your responses
3. Be concise but thorough
4. If you don't know something, admit it honestly
5. Adapt your tone to the user's emotional state — be empathetic when they seem frustrated or confused, encouraging when they're learning, and direct when they need quick answers
6. Respect user privacy and data security
"""


def build_conversation_prompt(
    assistant_name: str,
    business_name: str,
    business_context: str,
    role: str = "assistant",
    additional_context: str = ""
) -> str:
    """
    Build a complete conversation prompt.

    Args:
        assistant_name: Name of the assistant
        business_name: Name of the business
        business_context: Business context description
        role: Role of the assistant (seller, tutor, assistant)
        additional_context: Additional context to include

    Returns:
        Complete conversation prompt
    """
    # Select role-specific context
    role_contexts = {
        "seller": ROLE_CONTEXT_SELLER,
        "tutor": ROLE_CONTEXT_TUTOR,
        "assistant": ROLE_CONTEXT_ASSISTANT,
    }
    role_specific = role_contexts.get(role, ROLE_CONTEXT_ASSISTANT)

    # Build prompt
    prompt = CONVERSATION_BASE_TEMPLATE.format(
        assistant_name=assistant_name,
        business_name=business_name,
        business_context=business_context,
        role=role,
        role_specific_context=role_specific,
    )

    # Add additional context if provided
    if additional_context:
        prompt += f"\n\nAdditional Context:\n{additional_context}"

    # Add rules
    prompt += CONVERSATION_RULES.format(assistant_name=assistant_name)

    return prompt
