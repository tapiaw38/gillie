import { ref, type Ref } from 'vue'
import { useToast } from 'primevue/usetoast'
import {
  ApplicationError,
  getErrorMessage,
  isAuthError,
  type ApiErrorResponse,
} from '@/types/error'
import type { AxiosError } from 'axios'

export interface UseApiErrorOptions {
  showToast?: boolean
  toastSummary?: string
  toastLife?: number
  onAuthError?: () => void
  onError?: (error: ApplicationError) => void
}

export const useApiError = (options: UseApiErrorOptions = {}) => {
  const {
    showToast = true,
    toastSummary = 'Error',
    toastLife = 5000,
    onAuthError,
    onError,
  } = options

  const toast = useToast()
  const error = ref<ApplicationError | null>(null)
  const isError = ref(false)

  const parseAxiosError = (axiosError: AxiosError): ApplicationError => {
    if (axiosError.response?.data) {
      const data = axiosError.response.data as {
        code?: string
        message?: string
        [key: string]: unknown
      }

      if (data.code && data.message) {
        const errorResponse: ApiErrorResponse = {
          code: data.code,
          message: data.message,
        }
        return new ApplicationError(errorResponse, axiosError.response.status)
      }

      if (data.message) {
        return new ApplicationError(
          {
            code: `http:${axiosError.response.status}`,
            message: data.message,
          },
          axiosError.response.status,
        )
      }
    }

    return new ApplicationError(
      {
        code: 'network:error',
        message: axiosError.message || 'Connection error',
      },
      axiosError.response?.status,
    )
  }

  const handleError = (err: unknown): ApplicationError => {
    let appError: ApplicationError

    if (err instanceof ApplicationError) {
      appError = err
    } else if (
      err &&
      typeof err === 'object' &&
      'isAxiosError' in err &&
      (err as AxiosError).isAxiosError
    ) {
      appError = parseAxiosError(err as AxiosError)
    } else if (err instanceof Error) {
      appError = new ApplicationError({
        code: 'unknown:error',
        message: err.message,
      })
    } else {
      appError = new ApplicationError({
        code: 'unknown:error',
        message: 'An unknown error occurred',
      })
    }

    error.value = appError
    isError.value = true

    if (isAuthError(appError) && onAuthError) {
      onAuthError()
    }

    if (onError) {
      onError(appError)
    }

    if (showToast) {
      showErrorToast(appError)
    }

    return appError
  }

  const showErrorToast = (appError: ApplicationError, customSummary?: string) => {
    const message = getErrorMessage(appError)

    toast.add({
      severity: 'error',
      summary: customSummary || toastSummary,
      detail: message,
      life: toastLife,
    })
  }

  const clearError = () => {
    error.value = null
    isError.value = false
  }

  const isErrorCode = (code: string): boolean => {
    return error.value?.is(code) ?? false
  }

  const isErrorDomain = (domain: string): boolean => {
    return error.value?.isDomain(domain) ?? false
  }

  return {
    error: error as Ref<ApplicationError | null>,
    isError,
    handleError,
    showErrorToast,
    clearError,
    parseAxiosError,
    isErrorCode,
    isErrorDomain,
    getErrorMessage,
    toast,
  }
}

export const useErrorToast = () => {
  const { handleError, showErrorToast, clearError } = useApiError()

  return {
    handleError,
    showErrorToast,
    clearError,
  }
}
