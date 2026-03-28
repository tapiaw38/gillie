import type { AxiosInstance } from 'axios'
import type { AssistantConversationResponse } from '@/types/conversation'

export interface IConversationService {
  getUserConversation(): Promise<AssistantConversationResponse>
  deleteConversation(conversationId: string): Promise<void>
}

export class ConversationService implements IConversationService {
  constructor(private readonly api: AxiosInstance) {
    this.api = api
  }

  async getUserConversation(): Promise<AssistantConversationResponse> {
    const { data } = await this.api.get<AssistantConversationResponse>('/conversation/user')
    return data
  }

  async deleteConversation(conversationId: string): Promise<void> {
    await this.api.delete(`/conversation/${conversationId}`)
  }
}
