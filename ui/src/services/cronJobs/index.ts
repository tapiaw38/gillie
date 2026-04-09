import { server } from '@/api/request/server'
import { CronJobsService } from './cronJobsService'

const BASE_URL = import.meta.env.VITE_ASSISTANT_BASE_URL || 'http://localhost:8000'

export const cronJobsService = new CronJobsService(server({ baseURL: BASE_URL }))

export { CronJobsService }
export type { ICronJobsService } from './cronJobsService'
