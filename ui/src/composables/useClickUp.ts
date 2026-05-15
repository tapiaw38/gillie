import { inject } from 'vue'
import { useMutation } from '@tanstack/vue-query'
import type { IClickUpService } from '@/services/clickup/clickupService'

export const useClickUp = () => {
  const services = inject<{ clickupService: IClickUpService }>('services')
  if (!services) throw new Error('Services not provided')

  const verifyConnectionMutation = useMutation({
    mutationFn: services.clickupService.getWorkspaces.bind(services.clickupService),
  })

  return {
    verifyConnection: verifyConnectionMutation.mutateAsync,
    workspaces: verifyConnectionMutation.data,
    isVerifyConnectionPending: verifyConnectionMutation.isPending,
    isVerifyConnectionError: verifyConnectionMutation.isError,
    verifyConnectionError: verifyConnectionMutation.error,
  }
}
