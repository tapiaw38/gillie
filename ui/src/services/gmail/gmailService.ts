import type { AxiosInstance } from 'axios'
import type { GmailAuthorizationResponse, GmailStatusResponse } from '@/types/gmail'

export interface GmailCredentialsResponse {
  client_id?: string
  redirect_uri?: string
  has_secret?: boolean
}

export interface IGmailService {
  getCredentials(): Promise<GmailCredentialsResponse>
  saveCredentials(clientId: string, clientSecret: string, redirectUri?: string): Promise<void>
  getAuthorizationUrl(profileId?: string): Promise<GmailAuthorizationResponse>
  checkStatus(profileId?: string): Promise<GmailStatusResponse>
}

export class GmailService implements IGmailService {
  constructor(private readonly api: AxiosInstance) {}

  async getCredentials(): Promise<GmailCredentialsResponse> {
    const { data } = await this.api.get<GmailCredentialsResponse>('/api/v1/gmail/credentials')
    return data
  }

  async saveCredentials(clientId: string, clientSecret: string, redirectUri?: string): Promise<void> {
    await this.api.post('/api/v1/gmail/credentials', {
      client_id: clientId,
      client_secret: clientSecret,
      ...(redirectUri ? { redirect_uri: redirectUri } : {}),
    })
  }

  async getAuthorizationUrl(profileId?: string): Promise<GmailAuthorizationResponse> {
    const params = profileId ? { profile_id: profileId } : {}
    const { data } = await this.api.get<GmailAuthorizationResponse>('/api/v1/gmail/authorize', { params })
    return data
  }

  async checkStatus(profileId?: string): Promise<GmailStatusResponse> {
    const params = profileId ? { profile_id: profileId } : {}
    const { data } = await this.api.get<GmailStatusResponse>('/api/v1/gmail/status', { params })
    return data
  }
}
