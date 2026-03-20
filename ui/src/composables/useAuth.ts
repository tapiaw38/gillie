import { inject, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { useAuthStore } from '@/stores/authStore'
import type { IAssistantService } from '@/services/assistant/assistantService'
import type { IAuthService } from '@/services/auth/authService'
import type {
  LoginParams,
  SetPasswordParams,
  RegisterParams,
  ChangePasswordParams,
  RequestResetPasswordParams,
  ResetPasswordParams,
  User,
} from '@/types/auth'
import type { ApplicationError } from '@/types/error'

type AuthError = string | Error | ApplicationError | null

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
  const loginError = ref<AuthError>(null)
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
      loginError.value = error instanceof Error ? error : String(error)
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

  // ── Register ───────────────────────────────────────────────────────────────
  const isRegisterPending = ref(false)
  const isRegisterSuccess = ref(false)
  const isRegisterError = ref(false)
  const registerError = ref<AuthError>(null)

  const registerUser = async (params: RegisterParams) => {
    isRegisterPending.value = true
    isRegisterSuccess.value = false
    isRegisterError.value = false
    registerError.value = null
    try {
      const response = await services.authService.register(params)
      isRegisterSuccess.value = true
      return response
    } catch (error) {
      registerError.value = error instanceof Error ? error : String(error)
      isRegisterError.value = true
      throw error
    } finally {
      isRegisterPending.value = false
    }
  }

  // ── Change Password ────────────────────────────────────────────────────────
  const isChangePasswordPending = ref(false)
  const isChangePasswordSuccess = ref(false)
  const isChangePasswordError = ref(false)
  const changePasswordError = ref<AuthError>(null)

  const changePassword = async (params: ChangePasswordParams) => {
    isChangePasswordPending.value = true
    isChangePasswordSuccess.value = false
    isChangePasswordError.value = false
    changePasswordError.value = null
    try {
      const response = await services.authService.changePassword(params)
      isChangePasswordSuccess.value = true
      return response
    } catch (error) {
      changePasswordError.value = error instanceof Error ? error : String(error)
      isChangePasswordError.value = true
      throw error
    } finally {
      isChangePasswordPending.value = false
    }
  }

  // ── Set Password ───────────────────────────────────────────────────────────
  const isSetPasswordPending = ref(false)
  const isSetPasswordSuccess = ref(false)
  const isSetPasswordError = ref(false)
  const setPasswordError = ref<AuthError>(null)

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
      setPasswordError.value = error instanceof Error ? error : String(error)
      isSetPasswordError.value = true
      throw error
    } finally {
      isSetPasswordPending.value = false
    }
  }

  // ── Request Reset Password ─────────────────────────────────────────────────
  const isRequestResetPasswordPending = ref(false)
  const isRequestResetPasswordSuccess = ref(false)
  const isRequestResetPasswordError = ref(false)
  const requestResetPasswordError = ref<AuthError>(null)

  const requestResetPassword = async (params: RequestResetPasswordParams) => {
    isRequestResetPasswordPending.value = true
    isRequestResetPasswordSuccess.value = false
    isRequestResetPasswordError.value = false
    requestResetPasswordError.value = null
    try {
      const response = await services.authService.requestResetPassword(params)
      isRequestResetPasswordSuccess.value = true
      return response
    } catch (error) {
      requestResetPasswordError.value = error instanceof Error ? error : String(error)
      isRequestResetPasswordError.value = true
      throw error
    } finally {
      isRequestResetPasswordPending.value = false
    }
  }

  // ── Reset Password ─────────────────────────────────────────────────────────
  const isResetPasswordPending = ref(false)
  const isResetPasswordSuccess = ref(false)
  const isResetPasswordError = ref(false)
  const resetPasswordError = ref<AuthError>(null)

  const resetPassword = async (params: ResetPasswordParams) => {
    isResetPasswordPending.value = true
    isResetPasswordSuccess.value = false
    isResetPasswordError.value = false
    resetPasswordError.value = null
    try {
      const response = await services.authService.resetPassword(params)
      isResetPasswordSuccess.value = true
      return response
    } catch (error) {
      resetPasswordError.value = error instanceof Error ? error : String(error)
      isResetPasswordError.value = true
      throw error
    } finally {
      isResetPasswordPending.value = false
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

    // Register
    isRegisterPending,
    isRegisterSuccess,
    isRegisterError,
    registerError,
    registerUser,

    // Change Password
    isChangePasswordPending,
    isChangePasswordSuccess,
    isChangePasswordError,
    changePasswordError,
    changePassword,

    // Set Password
    isSetPasswordPending,
    isSetPasswordSuccess,
    isSetPasswordError,
    setPasswordError,
    setPassword,

    // Request Reset Password
    isRequestResetPasswordPending,
    isRequestResetPasswordSuccess,
    isRequestResetPasswordError,
    requestResetPasswordError,
    requestResetPassword,

    // Reset Password
    isResetPasswordPending,
    isResetPasswordSuccess,
    isResetPasswordError,
    resetPasswordError,
    resetPassword,
  }
}
