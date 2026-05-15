import { server } from '@/api/request/server'
import { JiraService } from './jiraService'

const BASE_URL = import.meta.env.VITE_ASSISTANT_BASE_URL || 'http://localhost:8000'

export const jiraService = new JiraService(server({ baseURL: BASE_URL }))

export { JiraService }
export type { IJiraService, JiraProject } from './jiraService'
