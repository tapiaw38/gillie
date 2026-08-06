import type { AxiosInstance } from 'axios'

export interface AvatarAsset {
  type: 'model' | 'animation'
  name: string
  key: string
  url: string
}

export interface AvatarAssetsResponse {
  data: { model: AvatarAsset | null; animations: AvatarAsset[] }
}

export interface IAvatarService {
  listAssets(): Promise<AvatarAssetsResponse>
  uploadAsset(file: File, assetType: 'model' | 'animation'): Promise<AvatarAssetsResponse>
  removeAnimation(name: string): Promise<AvatarAssetsResponse>
  rebuild(): Promise<AvatarAssetsResponse>
}

export class AvatarService implements IAvatarService {
  constructor(private readonly api: AxiosInstance) {}

  async listAssets(): Promise<AvatarAssetsResponse> {
    const { data } = await this.api.get<AvatarAssetsResponse>('/profile/avatar/assets')
    return data
  }

  async uploadAsset(file: File, assetType: 'model' | 'animation'): Promise<AvatarAssetsResponse> {
    const form = new FormData()
    form.append('asset_type', assetType)
    form.append('file', file)
    const { data } = await this.api.post<AvatarAssetsResponse>('/profile/avatar/assets', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return data
  }

  async removeAnimation(name: string): Promise<AvatarAssetsResponse> {
    const { data } = await this.api.delete<AvatarAssetsResponse>(
      `/profile/avatar/assets/animation/${encodeURIComponent(name)}`,
    )
    return data
  }

  async rebuild(): Promise<AvatarAssetsResponse> {
    const { data } = await this.api.post<AvatarAssetsResponse>('/profile/avatar/assets/rebuild')
    return data
  }
}
