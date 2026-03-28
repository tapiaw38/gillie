from typing import Optional
from src.adapters.datasources.datasources import Datasources
from src.adapters.datasources.repositories.conversation.repository import Repository as ConversationRepository
from src.adapters.datasources.repositories.profile.repository import Repository as ProfileRepository
from src.adapters.datasources.repositories.calendar.repository import Repository as CalendarRepository
from src.adapters.datasources.repositories.drive.repository import Repository as DriveRepository
from src.adapters.datasources.repositories.whatsapp_device.repository import Repository as WhatsAppDeviceRepository
from src.adapters.datasources.repositories.job.repository import Repository as JobRepository
from src.adapters.datasources.repositories.inmemory.role_repository import RoleRepository, role_repository


class Repositories:
    def __init__(
            self,
            conversation: ConversationRepository,
            profile: ProfileRepository,
            role: RoleRepository,
            calendar: Optional[CalendarRepository] = None,
            drive: Optional[DriveRepository] = None,
            whatsapp_device: Optional[WhatsAppDeviceRepository] = None,
            job: Optional[JobRepository] = None,
    ):
        self.conversation = conversation
        self.profile = profile
        self.role = role
        self.calendar = calendar
        self.drive = drive
        self.whatsapp_device = whatsapp_device
        self.job = job

    @staticmethod
    def create_repositories(datasources: Datasources):
        calendar = None
        if datasources.no_sql_calendar_sessions_client is not None:
            calendar = CalendarRepository(datasources)

        drive = None
        if datasources.no_sql_drive_sessions_client is not None:
            drive = DriveRepository(datasources)

        whatsapp_device = None
        if datasources.no_sql_whatsapp_devices_client is not None:
            whatsapp_device = WhatsAppDeviceRepository(datasources)

        job = None
        if datasources.no_sql_jobs_client is not None:
            job = JobRepository(datasources)

        return Repositories(
            conversation=ConversationRepository(datasources),
            profile=ProfileRepository(datasources),
            role=role_repository,
            calendar=calendar,
            drive=drive,
            whatsapp_device=whatsapp_device,
            job=job,
        )