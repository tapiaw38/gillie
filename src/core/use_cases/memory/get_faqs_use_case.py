from src.core.platform.appcontext.appcontext import Factory


class GetFAQsUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    def execute(self):
        skill_manager = self.context_factory().platform_managers.skill_manager
        return skill_manager.get_faqs()
