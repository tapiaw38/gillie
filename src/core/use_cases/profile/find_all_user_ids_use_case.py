from src.core.platform.appcontext.appcontext import Factory


class FindAllUserIdsUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory()

    def execute(self):
        user_ids = self.context_factory.repositories.profile.find_all_user_ids()
        return user_ids