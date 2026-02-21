from dataclasses import dataclass
from src.core.platform.appcontext.appcontext import Factory
from src.core.use_cases.conversation import (
    CreateUseCase as ConversationCreateUseCase,
    FindByUserIdUseCase as ConversationFindByUserIdUseCase,
    FindByIdUseCase as ConversationFindByIdUseCase,
    AddMessageUseCase as ConversationAddMessageUseCase,
    DeleteAllMessagesUseCase as ConversationDeleteAllMessagesUseCase,
    DeleteUseCase as ConversationDeleteUseCase
)
from src.core.use_cases.profile import (
    CreateUseCase as ProfileCreateUseCase,
    FindByUserIdUseCase as ProfileFindByUserIdUseCase,
    FindAllUserIdsUseCase as ProfileFindAllUserIdsUseCase,
    FindAllUseCase as ProfileFindAllUseCase,
    UpdateUseCase as ProfileUpdateUseCase,
    AddApiKeyUseCase as ProfileAddApiKeyUseCase,
    DeleteApiKeyUseCase as ProfileDeleteApiKeyUseCase,
    AddFilesUseCase as ProfileAddFilesUseCase,
    DeleteFileByIdUseCase as ProfileDeleteFileByIdUseCase,
    AddIntegrationUseCase as ProfileAddIntegrationUseCase,
    ListOptionsUseCase as ProfileListOptionsUseCase,
    FindByWhatsAppBusinessIdUseCase as ProfileFindByWhatsAppBusinessIdUseCase,
    FindWithActiveWhatsAppIntegrationUseCase as ProfileFindWithActiveWhatsAppIntegrationUseCase
)
from src.core.use_cases.memory import (
    GetFAQsUseCase,
    AddFAQUseCase,
    UpdateFAQUseCase,
    DeleteFAQUseCase,
    GetSkillsUseCase,
    ExtractMemoryUseCase,
)
from src.core.use_cases.whatsapp import (
    ProcessWhatsAppMessageUseCase,
    TranscribeAudioUseCase
)
from src.core.use_cases.calendar import (
    GetAuthorizationUrlUseCase,
    HandleOAuthCallbackUseCase,
    CheckSessionStatusUseCase,
    CreateEventUseCase as CalendarCreateEventUseCase,
    ListEventsUseCase,
    UpdateEventUseCase as CalendarUpdateEventUseCase,
    DeleteEventUseCase as CalendarDeleteEventUseCase,
    SyncEventsUseCase,
)
from src.core.use_cases.drive import (
    GetAuthorizationUrlUseCase as DriveGetAuthorizationUrlUseCase,
    HandleOAuthCallbackUseCase as DriveHandleOAuthCallbackUseCase,
    CheckSessionStatusUseCase as DriveCheckSessionStatusUseCase,
    ListFilesUseCase,
    IngestFileUseCase,
    SyncDriveUseCase,
    SearchDriveUseCase,
    GetIndexStatusUseCase,
    RemoveFileIndexUseCase,
)


@dataclass
class Profile:
    create_usecase: ProfileCreateUseCase
    find_by_user_id_usecase: ProfileFindByUserIdUseCase
    find_all_user_ids_usecase: ProfileFindAllUserIdsUseCase
    find_all_usecase: ProfileFindAllUseCase
    update_usecase: ProfileUpdateUseCase
    add_api_key_usecase: ProfileAddApiKeyUseCase
    delete_api_key_usecase: ProfileDeleteApiKeyUseCase
    add_files_usecase: ProfileAddFilesUseCase
    delete_file_by_id_usecase: ProfileDeleteFileByIdUseCase
    add_integration_usecase: ProfileAddIntegrationUseCase
    list_options_usecase: ProfileListOptionsUseCase
    find_by_whatsapp_business_id_usecase: ProfileFindByWhatsAppBusinessIdUseCase
    find_with_active_whatsapp_integration_usecase: ProfileFindWithActiveWhatsAppIntegrationUseCase


@dataclass
class Conversation:
    create_usecase: ConversationCreateUseCase
    find_by_user_id_usecase: ConversationFindByUserIdUseCase
    find_by_id_usecase: ConversationFindByIdUseCase
    add_message_usecase: ConversationAddMessageUseCase
    delete_all_messages_usecase: ConversationDeleteAllMessagesUseCase
    delete_usecase: ConversationDeleteUseCase


@dataclass
class Memory:
    get_faqs_usecase: GetFAQsUseCase
    add_faq_usecase: AddFAQUseCase
    update_faq_usecase: UpdateFAQUseCase
    delete_faq_usecase: DeleteFAQUseCase
    get_skills_usecase: GetSkillsUseCase
    extract_memory_usecase: ExtractMemoryUseCase


@dataclass
class WhatsApp:
    process_message_usecase: ProcessWhatsAppMessageUseCase
    transcribe_audio_usecase: TranscribeAudioUseCase


