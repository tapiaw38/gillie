import { useMutation, useQuery } from '@tanstack/vue-query'
import type { IAssistantService } from '@/services/assistant/assistantService'
import type {
  AssistantProfileParams,
  AssistantProfileResponse,
  AssistantProfileUpdateParams,
  ApiKeyParams,
  ApiKeyResponse,
  ApiKeyRemoveResponse,
  AssistantFileResponse,
  AssistantFileRemoveResponse,
  IntegrationResponse,
  IntegrationParams,
  ContactParams,
  ContactResponse,
  ContactListResponse,
  ContactDeleteResponse,
  OwnerMemoryListResponse,
} from '@/types/assistant.ts'

export const useAssistantQueries = (assistantService: IAssistantService) => {
  const addAssistantProfileMutation = useMutation<
    AssistantProfileResponse,
    Error,
    AssistantProfileParams
  >({
    mutationFn: assistantService.addAssistant.bind(assistantService),
  })

  const getAssistantProfileQuery = useQuery<AssistantProfileResponse, Error>({
    queryKey: ['getAssistantProfile'],
    queryFn: assistantService.getAssistant.bind(assistantService),
  })

  const updateAssistantProfileMutation = useMutation<
    AssistantProfileResponse,
    Error,
    AssistantProfileUpdateParams
  >({
    mutationFn: assistantService.updateAssistant.bind(assistantService),
  })

  const addApiKeyMutation = useMutation<ApiKeyResponse, Error, ApiKeyParams>({
    mutationFn: assistantService.addApiKey.bind(assistantService),
  })

  const removeApiKeyMutation = useMutation<ApiKeyRemoveResponse, Error, string>({
    mutationFn: assistantService.removeApiKey.bind(assistantService),
  })

  const listContactsQuery = useQuery<ContactListResponse, Error>({
    queryKey: ['listContacts'],
    queryFn: assistantService.listContacts.bind(assistantService),
    enabled: false,
  })

  const addContactMutation = useMutation<ContactResponse, Error, ContactParams>({
    mutationFn: assistantService.addContact.bind(assistantService),
  })

  const updateContactMutation = useMutation<ContactResponse, Error, { contactId: string; contact: ContactParams }>({
    mutationFn: ({ contactId, contact }) => assistantService.updateContact(contactId, contact),
  })

  const deleteContactMutation = useMutation<ContactDeleteResponse, Error, string>({
    mutationFn: assistantService.deleteContact.bind(assistantService),
  })

  const listOwnerMemoriesMutation = useMutation<
    OwnerMemoryListResponse,
    Error,
    { contact_id?: string; query?: string; limit?: number; offset?: number } | undefined
  >({
    mutationFn: assistantService.listOwnerMemories.bind(assistantService),
  })

  const addFilesMutation = useMutation<AssistantFileResponse, Error, File[]>({
    mutationFn: assistantService.addFiles.bind(assistantService),
  })

  const removeFileByIdMutation = useMutation<AssistantFileRemoveResponse, Error, string>({
    mutationFn: assistantService.removeFileById.bind(assistantService),
  })

  const addIntegrationMutation = useMutation<IntegrationResponse, Error, IntegrationParams>({
    mutationFn: assistantService.addIntegration.bind(assistantService),
  })

  const removeIntegrationByIdMutation = useMutation<IntegrationResponse, Error, string>({
    mutationFn: assistantService.removeIntegrationById.bind(assistantService),
  })

  return {
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
    addIntegrationMutation,
    removeIntegrationByIdMutation,
  }
}
