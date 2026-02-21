from typing import Optional
from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.memory import MemoryFAQCreateError


class AddFAQUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    def execute(self, question: str, answer: str, category: Optional[str] = None) -> dict:
        if not question or not question.strip():
            from src.core.platform.errors.application_error import ErrorDetails
            raise NewApplicationError(
                ErrorDetails(internal_code="memory:faq:question-required", status_code=400, message="question is required")
            )
        if not answer or not answer.strip():
            from src.core.platform.errors.application_error import ErrorDetails
            raise NewApplicationError(
                ErrorDetails(internal_code="memory:faq:answer-required", status_code=400, message="answer is required")
            )

        try:
            skill_manager = self.context_factory().platform_managers.skill_manager
            faq_id = skill_manager.add_faq(question.strip(), answer.strip(), category)
            return {"id": faq_id, "question": question.strip(), "answer": answer.strip(), "category": category or "General"}
        except Exception as e:
            raise NewApplicationError(MemoryFAQCreateError, e)
