import { server } from '@/api/request/server'
import { SlackService } from './slackService'

const BASE_URL = import.meta.env.VITE_ASSISTANT_BASE_URL || 'http://localhost:8000'

export const slackService = new SlackService(server({ baseURL: BASE_URL }))

export { SlackService }
export type { ISlackService, SlackAuthTestResponse } from './slackService'
