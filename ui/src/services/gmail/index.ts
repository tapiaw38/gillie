import { server } from '@/api/request/server'
import { GmailService } from './gmailService'

const BASE_URL = import.meta.env.VITE_GMAIL_BASE_URL || 'http://localhost:8000'

export const gmailService = new GmailService(server({ baseURL: BASE_URL }))

export { GmailService }
export type { IGmailService } from './gmailService'
