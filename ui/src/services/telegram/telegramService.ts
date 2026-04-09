import type { AxiosInstance } from 'axios'

export interface TelegramWebhookResponse {
  success?: boolean
  error?: string
  message?: string
}

export interface ITelegramService {
  registerWebhook(webhookUrl: string): Promise<TelegramWebhookResponse>
}

export class TelegramService implements ITelegramService {
  constructor(private readonly api: AxiosInstance) {
    this.api = api
  }

  async registerWebhook(webhookUrl: string): Promise<TelegramWebhookResponse> {
    const { data } = await this.api.post<TelegramWebhookResponse>(
      '/api/telegram/set-webhook',
      { webhook_url: webhookUrl },
    )
    return data
  }
}
