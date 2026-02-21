from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.memory import MemorySkillNotFoundError


class GetSkillsUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    def execute(self):
        skill_manager = self.context_factory().platform_managers.skill_manager
        return skill_manager.list_skills()

    def get_skill(self, name: str) -> str:
        skill_manager = self.context_factory().platform_managers.skill_manager
        if not skill_manager.skill_exists(name):
            raise NewApplicationError(MemorySkillNotFoundError)
        return skill_manager.load_skill(name)
