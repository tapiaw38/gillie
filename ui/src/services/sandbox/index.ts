import { server } from '@/api/request/server'
import { SandboxService } from './sandboxService'

const BASE_URL = import.meta.env.VITE_ASSISTANT_BASE_URL
export const sandboxService = new SandboxService(server({ baseURL: BASE_URL }))

export * from './sandboxService'
