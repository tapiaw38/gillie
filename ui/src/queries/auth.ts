import { useMutation, useQuery } from '@tanstack/vue-query'
import type { IAuthService } from '@/services/auth/authService'
import type {
  LoginParams,
  LoginResponse,
  MeUserResponse,
  RegisterParams,
  RegisterResponse,
  ChangePasswordParams,
  ChangePasswordResponse,
  SetPasswordParams,
  SetPasswordResponse,
  RequestResetPasswordParams,
  RequestResetPasswordResponse,
  ResetPasswordParams,
  ResetPasswordResponse,
} from '@/types/auth'

export function useAuthQueries(authService: IAuthService) {
  const loginMutation = useMutation<LoginResponse, Error, LoginParams>({
    mutationFn: authService.login.bind(authService),
  })

  const meUserQuery = useQuery<MeUserResponse, Error>({
    queryKey: ['meUser'],
    queryFn: authService.meUser.bind(authService),
    enabled: false,
    retry: false,
  })

  const registerMutation = useMutation<RegisterResponse, Error, RegisterParams>({
    mutationFn: authService.register.bind(authService),
  })

  const changePasswordMutation = useMutation<ChangePasswordResponse, Error, ChangePasswordParams>({
    mutationFn: authService.changePassword.bind(authService),
  })

  const setPasswordMutation = useMutation<SetPasswordResponse, Error, SetPasswordParams>({
    mutationFn: authService.setPassword.bind(authService),
  })

  const requestResetPasswordMutation = useMutation<RequestResetPasswordResponse, Error, RequestResetPasswordParams>({
    mutationFn: authService.requestResetPassword.bind(authService),
  })

  const resetPasswordMutation = useMutation<ResetPasswordResponse, Error, ResetPasswordParams>({
    mutationFn: authService.resetPassword.bind(authService),
  })

  return {
    loginMutation,
    meUserQuery,
    registerMutation,
    changePasswordMutation,
    setPasswordMutation,
    requestResetPasswordMutation,
    resetPasswordMutation,
  }
}
