import type { AxiosInstance } from 'axios'
import type {
  CronJobInput,
  CronJobResponse,
  CronJobsListResponse,
  CronJobRunResult,
} from '@/types/cronJobs'

export interface ICronJobsService {
  listJobs(): Promise<CronJobsListResponse>
  createJob(job: CronJobInput): Promise<CronJobResponse>
  deleteJob(jobId: string): Promise<void>
  runJob(jobId: string): Promise<CronJobRunResult>
}

export class CronJobsService implements ICronJobsService {
  constructor(private readonly api: AxiosInstance) {
    this.api = api
  }

  async listJobs(): Promise<CronJobsListResponse> {
    const { data } = await this.api.get<CronJobsListResponse>('/api/v1/jobs')
    return data
  }

  async createJob(job: CronJobInput): Promise<CronJobResponse> {
    const { data } = await this.api.post<CronJobResponse>('/api/v1/jobs', job)
    return data
  }

  async deleteJob(jobId: string): Promise<void> {
    await this.api.delete(`/api/v1/jobs/${jobId}`)
  }

  async runJob(jobId: string): Promise<CronJobRunResult> {
    const { data } = await this.api.post<CronJobRunResult>(`/api/v1/jobs/${jobId}/run`)
    return data
  }
}
