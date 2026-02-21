import { inject } from 'vue'
import { storeToRefs } from 'pinia'
import { useAuthStore } from '@/stores/authStore'
import type { IAssistantService } from '@/services/assistant/assistantService'

export const useAuth = () => {
  const services = inject<{ assistantService: IAssistantService }>('services')
  if (!services) throw new Error('Services not provided')

  const store = useAuthStore(services.assistantService)
  const authStore = store()

  const { profile, isFetchingProfile, fetchProfileError } = storeToRefs(authStore)
  const { fetchProfile } = authStore

  return {
    profile,
    isFetchingProfile,
    fetchProfileError,
    fetchProfile,
  }
}
