import { server } from '@/api/request/server'
import { ClickUpService } from './clickupService'

const BASE_URL = import.meta.env.VITE_ASSISTANT_BASE_URL || 'http://localhost:8000'

export const clickupService = new ClickUpService(server({ baseURL: BASE_URL }))

export { ClickUpService }
export type { IClickUpService, ClickUpWorkspace } from './clickupService'
