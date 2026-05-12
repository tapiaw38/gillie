import type { AxiosInstance } from 'axios'

export interface NotionAuthorizationResponse {
  authorization_url: string
  user_id: string
}

export interface NotionStatusResponse {
  is_active: boolean
  user_id: string
  workspace_name?: string
  workspace_icon?: string
  owner_name?: string
}

export interface NotionCredentialsResponse {
  client_id?: string
  redirect_uri?: string
  has_secret?: boolean
}

export interface INotionService {
  getCredentials(): Promise<NotionCredentialsResponse>
  saveCredentials(clientId: string, clientSecret: string, redirectUri?: string): Promise<void>
  getAuthorizationUrl(profileId?: string): Promise<NotionAuthorizationResponse>
  checkStatus(profileId?: string): Promise<NotionStatusResponse>
  disconnect(): Promise<void>
}

export class NotionService implements INotionService {
  constructor(private readonly api: AxiosInstance) {
    this.api = api
  }

  async getCredentials(): Promise<NotionCredentialsResponse> {
    const { data } = await this.api.get<NotionCredentialsResponse>('/api/v1/notion/credentials')
    return data
  }

  async saveCredentials(clientId: string, clientSecret: string, redirectUri?: string): Promise<void> {
    await this.api.post('/api/v1/notion/credentials', {
      client_id: clientId,
      client_secret: clientSecret,
      ...(redirectUri ? { redirect_uri: redirectUri } : {}),
    })
  }

  async getAuthorizationUrl(profileId?: string): Promise<NotionAuthorizationResponse> {
    const params = profileId ? { profile_id: profileId } : {}
    const { data } = await this.api.get<NotionAuthorizationResponse>('/api/v1/notion/authorize', { params })
    return data
  }

  async checkStatus(profileId?: string): Promise<NotionStatusResponse> {
    const params = profileId ? { profile_id: profileId } : {}
    const { data } = await this.api.get<NotionStatusResponse>('/api/v1/notion/status', { params })
    return data
  }

  async disconnect(): Promise<void> {
    await this.api.delete('/api/v1/notion/session')
  }
}
