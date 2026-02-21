import { watch } from 'vue'
import { useToast } from 'primevue/usetoast'
import type { Ref } from 'vue'
import { ApplicationError, getErrorMessage } from '@/types/error'

interface ErrorWatcher {
  flag: Ref<boolean>
  summary: string
  detail: Ref<string | Error | ApplicationError | null>
}

export const useErrorToast = (errorWatchers: ErrorWatcher[]) => {
  const toast = useToast()

  errorWatchers.forEach(({ flag, summary, detail }) => {
    watch(flag, (value) => {
      if (value) {
        let errorMessage = 'Error desconocido'

        if (detail.value) {
          if (detail.value instanceof ApplicationError) {
            errorMessage = getErrorMessage(detail.value)
          } else if (typeof detail.value === 'string') {
            errorMessage = detail.value
          } else if (detail.value instanceof Error) {
            errorMessage = detail.value.message || 'Error desconocido'
          }
        }

        toast.add({
          severity: 'error',
          summary,
          detail: errorMessage,
          life: 3000,
        })
      }
    })
  })

  return { toast }
}
