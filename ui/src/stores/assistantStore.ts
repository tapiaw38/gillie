import { defineStore } from 'pinia'
import { useAssistantQueries } from '@/queries/assistant'
import { ref } from 'vue'
import type { IAssistantService } from '@/services/assistant/assistantService'
import type {
  AssistantProfileParams,
  AssistantProfile,
  AssistantProfileResponse,
  AssistantProfileUpdateParams,
  ApiKeyResponse,
  ApiKeyParams,
  ApiKeyRemoveResponse,
  IntegrationParams,
  ContactParams,
  ContactResponse,
  ContactDeleteResponse,
  OwnerMemory,
  FileVectorStatus,
} from '@/types/assistant.ts'

export const useAssistantStore = (assistantService: IAssistantService) =>
  defineStore('assistant', () => {
    const assistantProfile = ref<AssistantProfile | null | undefined>(null)
    const ownerMemories = ref<OwnerMemory[]>([])
    const ownerMemoriesHasMore = ref(false)
    const ownerMemoriesNextOffset = ref<number | null>(null)
    const filesVectorStatuses = ref<Record<string, FileVectorStatus>>({})

    const {
      addAssistantProfileMutation,
      getAssistantProfileQuery,
      updateAssistantProfileMutation,
      addApiKeyMutation,
      removeApiKeyMutation,
      listContactsQuery,
      addContactMutation,
      updateContactMutation,
      deleteContactMutation,
      listOwnerMemoriesMutation,
      addFilesMutation,
      removeFileByIdMutation,
      getFilesVectorStatusQuery,
      addIntegrationMutation,
      removeIntegrationByIdMutation,
    } = useAssistantQueries(assistantService)

    const addAssistantProfile = async (params: AssistantProfileParams) => {
      try {
        const response: AssistantProfileResponse =
          await addAssistantProfileMutation.mutateAsync(params)
        assistantProfile.value = response.data
      } catch (error) {
        console.error('Failed to add assistant profile:', error)
        throw error
      }
    }

    const ensureAssistantProfileLoaded = async () => {
      if (assistantProfile.value) {
        return
      }
      const { data } = await getAssistantProfileQuery.refetch()
      assistantProfile.value = data?.data || null
      if (!assistantProfile.value) {
        throw new Error('Assistant profile is not available')
      }
    }

    const getAssistantProfile = async () => {
      try {
        const { data } = await getAssistantProfileQuery.refetch()
        assistantProfile.value = data?.data
      } catch (error) {
        console.error('Failed to fetch assistant profile data:', error)
        throw error
      }
    }

    const updateAssistantProfile = async (params: AssistantProfileUpdateParams) => {
      try {
        const data = await updateAssistantProfileMutation.mutateAsync(params)
        assistantProfile.value = data?.data
      } catch (error) {
        console.error('Failed to update assistant profile:', error)
        throw error
      }
    }

    const addApiKey = async (params: ApiKeyParams) => {
      try {
        await ensureAssistantProfileLoaded()
        const data: ApiKeyResponse = await addApiKeyMutation.mutateAsync(params)
        assistantProfile.value!.api_keys = [...data?.data]
      } catch (error) {
        console.error('Failed to add api key:', error)
        throw error
      }
    }

    const removeApiKey = async (apiKeyId: string) => {
      try {
        await ensureAssistantProfileLoaded()
        const data: ApiKeyRemoveResponse = await removeApiKeyMutation.mutateAsync(apiKeyId)
        const apiKey = assistantProfile.value!.api_keys.find(
          (apiKey) => apiKey.id === data?.data.id,
        )
        if (apiKey) {
          apiKey.is_active = false
        }
      } catch (error) {
        console.error('Failed to remove api key:', error)
        throw error
      }
    }

    const addFiles = async (files: File[]) => {
      try {
        const data = await addFilesMutation.mutateAsync(files)
        assistantProfile.value!.files = [...data?.data]
      } catch (error) {
        console.error('Failed to add files:', error)
        throw error
      }
    }

    const listContacts = async () => {
      try {
        await ensureAssistantProfileLoaded()
        const { data } = await listContactsQuery.refetch()
        assistantProfile.value!.contacts = data?.data || []
      } catch (error) {
        console.error('Failed to list contacts:', error)
        throw error
      }
    }

    const addContact = async (contact: ContactParams) => {
      try {
        await ensureAssistantProfileLoaded()
        const data: ContactResponse = await addContactMutation.mutateAsync(contact)
        assistantProfile.value!.contacts = [...(assistantProfile.value!.contacts || []), data.data]
      } catch (error) {
        console.error('Failed to add contact:', error)
        throw error
      }
    }

    const updateContact = async (contactId: string, contact: ContactParams) => {
      try {
        await ensureAssistantProfileLoaded()
        const data: ContactResponse = await updateContactMutation.mutateAsync({ contactId, contact })
        assistantProfile.value!.contacts = (assistantProfile.value!.contacts || []).map((item) =>
          item.id === data.data.id ? data.data : item,
        )
      } catch (error) {
        console.error('Failed to update contact:', error)
        throw error
      }
    }

    const deleteContact = async (contactId: string) => {
      try {
        await ensureAssistantProfileLoaded()
        const data: ContactDeleteResponse = await deleteContactMutation.mutateAsync(contactId)
        assistantProfile.value!.contacts = (assistantProfile.value!.contacts || []).filter((item) => item.id !== data.id)
      } catch (error) {
        console.error('Failed to delete contact:', error)
        throw error
      }
    }

    const listOwnerMemories = async (
      params?: { contact_id?: string; query?: string; limit?: number; offset?: number; append?: boolean },
    ) => {
      try {
        const append = Boolean(params?.append)
        const apiParams = params
          ? {
              contact_id: params.contact_id,
              query: params.query,
              limit: params.limit,
              offset: params.offset,
            }
          : undefined
        const data = await listOwnerMemoriesMutation.mutateAsync(apiParams)
        const list = data?.data || []
        ownerMemories.value = append ? [...ownerMemories.value, ...list] : list
        ownerMemoriesHasMore.value = Boolean(data?.has_more)
        ownerMemoriesNextOffset.value = data?.next_offset ?? null
      } catch (error) {
        console.error('Failed to list owner memories:', error)
        throw error
      }
    }

    const removeFileById = async (fileId: string) => {
      try {
        const data = await removeFileByIdMutation.mutateAsync(fileId)
        assistantProfile.value!.files = assistantProfile.value!.files?.filter(
          (file) => file.id !== data?.data.id,
        )
      } catch (error) {
        console.error('Failed to remove file:', error)
        throw error
      }
    }

    const getFilesVectorStatus = async () => {
      try {
        const { data } = await getFilesVectorStatusQuery.refetch()
        filesVectorStatuses.value = data?.data.statuses || {}
      } catch (error) {
        console.error('Failed to fetch files vector status:', error)
        throw error
      }
    }

    const addIntegration = async (integration: IntegrationParams) => {
      try {
        const data = await addIntegrationMutation.mutateAsync(integration)
        assistantProfile.value!.integrations = [...data?.data]
      } catch (error) {
        console.error('Failed to add integration:', error)
        throw error
      }
    }

    const removeIntegrationById = async (integrationId: string) => {
      try {
        const data = await removeIntegrationByIdMutation.mutateAsync(integrationId)
        assistantProfile.value!.integrations = [...data?.data]
      } catch (error) {
        console.error('Failed to remove integration:', error)
        throw error
      }
    }

    return {
      assistantProfile,
      ownerMemories,
      ownerMemoriesHasMore,
      ownerMemoriesNextOffset,
      filesVectorStatuses,
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

      isAddAssistantProfilePending: addAssistantProfileMutation.isPending,
      isAddAssistantProfileSuccess: addAssistantProfileMutation.isSuccess,
      isAddAssistantProfileError: addAssistantProfileMutation.isError,
      addAssistantProfileError: addAssistantProfileMutation.error,

      isGetAssistantProfilePending: getAssistantProfileQuery.isPending,
      isGetAssistantProfileSuccess: getAssistantProfileQuery.isSuccess,
      isGetAssistantProfileError: getAssistantProfileQuery.isError,
      getAssistantProfileError: getAssistantProfileQuery.error,

      isUpdateAssistantProfilePending: updateAssistantProfileMutation.isPending,
      isUpdateAssistantProfileSuccess: updateAssistantProfileMutation.isSuccess,
      isUpdateAssistantProfileError: updateAssistantProfileMutation.isError,
      updateAssistantProfileError: updateAssistantProfileMutation.error,

      addApiKeyError: addApiKeyMutation.error,
      isAddApiKeyPending: addApiKeyMutation.isPending,
      isAddApiKeySuccess: addApiKeyMutation.isSuccess,
      isAddApiKeyError: addApiKeyMutation.isError,

      isRemoveApiKeyPending: removeApiKeyMutation.isPending,
      isRemoveApiKeySuccess: removeApiKeyMutation.isSuccess,
      isRemoveApiKeyError: removeApiKeyMutation.isError,
      removeApiKeyError: removeApiKeyMutation.error,

      isListContactsPending: listContactsQuery.isPending,
      isListContactsError: listContactsQuery.isError,
      listContactsError: listContactsQuery.error,

      isAddContactPending: addContactMutation.isPending,
      isAddContactSuccess: addContactMutation.isSuccess,
      isAddContactError: addContactMutation.isError,
      addContactError: addContactMutation.error,

      isUpdateContactPending: updateContactMutation.isPending,
      isUpdateContactSuccess: updateContactMutation.isSuccess,
      isUpdateContactError: updateContactMutation.isError,
      updateContactError: updateContactMutation.error,

      isDeleteContactPending: deleteContactMutation.isPending,
      isDeleteContactSuccess: deleteContactMutation.isSuccess,
      isDeleteContactError: deleteContactMutation.isError,
      deleteContactError: deleteContactMutation.error,

      isListOwnerMemoriesPending: listOwnerMemoriesMutation.isPending,
      isListOwnerMemoriesError: listOwnerMemoriesMutation.isError,
      listOwnerMemoriesError: listOwnerMemoriesMutation.error,

      isAddFilesPending: addFilesMutation.isPending,
      isAddFilesSuccess: addFilesMutation.isSuccess,
      isAddFilesError: addFilesMutation.isError,
      addFilesError: addFilesMutation.error,

      isRemoveFileByIdPending: removeFileByIdMutation.isPending,
      isRemoveFileByIdSuccess: removeFileByIdMutation.isSuccess,
      isRemoveFileByIdError: removeFileByIdMutation.isError,
      removeFileByIdError: removeFileByIdMutation.error,

      isAddIntegrationPending: addIntegrationMutation.isPending,
      isAddIntegrationSuccess: addIntegrationMutation.isSuccess,
      isAddIntegrationError: addIntegrationMutation.isError,
      addIntegrationError: addIntegrationMutation.error,

      isRemoveIntegrationByIdPending: removeIntegrationByIdMutation.isPending,
      isRemoveIntegrationByIdError: removeIntegrationByIdMutation.isError,
      removeIntegrationByIdError: removeIntegrationByIdMutation.error,
    }
  })
