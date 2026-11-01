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
  streamSandboxMessage(
    conversationId: string,
    content: string,
    apiKey: string,
    workspace?: string,
    signal?: AbortSignal,
    runId?: string,
  ): Promise<Response>
  approveToolRequest(
    requestId: string,
    approved: boolean,
    apiKey: string,
    feedback?: string,
  ): Promise<void>
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

  async streamSandboxMessage(
    conversationId: string,
    content: string,
    apiKey: string,
    workspace?: string,
    signal?: AbortSignal,
    runId?: string,
  ): Promise<Response> {
    const baseURL = this.api.defaults.baseURL?.replace(/\/$/, '') ?? ''
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      'x-api-key': apiKey,
    }

    if (workspace) {
      headers['X-Gillie-Workspace'] = workspace
    }
    if (runId) headers['X-Gillie-Run-Id'] = runId

    return fetch(`${baseURL}/conversation/${conversationId}/message/stream`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ content }),
      signal,
    })
  }

  async approveToolRequest(
    requestId: string,
    approved: boolean,
    apiKey: string,
    feedback: string = '',
  ): Promise<void> {
    await this.api.post(
      '/conversation/tool/approve',
      {
        request_id: requestId,
        approved,
        feedback,
      },
      {
        headers: {
          'x-api-key': apiKey,
        },
      },
    )
  }

  async deleteSandboxConversation(conversationId: string): Promise<void> {
    await this.api.delete(`/conversation/${conversationId}`)
  }
}
