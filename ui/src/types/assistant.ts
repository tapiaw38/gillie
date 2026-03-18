export interface AssistantProfileParams {
  assistant_name: string
  business_name: string
  functions: string
  business_context: string
}

export interface AssistantProfileUpdateParams {
  assistant_name?: string
  business_name?: string
  functions?: string
  business_context?: string
  tts_enabled?: boolean
  tool_prompts?: string
  disabled_tools?: string[]
}

export interface AssistantProfile {
  id: string
  assistant_name: string
  business_name: string
  functions: string
  business_context: string
  user_id: string
  created_at: string
  updated_at: string
  is_active: boolean
  tts_enabled: boolean
  iteration_limit: number
  api_keys: ApiKey[]
  files?: AssistantFile[]
  integrations?: Integration[]
  tool_prompts?: string
  disabled_tools?: string[]
}

export interface AssistantProfileResponse {
  data: AssistantProfile
}

export interface ApiKeyParams {
  description: string
}

export interface ApiKey {
  id: string
  user_id: string
  value: string
  description: string
  is_active: boolean
  limit: number
  created_at: string
}

export interface ApiKeyResponse {
  data: ApiKey[]
}

export interface ApiKeyRemoveID {
  id: string
}

export interface ApiKeyRemoveResponse {
  data: ApiKeyRemoveID
}

export interface AssistantFile {
  id: string
  name: string
  url: string
  created_at: string
}

export interface AssistantFileResponse {
  data: AssistantFile[]
}

export interface AssistantFileRemoveID {
  id: string
}

export interface AssistantFileRemoveResponse {
  data: AssistantFileRemoveID
}

export interface Integration {
  id: string
  name: string
  type: string
  activated: boolean
  config: Record<string, string>
  created_at?: string
  updated_at?: string
}

export interface MeliIntegrationConfig {
  app_id: string
  client_secret: string
}

export interface WhatsappIntegrationConfig {
  accessToken: string
  phoneNumberId: string
  businessAccountId: string
}

export interface GoogleCalendarIntegrationConfig {
  profile_id: string
  is_connected?: boolean
}

export interface GoogleDriveIntegrationConfig {
  profile_id: string
  is_connected?: boolean
}

export interface SQLDatabaseIntegrationConfig {
  connection_string: string
  allowed_table: string
  table_description: string
}

export interface IntegrationParams {
  name: string
  type: string
  activated: boolean
  config:
    | MeliIntegrationConfig
    | WhatsappIntegrationConfig
    | GoogleCalendarIntegrationConfig
    | GoogleDriveIntegrationConfig
    | SQLDatabaseIntegrationConfig
    | SystemCommandsIntegrationConfig
    | SlackIntegrationConfig
    | TelegramIntegrationConfig
}

export interface ToolPromptsConfig {
  search_images?: string
  analyze_pdf?: string
  extract_text_from_pdf?: string
  analyze_excel?: string
  describe_image?: string
  search_documents?: string
  query_database?: string
  save_memory?: string
  search_memory?: string
  system_propose?: string
  system_confirm?: string
  cron_create?: string
  cron_list?: string
  cron_delete?: string
  cron_run?: string
}

export interface SystemCommandsIntegrationConfig {
  blacklist: string[]
  require_confirmation: boolean
}

export interface SlackIntegrationConfig {
  bot_token: string
  signing_secret: string
}

export interface TelegramIntegrationConfig {
  bot_token: string
  secret_token: string
}

export interface IntegrationResponse {
  data: Integration[]
}

