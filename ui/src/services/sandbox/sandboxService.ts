import type { AxiosInstance } from 'axios'
import type {
  SandboxConversationResponse,
  SandboxConversationDetailResponse,
  SandboxMessageResponse,
  CreateSandboxConversationParams,
  CreateSandboxConversationResponse,
} from '@/types/sandbox'

export interface ISandboxService {
  getSandboxConversations(): Promise<SandboxConversationResponse>
  getSandboxConversation(conversationId: string): Promise<SandboxConversationDetailResponse>
  createSandboxConversation(
    params: CreateSandboxConversationParams,
  ): Promise<CreateSandboxConversationResponse>
  sendSandboxMessage(
    conversationId: string,
    content: string,
    context?: string,
    hasImageProcessor?: 'activate' | 'deactivate',
    hasTextToVoice?: 'activate' | 'deactivate',
  ): Promise<SandboxMessageResponse>
  deleteSandboxConversation(conversationId: string): Promise<void>
}

export class SandboxService implements ISandboxService {
  constructor(private readonly api: AxiosInstance) {
    this.api = api
  }

  async getSandboxConversations(): Promise<SandboxConversationResponse> {
    const { data } = await this.api.get<SandboxConversationResponse>('/conversation/user', {
      params: {
        include_sandbox: true,
      },
    })
    return data
  }

  async getSandboxConversation(
    conversationId: string,
  ): Promise<SandboxConversationDetailResponse> {
    const { data } = await this.api.get<SandboxConversationDetailResponse>(
      `/conversation/${conversationId}`,
    )
    return data
  }

  async createSandboxConversation(
    params: CreateSandboxConversationParams,
  ): Promise<CreateSandboxConversationResponse> {
    const { data } = await this.api.post<CreateSandboxConversationResponse>(
      '/conversation/',
      params,
    )
    return data
  }

  async sendSandboxMessage(
    conversationId: string,
    content: string,
    context: string = '',
    hasImageProcessor: 'activate' | 'deactivate' = 'deactivate',
    hasTextToVoice: 'activate' | 'deactivate' = 'deactivate',
  ): Promise<SandboxMessageResponse> {
    const formData = new FormData()
    formData.append('content', content)
    formData.append('context', context)

    const { data } = await this.api.post<SandboxMessageResponse>(
      `/conversation/${conversationId}/message`,
      formData,
      {
        params: {
          has_image_processor: hasImageProcessor,
          has_text_to_voice: hasTextToVoice,
        },
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      },
    )
    return data
  }

  async deleteSandboxConversation(conversationId: string): Promise<void> {
    await this.api.delete(`/conversation/${conversationId}`)
  }
}
