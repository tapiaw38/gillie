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
    DeleteIntegrationUseCase as ProfileDeleteIntegrationUseCase,
    ListOptionsUseCase as ProfileListOptionsUseCase,
    FindByWhatsAppBusinessIdUseCase as ProfileFindByWhatsAppBusinessIdUseCase,
    FindWithActiveWhatsAppIntegrationUseCase as ProfileFindWithActiveWhatsAppIntegrationUseCase,
    FindWithActiveSlackIntegrationUseCase as ProfileFindWithActiveSlackIntegrationUseCase,
    FindWithActiveTelegramIntegrationUseCase as ProfileFindWithActiveTelegramIntegrationUseCase,
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
    SetCredentialsUseCase as CalendarSetCredentialsUseCase,
    GetCredentialsUseCase as CalendarGetCredentialsUseCase,
)
from src.core.use_cases.drive import (
    GetAuthorizationUrlUseCase as DriveGetAuthorizationUrlUseCase,
    HandleOAuthCallbackUseCase as DriveHandleOAuthCallbackUseCase,
    CheckSessionStatusUseCase as DriveCheckSessionStatusUseCase,
    ListFilesUseCase,
    DownloadFileUseCase,
    UploadFileUseCase,
    CreateFolderUseCase,
    MoveFileUseCase,
    SetCredentialsUseCase as DriveSetCredentialsUseCase,
    GetCredentialsUseCase as DriveGetCredentialsUseCase,
)
from src.core.use_cases.slack import ProcessSlackMessageUseCase
from src.core.use_cases.telegram import ProcessTelegramMessageUseCase
from src.core.use_cases.job import (
    CreateJobUseCase,
    ListJobsUseCase,
    GetJobUseCase,
    DeleteJobUseCase,
    RunJobUseCase,
)
from src.core.use_cases.whatsapp_device import (
    CreateDeviceUseCase as WhatsAppDeviceCreateUseCase,
    ListDevicesUseCase as WhatsAppDeviceListUseCase,
    GetDeviceUseCase as WhatsAppDeviceGetUseCase,
    DeleteDeviceUseCase as WhatsAppDeviceDeleteUseCase,
    AuthenticateDeviceUseCase as WhatsAppDeviceAuthenticateUseCase,
    ConnectDeviceUseCase as WhatsAppDeviceConnectUseCase,
    DisconnectDeviceUseCase as WhatsAppDeviceDisconnectUseCase,
    SendMessageUseCase as WhatsAppDeviceSendMessageUseCase,
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
    delete_integration_usecase: ProfileDeleteIntegrationUseCase
    list_options_usecase: ProfileListOptionsUseCase
    find_by_whatsapp_business_id_usecase: ProfileFindByWhatsAppBusinessIdUseCase
    find_with_active_whatsapp_integration_usecase: ProfileFindWithActiveWhatsAppIntegrationUseCase
    find_with_active_slack_integration_usecase: ProfileFindWithActiveSlackIntegrationUseCase
    find_with_active_telegram_integration_usecase: ProfileFindWithActiveTelegramIntegrationUseCase


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
    set_credentials_usecase: CalendarSetCredentialsUseCase
    get_credentials_usecase: CalendarGetCredentialsUseCase


@dataclass
class Drive:
    get_authorization_url_usecase: DriveGetAuthorizationUrlUseCase
    handle_oauth_callback_usecase: DriveHandleOAuthCallbackUseCase
    check_session_status_usecase: DriveCheckSessionStatusUseCase
    list_files_usecase: ListFilesUseCase
    download_file_usecase: DownloadFileUseCase
    upload_file_usecase: UploadFileUseCase
    create_folder_usecase: CreateFolderUseCase
    move_file_usecase: MoveFileUseCase
    set_credentials_usecase: DriveSetCredentialsUseCase
    get_credentials_usecase: DriveGetCredentialsUseCase


@dataclass
class WhatsAppDevice:
    create_usecase: WhatsAppDeviceCreateUseCase
    list_usecase: WhatsAppDeviceListUseCase
    get_usecase: WhatsAppDeviceGetUseCase
    delete_usecase: WhatsAppDeviceDeleteUseCase
    authenticate_usecase: WhatsAppDeviceAuthenticateUseCase
    connect_usecase: WhatsAppDeviceConnectUseCase
    disconnect_usecase: WhatsAppDeviceDisconnectUseCase
    send_message_usecase: WhatsAppDeviceSendMessageUseCase


@dataclass
class Jobs:
    create_usecase: CreateJobUseCase
    list_usecase: ListJobsUseCase
    get_usecase: GetJobUseCase
    delete_usecase: DeleteJobUseCase
    run_usecase: RunJobUseCase


@dataclass
class Slack:
    process_message_usecase: ProcessSlackMessageUseCase


@dataclass
class Telegram:
    process_message_usecase: ProcessTelegramMessageUseCase


@dataclass
class Usecases:
    profile: Profile
    conversation: Conversation
    memory: Memory
    whatsapp: WhatsApp
    calendar: Calendar
    drive: Drive
    whatsapp_device: WhatsAppDevice
    jobs: Jobs
    slack: Slack
    telegram: Telegram


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
            delete_integration_usecase=ProfileDeleteIntegrationUseCase(context_factory),
            list_options_usecase=ProfileListOptionsUseCase(context_factory),
            find_by_whatsapp_business_id_usecase=ProfileFindByWhatsAppBusinessIdUseCase(context_factory),
            find_with_active_whatsapp_integration_usecase=ProfileFindWithActiveWhatsAppIntegrationUseCase(context_factory),
            find_with_active_slack_integration_usecase=ProfileFindWithActiveSlackIntegrationUseCase(context_factory),
            find_with_active_telegram_integration_usecase=ProfileFindWithActiveTelegramIntegrationUseCase(context_factory),
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
            set_credentials_usecase=CalendarSetCredentialsUseCase(context_factory),
            get_credentials_usecase=CalendarGetCredentialsUseCase(context_factory),
        ),
        drive=Drive(
            get_authorization_url_usecase=DriveGetAuthorizationUrlUseCase(context_factory),
            handle_oauth_callback_usecase=DriveHandleOAuthCallbackUseCase(context_factory),
            check_session_status_usecase=DriveCheckSessionStatusUseCase(context_factory),
            list_files_usecase=ListFilesUseCase(context_factory),
            download_file_usecase=DownloadFileUseCase(context_factory),
            upload_file_usecase=UploadFileUseCase(context_factory),
            create_folder_usecase=CreateFolderUseCase(context_factory),
            move_file_usecase=MoveFileUseCase(context_factory),
            set_credentials_usecase=DriveSetCredentialsUseCase(context_factory),
            get_credentials_usecase=DriveGetCredentialsUseCase(context_factory),
        ),
        whatsapp_device=WhatsAppDevice(
            create_usecase=WhatsAppDeviceCreateUseCase(context_factory),
            list_usecase=WhatsAppDeviceListUseCase(context_factory),
            get_usecase=WhatsAppDeviceGetUseCase(context_factory),
            delete_usecase=WhatsAppDeviceDeleteUseCase(context_factory),
            authenticate_usecase=WhatsAppDeviceAuthenticateUseCase(context_factory),
            connect_usecase=WhatsAppDeviceConnectUseCase(context_factory),
            disconnect_usecase=WhatsAppDeviceDisconnectUseCase(context_factory),
            send_message_usecase=WhatsAppDeviceSendMessageUseCase(context_factory),
        ),
        jobs=Jobs(
            create_usecase=CreateJobUseCase(context_factory),
            list_usecase=ListJobsUseCase(context_factory),
            get_usecase=GetJobUseCase(context_factory),
            delete_usecase=DeleteJobUseCase(context_factory),
            run_usecase=RunJobUseCase(context_factory),
        ),
        slack=Slack(
            process_message_usecase=ProcessSlackMessageUseCase(context_factory),
        ),
        telegram=Telegram(
            process_message_usecase=ProcessTelegramMessageUseCase(context_factory),
        ),
    )
