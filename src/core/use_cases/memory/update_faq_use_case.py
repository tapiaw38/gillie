from typing import Optional
from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.memory import MemoryFAQNotFoundError, MemoryFAQUpdateError


class UpdateFAQUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    def execute(self, faq_id: str, question: str, answer: str, category: Optional[str] = None) -> dict:
        try:
            skill_manager = self.context_factory().platform_managers.skill_manager
            updated = skill_manager.update_faq(faq_id, question.strip(), answer.strip(), category)
            if not updated:
                raise NewApplicationError(MemoryFAQNotFoundError)
            return {"id": faq_id, "question": question.strip(), "answer": answer.strip(), "category": category}
        except NewApplicationError:
            raise
        except Exception as e:
            raise NewApplicationError(MemoryFAQUpdateError, e)
