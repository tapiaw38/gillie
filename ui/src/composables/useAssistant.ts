import { inject } from 'vue'
import { storeToRefs } from 'pinia'
import { useAssistantStore } from '@/stores/assistantStore'
import type { IAssistantService } from '../services/assistant/assistantService'

export const useAssistant = () => {
  const services = inject<{ assistantService: IAssistantService }>('services')
  if (!services) throw new Error('Services not provided')

  const assistantService = services.assistantService

  const store = useAssistantStore(assistantService)
  const assistantStore = store()

  const {
    assistantProfile,
    ownerMemories,
    ownerMemoriesHasMore,
    ownerMemoriesNextOffset,
    filesVectorStatuses,

    isAddAssistantProfilePending,
    isAddAssistantProfileSuccess,
    isAddAssistantProfileError,
    addAssistantProfileError,

    isGetAssistantProfilePending,
    isGetAssistantProfileSuccess,
    isGetAssistantProfileError,
    getAssistantProfileError,

    isUpdateAssistantProfilePending,
    isUpdateAssistantProfileSuccess,
    isUpdateAssistantProfileError,
    updateAssistantProfileError,

    isAddApiKeyError,
    isAddApiKeyPending,
    isAddApiKeySuccess,
    addApiKeyError,

    isRemoveApiKeyPending,
    isRemoveApiKeySuccess,
    isRemoveApiKeyError,
    removeApiKeyError,

    isListContactsPending,
    isListContactsError,
    listContactsError,

    isAddContactPending,
    isAddContactSuccess,
    isAddContactError,
    addContactError,

    isUpdateContactPending,
    isUpdateContactSuccess,
    isUpdateContactError,
    updateContactError,

    isDeleteContactPending,
    isDeleteContactSuccess,
    isDeleteContactError,
    deleteContactError,

    isListOwnerMemoriesPending,
    isListOwnerMemoriesError,
    listOwnerMemoriesError,

    isAddFilesPending,
    isAddFilesSuccess,
    isAddFilesError,
    addFilesError,

    isRemoveFileByIdPending,
    isRemoveFileByIdSuccess,
    isRemoveFileByIdError,
    removeFileByIdError,

    isAddIntegrationPending,
    isAddIntegrationSuccess,
    isAddIntegrationError,
    addIntegrationError,

    isRemoveIntegrationByIdPending,
    isRemoveIntegrationByIdError,
    removeIntegrationByIdError,
  } = storeToRefs(assistantStore)

  const {
    addAssistantProfile,
    getAssistantProfile,
    updateAssistantProfile,
    addApiKey,
    removeApiKey,
    addFiles,
    listContacts,
    addContact,
    updateContact,
    deleteContact,
    listOwnerMemories,
    removeFileById,
    getFilesVectorStatus,
    addIntegration,
    removeIntegrationById,
  } = assistantStore

  return {
    // Data
    assistantProfile,
    ownerMemories,
    ownerMemoriesHasMore,
    ownerMemoriesNextOffset,
    filesVectorStatuses,

    addAssistantProfileError,
    isAddAssistantProfilePending,
    isAddAssistantProfileSuccess,
    isAddAssistantProfileError,

    isGetAssistantProfilePending,
    isGetAssistantProfileSuccess,
    isGetAssistantProfileError,
    getAssistantProfileError,

    isUpdateAssistantProfilePending,
    isUpdateAssistantProfileSuccess,
    isUpdateAssistantProfileError,
    updateAssistantProfileError,

    addApiKeyError,
    isAddApiKeyPending,
    isAddApiKeySuccess,
    isAddApiKeyError,

    isRemoveApiKeyPending,
    isRemoveApiKeySuccess,
    isRemoveApiKeyError,
    removeApiKeyError,

    isListContactsPending,
    isListContactsError,
    listContactsError,

    isAddContactPending,
    isAddContactSuccess,
    isAddContactError,
    addContactError,

    isUpdateContactPending,
    isUpdateContactSuccess,
    isUpdateContactError,
    updateContactError,

    isDeleteContactPending,
    isDeleteContactSuccess,
    isDeleteContactError,
    deleteContactError,

    isListOwnerMemoriesPending,
    isListOwnerMemoriesError,
    listOwnerMemoriesError,

    isAddFilesPending,
    isAddFilesSuccess,
    isAddFilesError,
    addFilesError,

    isRemoveFileByIdPending,
    isRemoveFileByIdSuccess,
    isRemoveFileByIdError,
    removeFileByIdError,

    isAddIntegrationPending,
    isAddIntegrationSuccess,
    isAddIntegrationError,
    addIntegrationError,

    isRemoveIntegrationByIdPending,
    isRemoveIntegrationByIdError,
    removeIntegrationByIdError,

    // Methods
    addAssistantProfile,
    getAssistantProfile,
    updateAssistantProfile,
    addApiKey,
    removeApiKey,
    addFiles,
    listContacts,
    addContact,
    updateContact,
    deleteContact,
    listOwnerMemories,
    removeFileById,
    getFilesVectorStatus,
    addIntegration,
    removeIntegrationById,
    reset: assistantStore.$reset,
  }
}
