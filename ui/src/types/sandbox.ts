export interface SandboxMessage {
  id: string
  content: string
  sender: 'user' | 'assistant'
  created_at: string
  audio_url?: string
}

export interface SandboxConversation {
  id: string
  title: string
  client_id: string
  is_sandbox: boolean
  created_at: string
  updated_at: string
  messages?: SandboxMessage[]
  message_count?: number
}

export interface SandboxConversationResponse {
  data: SandboxConversation[]
}

export interface SandboxConversationDetailResponse {
  data: {
    id: string
    title: string
    client_id: string
    is_sandbox: boolean
    created_at: string
    updated_at: string
    messages: SandboxMessage[]
  }
}

export interface SandboxMessageResponse {
  data: SandboxMessage[]
}

export interface CreateSandboxConversationParams {
  title: string
  is_sandbox: boolean
}

export interface CreateSandboxConversationResponse {
  data: SandboxConversation
}

export interface SendSandboxMessageParams {
  content: string
  context?: string
  has_image_processor?: 'activate' | 'deactivate'
  has_text_to_voice?: 'activate' | 'deactivate'
}
