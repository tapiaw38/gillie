import type { AxiosInstance } from 'axios'

export interface SlackAuthTestResponse {
  ok: boolean
  url: string
  team: string
  user: string
  team_id: string
  user_id: string
  bot_id?: string
}

export interface ISlackService {
  authTest(): Promise<SlackAuthTestResponse>
}

export class SlackService implements ISlackService {
  constructor(private readonly api: AxiosInstance) {
    this.api = api
  }

  async authTest(): Promise<SlackAuthTestResponse> {
    const { data } = await this.api.get<{ data: SlackAuthTestResponse }>('/api/slack/auth-test')
    return data.data
  }
}
