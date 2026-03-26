import type { AxiosInstance } from 'axios'

export interface DriveAuthorizationResponse {
  authorization_url: string
  user_id: string
}

export interface DriveStatusResponse {
  is_active: boolean
  user_id: string
}

export interface IDriveService {
  saveCredentials(clientId: string, clientSecret: string, redirectUri?: string): Promise<void>
  getAuthorizationUrl(profileId?: string): Promise<DriveAuthorizationResponse>
  checkStatus(profileId?: string): Promise<DriveStatusResponse>
}

export class DriveService implements IDriveService {
  constructor(private readonly api: AxiosInstance) {
    this.api = api
  }

  async saveCredentials(clientId: string, clientSecret: string, redirectUri?: string): Promise<void> {
    await this.api.post('/drive/credentials', {
      client_id: clientId,
      client_secret: clientSecret,
      ...(redirectUri ? { redirect_uri: redirectUri } : {}),
    })
  }

  async getAuthorizationUrl(profileId?: string): Promise<DriveAuthorizationResponse> {
    const params = profileId ? { profile_id: profileId } : {}
    const { data } = await this.api.get<DriveAuthorizationResponse>('/drive/authorize', { params })
    return data
  }

  async checkStatus(profileId?: string): Promise<DriveStatusResponse> {
    const params = profileId ? { profile_id: profileId } : {}
    const { data } = await this.api.get<DriveStatusResponse>('/drive/status', { params })
    return data
  }
}
