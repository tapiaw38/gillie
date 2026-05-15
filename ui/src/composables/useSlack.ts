import { inject } from 'vue'
import { useMutation } from '@tanstack/vue-query'
import type { ISlackService } from '@/services/slack/slackService'

export const useSlack = () => {
  const services = inject<{ slackService: ISlackService }>('services')
  if (!services) throw new Error('Services not provided')

  const verifyConnectionMutation = useMutation({
    mutationFn: services.slackService.authTest.bind(services.slackService),
  })

  return {
    verifyConnection: verifyConnectionMutation.mutateAsync,
    authData: verifyConnectionMutation.data,
    isVerifyConnectionPending: verifyConnectionMutation.isPending,
    isVerifyConnectionError: verifyConnectionMutation.isError,
    verifyConnectionError: verifyConnectionMutation.error,
  }
}
