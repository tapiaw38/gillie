import axios from 'axios'
import type { AxiosInstance, AxiosError } from 'axios'
import { ApplicationError, type ApiErrorResponse } from '@/types/error'

type ServerParams = {
  timeout?: number
  baseURL?: string
}

const parseErrorResponse = (error: AxiosError): ApplicationError => {
  if (error.response?.data) {
    const data = error.response.data as {
      code?: string
      message?: string
      [key: string]: unknown
    }

    if (data.code && data.message) {
      const errorResponse: ApiErrorResponse = {
        code: data.code,
        message: data.message,
      }
      return new ApplicationError(errorResponse, error.response.status)
    }

    if (data.message) {
      return new ApplicationError(
        {
          code: `http:${error.response.status}`,
          message: data.message,
        },
        error.response.status,
      )
    }
  }

  return new ApplicationError(
    {
      code: 'network:error',
      message: error.message || 'Error de conexión con el servidor',
    },
    error.response?.status,
  )
}

export const server = ({ timeout, baseURL }: ServerParams): AxiosInstance => {
  const instance = axios.create({
    timeout: timeout || 15000,
    baseURL: baseURL || import.meta.env.VITE_ASSISTANT_BASE_URL,
  })

  instance.interceptors.request.use(
    (config) => {
      const apiKey = import.meta.env.VITE_ASSISTANT_API_KEY
      if (apiKey) {
        config.headers['x-api-key'] = apiKey
      }
      return config
    },
    (error) => {
      return Promise.reject(error)
    },
  )

  instance.interceptors.response.use(
    (response) => response,
    (error: AxiosError) => {
      const appError = parseErrorResponse(error)

      if (import.meta.env.DEV) {
        console.error('[API Error]', {
          code: appError.code,
          message: appError.message,
          statusCode: appError.statusCode,
          url: error.config?.url,
          method: error.config?.method,
        })
      }

      return Promise.reject(appError)
    },
  )

  return instance
}