@dataclass
class Calendar:
    get_authorization_url_usecase: GetAuthorizationUrlUseCase
    handle_oauth_callback_usecase: HandleOAuthCallbackUseCase
    check_session_status_usecase: CheckSessionStatusUseCase
    create_event_usecase: CalendarCreateEventUseCase
    list_events_usecase: ListEventsUseCase
    update_event_usecase: CalendarUpdateEventUseCase
    delete_event_usecase: CalendarDeleteEventUseCase
    sync_events_usecase: SyncEventsUseCase


@dataclass
class Drive:
    get_authorization_url_usecase: DriveGetAuthorizationUrlUseCase
    handle_oauth_callback_usecase: DriveHandleOAuthCallbackUseCase
    check_session_status_usecase: DriveCheckSessionStatusUseCase
    list_files_usecase: ListFilesUseCase
    ingest_file_usecase: IngestFileUseCase
    sync_drive_usecase: SyncDriveUseCase
    search_drive_usecase: SearchDriveUseCase
    get_index_status_usecase: GetIndexStatusUseCase
    remove_file_index_usecase: RemoveFileIndexUseCase


@dataclass
class Usecases:
    profile: Profile
    conversation: Conversation
    memory: Memory
    whatsapp: WhatsApp
    calendar: Calendar
    drive: Drive


def create_usecases(context_factory: Factory) -> Usecases:
    return Usecases(
        profile=Profile(
            create_usecase=ProfileCreateUseCase(context_factory),
            find_by_user_id_usecase=ProfileFindByUserIdUseCase(context_factory),
            find_all_user_ids_usecase=ProfileFindAllUserIdsUseCase(context_factory),
            find_all_usecase=ProfileFindAllUseCase(context_factory),
            update_usecase=ProfileUpdateUseCase(context_factory),
            add_api_key_usecase=ProfileAddApiKeyUseCase(context_factory),
            delete_api_key_usecase=ProfileDeleteApiKeyUseCase(context_factory),
            add_files_usecase=ProfileAddFilesUseCase(context_factory),
            delete_file_by_id_usecase=ProfileDeleteFileByIdUseCase(context_factory),
            add_integration_usecase=ProfileAddIntegrationUseCase(context_factory),
            list_options_usecase=ProfileListOptionsUseCase(context_factory),
            find_by_whatsapp_business_id_usecase=ProfileFindByWhatsAppBusinessIdUseCase(context_factory),
            find_with_active_whatsapp_integration_usecase=ProfileFindWithActiveWhatsAppIntegrationUseCase(context_factory),
        ),
        conversation=Conversation(
            create_usecase=ConversationCreateUseCase(context_factory),
            find_by_user_id_usecase=ConversationFindByUserIdUseCase(context_factory),
            find_by_id_usecase=ConversationFindByIdUseCase(context_factory),
            add_message_usecase=ConversationAddMessageUseCase(context_factory),
            delete_all_messages_usecase=ConversationDeleteAllMessagesUseCase(context_factory),
            delete_usecase=ConversationDeleteUseCase(context_factory),
        ),
        memory=Memory(
            get_faqs_usecase=GetFAQsUseCase(context_factory),
            add_faq_usecase=AddFAQUseCase(context_factory),
            update_faq_usecase=UpdateFAQUseCase(context_factory),
            delete_faq_usecase=DeleteFAQUseCase(context_factory),
            get_skills_usecase=GetSkillsUseCase(context_factory),
            extract_memory_usecase=ExtractMemoryUseCase(context_factory),
        ),
        whatsapp=WhatsApp(
            process_message_usecase=ProcessWhatsAppMessageUseCase(context_factory),
            transcribe_audio_usecase=TranscribeAudioUseCase(context_factory),
        ),
        calendar=Calendar(
            get_authorization_url_usecase=GetAuthorizationUrlUseCase(context_factory),
            handle_oauth_callback_usecase=HandleOAuthCallbackUseCase(context_factory),
            check_session_status_usecase=CheckSessionStatusUseCase(context_factory),
            create_event_usecase=CalendarCreateEventUseCase(context_factory),
            list_events_usecase=ListEventsUseCase(context_factory),
            update_event_usecase=CalendarUpdateEventUseCase(context_factory),
            delete_event_usecase=CalendarDeleteEventUseCase(context_factory),
            sync_events_usecase=SyncEventsUseCase(context_factory),
        ),
        drive=Drive(
            get_authorization_url_usecase=DriveGetAuthorizationUrlUseCase(context_factory),
            handle_oauth_callback_usecase=DriveHandleOAuthCallbackUseCase(context_factory),
            check_session_status_usecase=DriveCheckSessionStatusUseCase(context_factory),
            list_files_usecase=ListFilesUseCase(context_factory),
            ingest_file_usecase=IngestFileUseCase(context_factory),
            sync_drive_usecase=SyncDriveUseCase(context_factory),
            search_drive_usecase=SearchDriveUseCase(context_factory),
            get_index_status_usecase=GetIndexStatusUseCase(context_factory),
            remove_file_index_usecase=RemoveFileIndexUseCase(context_factory),
        ),
    )
