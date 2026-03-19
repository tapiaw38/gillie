import { inject, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { useAuthStore } from '@/stores/authStore'
import type { IAssistantService } from '@/services/assistant/assistantService'
import type { IAuthService } from '@/services/auth/authService'
import type { LoginParams, SetPasswordParams, User } from '@/types/auth'

export const useAuth = () => {
  const services = inject<{ assistantService: IAssistantService; authService: IAuthService }>(
    'services',
  )
  if (!services) throw new Error('Services not provided')

  const store = useAuthStore(services.assistantService)
  const authStore = store()

  const { profile, isFetchingProfile, fetchProfileError } = storeToRefs(authStore)
  const { fetchProfile } = authStore

  // ── Login ──────────────────────────────────────────────────────────────────
  const isLoginPending = ref(false)
  const isLoginSuccess = ref(false)
  const isLoginError = ref(false)
  const loginError = ref<unknown>(null)
  const user = ref<User | null>(null)

  const loginUser = async (params: LoginParams) => {
    isLoginPending.value = true
    isLoginSuccess.value = false
    isLoginError.value = false
    loginError.value = null
    try {
      const response = await services.authService.login(params)
      user.value = response.data
      isLoginSuccess.value = true
    } catch (error) {
      loginError.value = error
      isLoginError.value = true
      throw error
    } finally {
      isLoginPending.value = false
    }
  }

  // ── Me User ────────────────────────────────────────────────────────────────
  const meUser = async () => {
    const response = await services.authService.meUser()
    user.value = response.data
    return response
  }

  // ── Set Password ───────────────────────────────────────────────────────────
  const isSetPasswordPending = ref(false)
  const isSetPasswordSuccess = ref(false)
  const isSetPasswordError = ref(false)
  const setPasswordError = ref<unknown>(null)

  const setPassword = async (params: SetPasswordParams) => {
    isSetPasswordPending.value = true
    isSetPasswordSuccess.value = false
    isSetPasswordError.value = false
    setPasswordError.value = null
    try {
      const response = await services.authService.setPassword(params)
      isSetPasswordSuccess.value = true
      return response
    } catch (error) {
      setPasswordError.value = error
      isSetPasswordError.value = true
      throw error
    } finally {
      isSetPasswordPending.value = false
    }
  }

  return {
    // Profile (authStore)
    profile,
    isFetchingProfile,
    fetchProfileError,
    fetchProfile,

    // Login
    user,
    isLoginPending,
    isLoginSuccess,
    isLoginError,
    loginError,
    loginUser,
    meUser,

    // Set Password
    isSetPasswordPending,
    isSetPasswordSuccess,
    isSetPasswordError,
    setPasswordError,
    setPassword,
  }
}
