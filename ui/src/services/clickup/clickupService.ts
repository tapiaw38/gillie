import type { AxiosInstance } from 'axios'

export interface ClickUpWorkspace {
  id: string
  name: string
}

export interface IClickUpService {
  getWorkspaces(): Promise<ClickUpWorkspace[]>
}

export class ClickUpService implements IClickUpService {
  constructor(private readonly api: AxiosInstance) {
    this.api = api
  }

  async getWorkspaces(): Promise<ClickUpWorkspace[]> {
    const { data } = await this.api.get<{ data: ClickUpWorkspace[] }>('/api/v1/clickup/workspaces')
    return data.data
  }
}
