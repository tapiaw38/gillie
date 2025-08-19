from src.core.platform.appcontext.appcontext import Factory
from typing import List
from src.core.domain.model import Profile

class FindAllUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory()

    def execute(self) -> List[Profile]:
        """
        Encuentra todos los perfiles
        """
        try:
            repository = self.context_factory.create_profile_repository()
            profiles = repository.find_all()
            return profiles
        except Exception as e:
            raise Exception(f"Error al buscar todos los perfiles: {e}")
