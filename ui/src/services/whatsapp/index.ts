import { server } from '@/api/request/server'
import { WhatsAppService } from './whatsappService'

const BASE_URL = import.meta.env.VITE_WHATSAPP_API_BASE_URL || 'http://localhost:8083'

export const whatsappService = new WhatsAppService(server({ baseURL: BASE_URL }))

export * from './whatsappService'
