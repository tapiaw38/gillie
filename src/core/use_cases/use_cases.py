from dataclasses import dataclass
from src.core.platform.appcontext.appcontext import Factory
from src.core.use_cases.conversation import (
    CreateUseCase as ConversationCreateUseCase,
    FindByUserIdUseCase as ConversationFindByUserIdUseCase,
    FindByIdUseCase as ConversationFindByIdUseCase,
    AddMessageUseCase as ConversationAddMessageUseCase,
    DeleteAllMessagesUseCase as ConversationDeleteAllMessagesUseCase
)
from src.core.use_cases.profile import (
    CreateUseCase as ProfileCreateUseCase,
    FindByUserIdUseCase as ProfileFindByUserIdUseCase,
    FindAllUserIdsUseCase as ProfileFindAllUserIdsUseCase,
    UpdateUseCase as ProfileUpdateUseCase,
    ChangeStatusUseCase as ProfileChangeStatusUseCase,
    AddApiKeyUseCase as ProfileAddApiKeyUseCase,
    DeleteApiKeyUseCase as ProfileDeleteApiKeyUseCase,
    FindByApiKeyValueUseCase as ProfileFindByApiKeyValueUseCase,
    UpdateIterationLimitUseCase as ProfileUpdateIterationLimitUseCase,
    AddFilesUseCase as ProfileAddFilesUseCase,
    DeleteFileByIdUseCase as ProfileDeleteFileByIdUseCase,
    AddIntegrationUseCase as ProfileAddIntegrationUseCase,
    ListOptionsUseCase as ProfileListOptionsUseCase
)


@dataclass
class Profile:
    create_usecase: ProfileCreateUseCase
    find_by_user_id_usecase: ProfileFindByUserIdUseCase
    find_all_user_ids_usecase: ProfileFindAllUserIdsUseCase
    update_usecase: ProfileUpdateUseCase
    change_status_usecase: ProfileChangeStatusUseCase
    add_api_key_usecase: ProfileAddApiKeyUseCase
    delete_api_key_usecase: ProfileDeleteApiKeyUseCase
    find_by_api_key_value_usecase: ProfileFindByApiKeyValueUseCase
    update_iteration_limit_usecase: ProfileUpdateIterationLimitUseCase
    add_files_usecase: ProfileAddFilesUseCase
    delete_file_by_id_usecase: ProfileDeleteFileByIdUseCase
    add_integration_usecase: ProfileAddIntegrationUseCase
    list_options_usecase: ProfileListOptionsUseCase


@dataclass
class Conversation:
    create_usecase: ConversationCreateUseCase
    find_by_user_id_usecase: ConversationFindByUserIdUseCase
    find_by_id_usecase: ConversationFindByIdUseCase
    add_message_usecase: ConversationAddMessageUseCase
    delete_all_messages_usecase: ConversationDeleteAllMessagesUseCase


@dataclass
class Usecases:
    profile: Profile
    conversation: Conversation


def create_usecases(context_factory: Factory) -> Usecases:
    return Usecases(
        profile=Profile(
            create_usecase=ProfileCreateUseCase(context_factory),
            find_by_user_id_usecase=ProfileFindByUserIdUseCase(context_factory),
            find_all_user_ids_usecase=ProfileFindAllUserIdsUseCase(context_factory),
            update_usecase=ProfileUpdateUseCase(context_factory),
            change_status_usecase=ProfileChangeStatusUseCase(context_factory),
            add_api_key_usecase=ProfileAddApiKeyUseCase(context_factory),
            delete_api_key_usecase=ProfileDeleteApiKeyUseCase(context_factory),
            find_by_api_key_value_usecase=ProfileFindByApiKeyValueUseCase(context_factory),
            update_iteration_limit_usecase=ProfileUpdateIterationLimitUseCase(context_factory),
            add_files_usecase=ProfileAddFilesUseCase(context_factory),
            delete_file_by_id_usecase=ProfileDeleteFileByIdUseCase(context_factory),
            add_integration_usecase=ProfileAddIntegrationUseCase(context_factory),
            list_options_usecase=ProfileListOptionsUseCase(context_factory),
        ),
        conversation=Conversation(
            create_usecase=ConversationCreateUseCase(context_factory),
            find_by_user_id_usecase=ConversationFindByUserIdUseCase(context_factory),
            find_by_id_usecase=ConversationFindByIdUseCase(context_factory),
            add_message_usecase=ConversationAddMessageUseCase(context_factory),
            delete_all_messages_usecase=ConversationDeleteAllMessagesUseCase(context_factory),
        ),
    )