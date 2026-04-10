import { server } from '@/api/request/server'
import { TelegramService } from './telegramService'

const BASE_URL = import.meta.env.VITE_ASSISTANT_BASE_URL || 'http://localhost:8000'

export const telegramService = new TelegramService(server({ baseURL: BASE_URL }))

export { TelegramService }
export type { ITelegramService, TelegramWebhookResponse } from './telegramService'
