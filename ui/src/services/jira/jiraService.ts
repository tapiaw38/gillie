import type { AxiosInstance } from 'axios'

export interface JiraProject {
  id: string
  key: string
  name: string
}

export interface IJiraService {
  getProjects(): Promise<JiraProject[]>
}

export class JiraService implements IJiraService {
  constructor(private readonly api: AxiosInstance) {
    this.api = api
  }

  async getProjects(): Promise<JiraProject[]> {
    const { data } = await this.api.get<{ data: JiraProject[] }>('/api/v1/jira/projects')
    return data.data
  }
}
