import { ref } from 'vue'
import { defineStore } from 'pinia'
import type { IAssistantService } from '@/services/assistant/assistantService'
import type { AssistantProfile } from '@/types/assistant.ts'

export const useAuthStore = (assistantService: IAssistantService) =>
  defineStore('auth', () => {
    const profile = ref<AssistantProfile | null>(null)
    const isFetchingProfile = ref(false)
    const fetchProfileError = ref<Error | null>(null)

    const fetchProfile = async () => {
      isFetchingProfile.value = true
      fetchProfileError.value = null
      try {
        const response = await assistantService.getAssistant()
        profile.value = response.data
      } catch (error) {
        fetchProfileError.value = error as Error
        console.error('Failed to fetch assistant profile:', error)
        throw error
      } finally {
        isFetchingProfile.value = false
      }
    }

    return {
      profile,
      isFetchingProfile,
      fetchProfileError,
      fetchProfile,
    }
  })
