import type { AxiosInstance } from 'axios'
import type {
  AssistantProfileParams,
  AssistantProfileResponse,
  AssistantProfileUpdateParams,
  ApiKeyResponse,
  ApiKeyParams,
  ApiKeyRemoveResponse,
  AssistantFileResponse,
  AssistantFileRemoveResponse,
  AssistantFileVectorStatusResponse,
  IntegrationParams,
  IntegrationResponse,
  ProfileOptionsResponse,
  CustomProviderInput,
  ContactParams,
  ContactResponse,
  ContactListResponse,
  ContactDeleteResponse,
  OwnerMemoryListResponse,
} from '@/types/assistant.ts'
import type { WorkflowStepTestParams, WorkflowStepTestResponse } from '@/types/workflow.types'

export interface IAssistantService {
  addAssistant(assistantProfile: AssistantProfileParams): Promise<AssistantProfileResponse>
  getAssistant(): Promise<AssistantProfileResponse>
  updateAssistant(assistantProfile: AssistantProfileUpdateParams): Promise<AssistantProfileResponse>
  getOptions(): Promise<ProfileOptionsResponse>
  testWorkflowStep(payload: WorkflowStepTestParams): Promise<WorkflowStepTestResponse>
  setProvider(provider: string, api_key?: string): Promise<{ data: { provider: string; model: string } }>
  addProvider(input: CustomProviderInput): Promise<{ data: { name: string; model: string } }>
  addApiKey(apiKey: ApiKeyParams): Promise<ApiKeyResponse>
  removeApiKey(apiKeyId: string): Promise<ApiKeyRemoveResponse>
  listContacts(): Promise<ContactListResponse>
  addContact(contact: ContactParams): Promise<ContactResponse>
  updateContact(contactId: string, contact: ContactParams): Promise<ContactResponse>
  deleteContact(contactId: string): Promise<ContactDeleteResponse>
  listOwnerMemories(params?: { contact_id?: string; query?: string; limit?: number }): Promise<OwnerMemoryListResponse>
  addFiles(files: File[]): Promise<AssistantFileResponse>
  removeFileById(fileId: string): Promise<AssistantFileRemoveResponse>
  getFilesVectorStatus(): Promise<AssistantFileVectorStatusResponse>
  addIntegration(integration: IntegrationParams): Promise<IntegrationResponse>
  removeIntegrationById(integrationId: string): Promise<IntegrationResponse>
}

export class AssistantService implements IAssistantService {
  constructor(private readonly api: AxiosInstance) {
    this.api = api
  }

  async addAssistant(assistantProfile: AssistantProfileParams): Promise<AssistantProfileResponse> {
    const { data } = await this.api.post<AssistantProfileResponse>('/profile/', assistantProfile)
    return data
  }

  async getAssistant(): Promise<AssistantProfileResponse> {
    const { data } = await this.api.get<AssistantProfileResponse>('/profile/')
    return data
  }

  async updateAssistant(
    assistantProfile: AssistantProfileUpdateParams,
  ): Promise<AssistantProfileResponse> {
    const { data } = await this.api.patch<AssistantProfileResponse>('/profile/', assistantProfile)
    return data
  }

  async getOptions(): Promise<ProfileOptionsResponse> {
    const { data } = await this.api.get<ProfileOptionsResponse>('/profile/options')
    return data
  }

  async testWorkflowStep(payload: WorkflowStepTestParams): Promise<WorkflowStepTestResponse> {
    const { data } = await this.api.post<WorkflowStepTestResponse>(
      '/profile/functions/test-step',
      payload,
    )
    return data
  }

  async setProvider(provider: string, api_key?: string): Promise<{ data: { provider: string; model: string } }> {
    const { data } = await this.api.post('/system/provider', { provider, api_key: api_key || undefined })
    return data
  }

  async addProvider(input: CustomProviderInput): Promise<{ data: { name: string; model: string } }> {
    const { data } = await this.api.post('/system/provider/custom', input)
    return data
  }

  async addApiKey(apiKey: ApiKeyParams): Promise<ApiKeyResponse> {
    const { data } = await this.api.post<ApiKeyResponse>('/profile/api-key', apiKey)
    return data
  }

  async removeApiKey(apiKeyId: string): Promise<ApiKeyRemoveResponse> {
    const { data } = await this.api.delete<ApiKeyRemoveResponse>(`/profile/api-key/${apiKeyId}`)
    return data
  }

  async listContacts(): Promise<ContactListResponse> {
    const { data } = await this.api.get<ContactListResponse>('/profile/contacts')
    return data
  }

  async addContact(contact: ContactParams): Promise<ContactResponse> {
    const { data } = await this.api.post<ContactResponse>('/profile/contacts', contact)
    return data
  }

  async updateContact(contactId: string, contact: ContactParams): Promise<ContactResponse> {
    const { data } = await this.api.patch<ContactResponse>(`/profile/contacts/${contactId}`, contact)
    return data
  }

  async deleteContact(contactId: string): Promise<ContactDeleteResponse> {
    const { data } = await this.api.delete<ContactDeleteResponse>(`/profile/contacts/${contactId}`)
    return data
  }

  async listOwnerMemories(params?: { contact_id?: string; query?: string; limit?: number }): Promise<OwnerMemoryListResponse> {
    const { data } = await this.api.get<OwnerMemoryListResponse>('/api/v1/memory/owner/episodes', { params })
    return data
  }

  async addFiles(files: File[]): Promise<AssistantFileResponse> {
    const formData = new FormData()
    files.forEach((file) => {
      formData.append('files', file)
    })

    const { data } = await this.api.post<AssistantFileResponse>('/profile/files/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return data
  }

  async removeFileById(fileId: string): Promise<AssistantFileRemoveResponse> {
    const { data } = await this.api.delete<AssistantFileRemoveResponse>(`/profile/files/${fileId}`)
    return data
  }

  async getFilesVectorStatus(): Promise<AssistantFileVectorStatusResponse> {
    const { data } = await this.api.get<AssistantFileVectorStatusResponse>('/profile/files/status')
    return data
  }

  async addIntegration(integration: IntegrationParams): Promise<IntegrationResponse> {
    const { data } = await this.api.post<IntegrationResponse>('/profile/integrations', integration)
    return data
  }

  async removeIntegrationById(integrationId: string): Promise<IntegrationResponse> {
    const { data } = await this.api.delete<IntegrationResponse>(`/profile/integrations/${integrationId}`)
    return data
  }

}
