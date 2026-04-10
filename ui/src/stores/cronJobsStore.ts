import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useCronJobsQueries } from '@/queries/cronJobs'
import type { ICronJobsService } from '@/services/cronJobs/cronJobsService'
import type { CronJob, CronJobInput } from '@/types/cronJobs'

export const useCronJobsStore = (cronJobsService: ICronJobsService) =>
  defineStore('cronJobs', () => {
    const jobs = ref<CronJob[]>([])

    const { listJobsQuery, createJobMutation, deleteJobMutation, runJobMutation } =
      useCronJobsQueries(cronJobsService)

    const listJobs = async () => {
      const { data } = await listJobsQuery.refetch()
      jobs.value = data?.data ?? []
      return data
    }

    const createJob = async (job: CronJobInput) => {
      const response = await createJobMutation.mutateAsync(job)
      jobs.value.push(response.data)
      return response
    }

    const deleteJob = async (jobId: string) => {
      await deleteJobMutation.mutateAsync(jobId)
      jobs.value = jobs.value.filter((j) => j.id !== jobId)
    }

    const runJob = async (jobId: string) => {
      return runJobMutation.mutateAsync(jobId)
    }

    return {
      jobs,

      listJobs,
      createJob,
      deleteJob,
      runJob,

      isListJobsPending: listJobsQuery.isPending,
      isListJobsError: listJobsQuery.isError,
      listJobsError: listJobsQuery.error,

      isCreateJobPending: createJobMutation.isPending,
      isCreateJobError: createJobMutation.isError,
      createJobError: createJobMutation.error,

      isDeleteJobPending: deleteJobMutation.isPending,
      isDeleteJobError: deleteJobMutation.isError,

      isRunJobPending: runJobMutation.isPending,
      isRunJobError: runJobMutation.isError,
      runJobError: runJobMutation.error,
    }
  })
