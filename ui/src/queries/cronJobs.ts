import { useQuery, useMutation } from '@tanstack/vue-query'
import type { ICronJobsService } from '@/services/cronJobs/cronJobsService'
import type { CronJobInput } from '@/types/cronJobs'

export const useCronJobsQueries = (cronJobsService: ICronJobsService) => {
  const listJobsQuery = useQuery({
    queryKey: ['cronJobs'],
    queryFn: cronJobsService.listJobs.bind(cronJobsService),
  })

  const createJobMutation = useMutation({
    mutationFn: (job: CronJobInput) => cronJobsService.createJob(job),
  })

  const deleteJobMutation = useMutation({
    mutationFn: (jobId: string) => cronJobsService.deleteJob(jobId),
  })

  const runJobMutation = useMutation({
    mutationFn: (jobId: string) => cronJobsService.runJob(jobId),
  })

  return {
    listJobsQuery,
    createJobMutation,
    deleteJobMutation,
    runJobMutation,
  }
}
