from src.core.platform.appcontext.appcontext import Factory
from typing import List
from src.core.domain import Profile

class FindAllUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    async def execute(self) -> List[Profile]:
        """
        Encuentra todos los perfiles
        """
        context = self.context_factory()
        repository = context.repositories.profile
        profiles = await repository.find_all()
        return profiles
