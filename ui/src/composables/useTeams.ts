import { inject } from 'vue'
import { useMutation } from '@tanstack/vue-query'
import type { ITeamsService } from '@/services/teams/teamsService'

export const useTeams = () => {
  const services = inject<{ teamsService: ITeamsService }>('services')
  if (!services) throw new Error('Services not provided')

  const verifyConnectionMutation = useMutation({
    mutationFn: services.teamsService.verifyConnection.bind(services.teamsService),
  })

  return {
    verifyConnection: verifyConnectionMutation.mutateAsync,
    verifyResult: verifyConnectionMutation.data,
    isVerifyConnectionPending: verifyConnectionMutation.isPending,
    isVerifyConnectionError: verifyConnectionMutation.isError,
    verifyConnectionError: verifyConnectionMutation.error,
  }
}
