from src.adapters.datasources.datasources import Datasources
from src.adapters.datasources.repositories.conversation.repository import Repository as ConversationRepository
from src.adapters.datasources.repositories.profile.repository import Repository as ProfileRepository
from src.adapters.datasources.repositories.inmemory.role_repository import RoleRepository, role_repository


class Repositories:
    def __init__(
            self,
            conversation: ConversationRepository,
            profile: ProfileRepository,
            role: RoleRepository,
    ):
        self.conversation = conversation
        self.profile = profile
        self.role = role

    @staticmethod
    def create_repositories(datasources: Datasources):
        return Repositories(
            conversation=ConversationRepository(datasources),
            profile=ProfileRepository(datasources),
            role=role_repository,
        )