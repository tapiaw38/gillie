export interface CronJob {
  id: string
  profile_id: string
  name: string
  description: string
  cron_expr: string
  source_type: string
  source_params: Record<string, string>
  destination_type: string
  destination_params: Record<string, string>
  message_template: string
  enabled: boolean
  status: string
  last_run_at: string | null
  last_result: string | null
  created_at: string
  updated_at: string
}

export interface CronJobInput {
  name: string
  description: string
  cron_expr: string
  source_type: string
  source_params: Record<string, string>
  destination_type: string
  destination_params: Record<string, string>
  message_template: string
  enabled: boolean
}

export interface CronJobRunResult {
  status: string
  result: string
}

export interface CronJobsListResponse {
  data: CronJob[]
}

export interface CronJobResponse {
  data: CronJob
}
