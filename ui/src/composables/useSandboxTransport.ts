import { inject } from 'vue'
import services from '@/services'
import type { ISandboxService } from '@/services/sandbox/sandboxService'

export const useSandboxTransport = () => {
  const injected = inject<{ sandboxService: ISandboxService }>('services', {
    sandboxService: services.sandboxService,
  })

  return {
    streamSandboxMessage: injected.sandboxService.streamSandboxMessage.bind(
      injected.sandboxService,
    ),
    approveToolRequest: injected.sandboxService.approveToolRequest.bind(
      injected.sandboxService,
    ),
  }
}
