"""
RAG (Retrieval-Augmented Generation) Prompt Templates

Templates for RAG-enhanced responses.
"""

RAG_SYSTEM_TEMPLATE = """You are an AI assistant with access to a knowledge base.

Use the following context from the knowledge base to answer the user's question.
If the context doesn't contain relevant information, say so honestly.

Context from Knowledge Base:
{context}

Guidelines:
- Prioritize information from the provided context
- Cite specific details when possible
- If context is insufficient, acknowledge it
- Be accurate and don't hallucinate information"""


RAG_QUERY_TEMPLATE = """Based on the following context, please answer this question:

Context:
{context}

Question: {question}

Answer:"""


RAG_HYBRID_TEMPLATE = """You have access to multiple information sources.

Knowledge Base Context:
{kb_context}

Additional Context:
{additional_context}

Question: {question}

Please provide a comprehensive answer using all available information."""


def build_rag_prompt(
    question: str,
    context: str,
    additional_context: str = ""
) -> str:
    """
    Build RAG prompt with context.

    Args:
        question: User's question
        context: Retrieved context from knowledge base
        additional_context: Optional additional context

    Returns:
        Complete RAG prompt
    """
    if additional_context:
        return RAG_HYBRID_TEMPLATE.format(
            kb_context=context,
            additional_context=additional_context,
            question=question,
        )
    else:
        return RAG_QUERY_TEMPLATE.format(
            context=context,
            question=question,
        )


def build_rag_system_prompt(context: str) -> str:
    """
    Build RAG system prompt.

    Args:
        context: Context from knowledge base

    Returns:
        System prompt
    """
    return RAG_SYSTEM_TEMPLATE.format(context=context)
