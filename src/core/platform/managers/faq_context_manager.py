"""
FAQ Context Manager

This service handles FAQ formatting and injection into LLM context,
following the Single Responsibility Principle by focusing solely on
FAQ-related context preparation.

Responsibilities:
- Retrieve active FAQs from repository
- Format FAQs for LLM consumption
- Filter FAQs by relevance to user query
- Provide formatted FAQ context strings
"""

import logging
from typing import List, Optional
from src.core.domain import FAQ

logger = logging.getLogger(__name__)


class FAQContextManager:
    """
    Service for managing FAQ context injection into LLM prompts.

    This service formats FAQs in a way that's easy for the LLM to understand
    and use when answering user questions.
    """

    def __init__(self, faq_repository):
        """
        Initialize the FAQ context manager.

        Args:
            faq_repository: Repository for FAQ operations
        """
        self.faq_repository = faq_repository

    def get_faq_context(
        self,
        category: Optional[str] = None,
        max_faqs: int = 20
    ) -> str:
        """
        Retrieves and formats FAQs for LLM context.

        Args:
            category: Optional category to filter FAQs
            max_faqs: Maximum number of FAQs to include (default: 20)

        Returns:
            Formatted FAQ context string ready for LLM injection
        """
        try:
            # Retrieve active FAQs
            faqs = self.faq_repository.find_all(
                category=category,
                is_active=True
            )

            if not faqs:
                logger.info("No active FAQs found")
                return ""

            # Limit number of FAQs
            faqs = faqs[:max_faqs]

            # Format FAQs for LLM
            formatted_context = self._format_faqs_for_llm(faqs)

            logger.info(f"Generated FAQ context with {len(faqs)} FAQs")
            return formatted_context

        except Exception as e:
            logger.error(f"Error retrieving FAQ context: {e}")
            return ""

    def get_faqs_by_category(self, category: str) -> str:
        """
        Retrieves and formats FAQs for a specific category.

        Args:
            category: Category to filter FAQs

        Returns:
            Formatted FAQ context string for the category
        """
        try:
            faqs = self.faq_repository.find_by_category(category)

            if not faqs:
                return ""

            return self._format_faqs_for_llm(faqs)

        except Exception as e:
            logger.error(f"Error retrieving FAQs for category '{category}': {e}")
            return ""

    def _format_faqs_for_llm(self, faqs: List[FAQ]) -> str:
        """
        Formats FAQs in a structure that's optimal for LLM understanding.

        The format includes:
        - Clear section header
        - Numbered Q&A pairs
        - Category information when available
        - Clean, readable structure

        Args:
            faqs: List of FAQ objects to format

        Returns:
            Formatted FAQ string
        """
        if not faqs:
            return ""

        formatted_parts = [
            "\n" + "="*60,
            "PREGUNTAS FRECUENTES (FAQs)",
            "="*60,
            "\nA continuación se encuentran las preguntas frecuentes que debes usar",
            "como referencia PRIORITARIA para responder consultas del usuario.",
            "Si la pregunta del usuario coincide con alguna FAQ, usa esa respuesta.\n"
        ]

        # Group FAQs by category if they have categories
        faqs_by_category = self._group_by_category(faqs)

        for category, category_faqs in faqs_by_category.items():
            if category:
                formatted_parts.append(f"\n📁 Categoría: {category}")
                formatted_parts.append("-" * 60)

            for idx, faq in enumerate(category_faqs, 1):
                formatted_parts.append(f"\n{idx}. PREGUNTA: {faq.question}")
                formatted_parts.append(f"   RESPUESTA: {faq.answer}")

                # Add tags if available
                if faq.tags:
                    tags_str = ", ".join(faq.tags)
                    formatted_parts.append(f"   Tags: {tags_str}")

                formatted_parts.append("")  # Empty line for readability

        formatted_parts.append("=" * 60 + "\n")

        return "\n".join(formatted_parts)

    def _group_by_category(self, faqs: List[FAQ]) -> dict:
        """
        Groups FAQs by category.

        Args:
            faqs: List of FAQ objects

        Returns:
            Dictionary with categories as keys and FAQ lists as values
        """
        grouped = {}

        for faq in faqs:
            category = faq.category or "General"
            if category not in grouped:
                grouped[category] = []
            grouped[category].append(faq)

        return grouped

    def search_relevant_faqs(
        self,
        user_query: str,
        max_results: int = 5
    ) -> str:
        """
        Searches for FAQs relevant to the user's query.

        This is a simple keyword-based search. For production,
        you might want to implement semantic search using embeddings.

        Args:
            user_query: User's question or message
            max_results: Maximum number of relevant FAQs to return

        Returns:
            Formatted string with relevant FAQs
        """
        try:
            # Get all active FAQs
            all_faqs = self.faq_repository.find_all(is_active=True)

            if not all_faqs:
                return ""

            # Simple keyword matching (can be enhanced with embeddings)
            query_lower = user_query.lower()
            relevant_faqs = []

            for faq in all_faqs:
                # Check if query keywords appear in question or tags
                if (query_lower in faq.question.lower() or
                    any(tag.lower() in query_lower for tag in (faq.tags or []))):
                    relevant_faqs.append(faq)

            # Limit results
            relevant_faqs = relevant_faqs[:max_results]

            if not relevant_faqs:
                return ""

            return self._format_faqs_for_llm(relevant_faqs)

        except Exception as e:
            logger.error(f"Error searching relevant FAQs: {e}")
            return ""
