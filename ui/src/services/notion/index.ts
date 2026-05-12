import { server } from '@/api/request/server'
import { NotionService } from './notionService'

const BASE_URL = import.meta.env.VITE_NOTION_BASE_URL || 'http://localhost:8000'

export const notionService = new NotionService(server({ baseURL: BASE_URL }))

export type {
  INotionService,
  NotionAuthorizationResponse,
  NotionStatusResponse,
} from './notionService'
