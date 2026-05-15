import { server } from '@/api/request/server'
import { TeamsService } from './teamsService'

const BASE_URL = import.meta.env.VITE_ASSISTANT_BASE_URL || 'http://localhost:8000'

export const teamsService = new TeamsService(server({ baseURL: BASE_URL }))

export { TeamsService }
export type { ITeamsService } from './teamsService'
