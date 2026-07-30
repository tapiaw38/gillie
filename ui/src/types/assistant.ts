export interface AssistantProfileParams {
  assistant_name: string
  functions: string
}

export interface AssistantProfileUpdateParams {
  assistant_name?: string
  functions?: string
  tts_enabled?: boolean
  tts_voice?: string
  tts_engine?: string
  tool_prompts?: string
  disabled_tools?: string[]
  response_language?: string
}

export interface ProviderOption {
  key: string
  model: string
  base_url: string
  auth_type: string
  api_key_set: boolean
  is_builtin: boolean
}

export interface VoiceOption {
  id: string
  label: string
}

export interface VoiceEngineOption {
  key: string
  label: string
  description: string
  requires_key: boolean
  key_available: boolean
  voices: VoiceOption[]
}

export interface ProfileOptionsResponse {
  data: {
    roles: { code: string; name: string }[]
    providers: ProviderOption[]
    active_provider: string
    voice_engines: VoiceEngineOption[]
  }
}

export interface CustomProviderInput {
  name: string
  base_url: string
  model: string
  auth_type: string
  api_key: string
}

export interface AssistantProfile {
  id: string
  assistant_name: string
  functions: string
  user_id: string
  created_at: string
  updated_at: string
  is_active: boolean
  tts_enabled: boolean
  tts_voice?: string
  tts_engine?: string
  response_language?: string
  iteration_limit: number
  api_keys: ApiKey[]
  contacts?: Contact[]
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
  contact_id: string
}

export interface ApiKey {
  id: string
  user_id: string
  value: string
  description: string
  contact_id: string
  contact_name: string
  is_active: boolean
  limit: number
  created_at: string
}

export interface Contact {
  id: string
  name: string
  channel?: string
  external_id?: string
  tags?: string[]
  notes?: string
}

export interface ContactParams {
  name: string
  channel?: string
  external_id?: string
  tags?: string[]
  notes?: string
}

export interface ContactResponse {
  data: Contact
}

export interface ContactListResponse {
  data: Contact[]
}

export interface ContactDeleteResponse {
  deleted: boolean
  id: string
}

export interface OwnerMemory {
  id: string
  owner_user_id?: string
  memory_scope_id?: string
  source_conversation_id?: string
  content: string
  importance: number
  emotion?: string
  tags: string[]
  created_at: string
}

export interface OwnerMemoryListResponse {
  data: OwnerMemory[]
  has_more: boolean
  next_offset?: number
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

export type FileVectorStatus = 'indexed' | 'processing' | 'not_indexed'

export interface AssistantFileVectorStatusResponse {
  data: {
    statuses: Record<string, FileVectorStatus>
  }
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

export interface GoogleGmailIntegrationConfig {
  profile_id: string
  is_connected?: boolean
}

export interface NotionIntegrationConfig {
  profile_id: string
  is_connected?: boolean
  workspace_name?: string
  owner_name?: string
}

export interface SQLDatabaseTableEntry {
  name: string
  description: string
}

export interface SQLDatabaseIntegrationConfig {
  connection_string: string
  allowed_tables: SQLDatabaseTableEntry[]
  blocked_keywords?: string[]
}

export interface IntegrationParams {
  id?: string
  name: string
  type: string
  activated: boolean
  config:
    | MeliIntegrationConfig
    | WhatsappIntegrationConfig
    | GoogleCalendarIntegrationConfig
    | GoogleDriveIntegrationConfig
    | GoogleGmailIntegrationConfig
    | NotionIntegrationConfig
    | SQLDatabaseIntegrationConfig
    | SystemCommandsIntegrationConfig
    | SlackIntegrationConfig
    | TelegramIntegrationConfig
    | ClickUpIntegrationConfig
    | JiraIntegrationConfig
    | TeamsIntegrationConfig
}

export interface ToolPromptsConfig {
  search_images?: string
  analyze_pdf?: string
  extract_text_from_pdf?: string
  analyze_excel?: string
  write_excel?: string
  read_docx?: string
  write_docx?: string
  modify_excel?: string
  modify_docx?: string
  insert_image_docx?: string
  insert_image_excel?: string
  insert_image_pptx?: string
  describe_image?: string
  search_documents?: string
  query_database?: string
  fetch_url?: string
  save_memory?: string
  web_search?: string
  organize_memory?: string
  search_memory?: string
  save_solution?: string
  system_propose?: string
  system_confirm?: string
  cron_create?: string
  cron_list?: string
  cron_delete?: string
  cron_run?: string
  read_file?: string
  write_file?: string
  edit_file?: string
  list_directory?: string
  find_files?: string
  download_file?: string
  run_shell?: string
  grep_files?: string
  git_status?: string
  git_diff?: string
  git_log?: string
  git_commit?: string
  send_file?: string
  send_screenshot?: string
  take_screenshot?: string
  browser_act?: string
  browser_extract?: string
  browser_navigate?: string
  browser_click?: string
  browser_type?: string
  browser_get_content?: string
  browser_screenshot?: string
  browser_close?: string
  browser_connect?: string
  browser_switch_tab?: string
  browser_enable_remote_debug?: string
  browser_evaluate?: string
  repo_map?: string
  check_code?: string
  read_pptx?: string
  write_pptx?: string
  modify_pptx?: string
}

export interface SystemCommandsIntegrationConfig {
  blacklist: string[]
  require_confirmation: boolean
}

export interface SlackIntegrationConfig {
  bot_token: string
  signing_secret: string
  team_id?: string
  team_name?: string
  bot_user_id?: string
}

export interface TelegramIntegrationConfig {
  bot_token: string
  secret_token: string
}

export interface ClickUpIntegrationConfig {
  api_token: string
}

export interface JiraIntegrationConfig {
  domain: string
  email: string
  api_token: string
}

export interface TeamsIntegrationConfig {
  app_id: string
  app_password: string
  tenant_id?: string
  bot_id?: string
  service_url?: string
}

export interface IntegrationResponse {
  data: Integration[]
}
