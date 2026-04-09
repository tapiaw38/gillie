import { inject } from 'vue'
import { storeToRefs } from 'pinia'
import { useCronJobsStore } from '@/stores/cronJobsStore'
import type { ICronJobsService } from '@/services/cronJobs/cronJobsService'

export const useCronJobs = () => {
  const services = inject<{ cronJobsService: ICronJobsService }>('services')
  if (!services) throw new Error('Services not provided')

  const store = useCronJobsStore(services.cronJobsService)
  const cronJobsStore = store()

  const {
    jobs,
    isListJobsPending,
    isListJobsError,
    listJobsError,
    isCreateJobPending,
    isCreateJobError,
    createJobError,
    isDeleteJobPending,
    isDeleteJobError,
    isRunJobPending,
    isRunJobError,
    runJobError,
  } = storeToRefs(cronJobsStore)

  const { listJobs, createJob, deleteJob, runJob } = cronJobsStore

  return {
    jobs,
    isListJobsPending,
    isListJobsError,
    listJobsError,
    isCreateJobPending,
    isCreateJobError,
    createJobError,
    isDeleteJobPending,
    isDeleteJobError,
    isRunJobPending,
    isRunJobError,
    runJobError,
    listJobs,
    createJob,
    deleteJob,
    runJob,
    reset: cronJobsStore.$reset,
  }
}
