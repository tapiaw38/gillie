import type { AxiosInstance } from 'axios'

export interface ITeamsService {
  verifyConnection(): Promise<{ status: string; message: string }>
}

export class TeamsService implements ITeamsService {
  constructor(private readonly api: AxiosInstance) {}

  async verifyConnection(): Promise<{ status: string; message: string }> {
    const { data } = await this.api.post<{ status: string; message: string }>(
      '/api/teams/verify',
    )
    return data
  }
}
