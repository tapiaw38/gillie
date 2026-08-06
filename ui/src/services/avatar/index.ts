import { server } from '@/api/request/server'
import { AvatarService } from './avatarService'

const BASE_URL = import.meta.env.VITE_ASSISTANT_BASE_URL
export const avatarService = new AvatarService(server({ baseURL: BASE_URL }))
