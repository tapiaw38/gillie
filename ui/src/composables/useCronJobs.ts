import { ref } from 'vue'
import services from '@/services'
import type { CronJob, CronJobInput, CronJobRunResult } from '@/types/cronJobs'
import { ApplicationError, getErrorMessage } from '@/types/error'

export const useCronJobs = () => {
  const jobs = ref<CronJob[]>([])
  const isLoading = ref(false)
  const isSubmitting = ref(false)
  const error = ref<string | null>(null)

  const loadJobs = async () => {
    isLoading.value = true
    error.value = null
    try {
      const response = await services.cronJobsService.listJobs()
      jobs.value = response.data ?? []
      return response
    } catch (err) {
      error.value = err instanceof ApplicationError ? getErrorMessage(err) : 'Error loading jobs'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  const createJob = async (job: CronJobInput) => {
    isSubmitting.value = true
    error.value = null
    try {
      return await services.cronJobsService.createJob(job)
    } catch (err) {
      error.value = err instanceof ApplicationError ? getErrorMessage(err) : 'Error creating job'
      throw err
    } finally {
      isSubmitting.value = false
    }
  }

  const deleteJob = async (jobId: string) => {
    error.value = null
    try {
      await services.cronJobsService.deleteJob(jobId)
      jobs.value = jobs.value.filter((job) => job.id !== jobId)
    } catch (err) {
      error.value = err instanceof ApplicationError ? getErrorMessage(err) : 'Error deleting job'
      throw err
    }
  }

  const runJob = async (jobId: string): Promise<CronJobRunResult> => {
    error.value = null
    try {
      return await services.cronJobsService.runJob(jobId)
    } catch (err) {
      error.value = err instanceof ApplicationError ? getErrorMessage(err) : 'Error running job'
      throw err
    }
  }

  return {
    jobs,
    isLoading,
    isSubmitting,
    error,
    loadJobs,
    createJob,
    deleteJob,
    runJob,
  }
}
