from typing import Optional
from src.adapters.datasources.datasources import Datasources
from src.adapters.datasources.repositories.conversation.repository import Repository as ConversationRepository
from src.adapters.datasources.repositories.profile.repository import Repository as ProfileRepository
from src.adapters.datasources.repositories.calendar.repository import Repository as CalendarRepository
from src.adapters.datasources.repositories.inmemory.role_repository import RoleRepository, role_repository


class Repositories:
    def __init__(
            self,
            conversation: ConversationRepository,
            profile: ProfileRepository,
            role: RoleRepository,
            calendar: Optional[CalendarRepository] = None,
    ):
        self.conversation = conversation
        self.profile = profile
        self.role = role
        self.calendar = calendar

    @staticmethod
    def create_repositories(datasources: Datasources):
        calendar = None
        if (
            datasources.no_sql_calendar_sessions_client is not None
            and datasources.no_sql_calendar_events_client is not None
        ):
            calendar = CalendarRepository(datasources)

        return Repositories(
            conversation=ConversationRepository(datasources),
            profile=ProfileRepository(datasources),
            role=role_repository,
            calendar=calendar,
        )