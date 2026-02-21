from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.memory import MemoryFAQNotFoundError, MemoryFAQDeleteError


class DeleteFAQUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    def execute(self, faq_id: str) -> dict:
        try:
            skill_manager = self.context_factory().platform_managers.skill_manager
            deleted = skill_manager.delete_faq(faq_id)
            if not deleted:
                raise NewApplicationError(MemoryFAQNotFoundError)
            return {"id": faq_id, "deleted": True}
        except NewApplicationError:
            raise
        except Exception as e:
            raise NewApplicationError(MemoryFAQDeleteError, e)
