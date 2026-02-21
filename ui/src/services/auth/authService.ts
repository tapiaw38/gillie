import type { AxiosInstance } from 'axios'
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

export interface IAuthService {
  login(params: LoginParams): Promise<LoginResponse>
  meUser(): Promise<MeUserResponse>
  register(params: RegisterParams): Promise<RegisterResponse>
  changePassword(params: ChangePasswordParams): Promise<ChangePasswordResponse>
  setPassword(params: SetPasswordParams): Promise<SetPasswordResponse>
  requestResetPassword(params: RequestResetPasswordParams): Promise<RequestResetPasswordResponse>
  resetPassword(params: ResetPasswordParams): Promise<ResetPasswordResponse>
}

export class AuthService implements IAuthService {
  constructor(private readonly api: AxiosInstance) {
    this.api = api
  }

  async login({ email, password, ssoType, ssoCode }: LoginParams): Promise<LoginResponse> {
    const { data } = await this.api.post<LoginResponse>('/auth/login', {
      email,
      password,
      sso_type: ssoType,
      code: ssoCode,
    })
    return data
  }

  async meUser(): Promise<MeUserResponse> {
    const { data } = await this.api.get<MeUserResponse>('/user/me')
    return data
  }

  async register(params: RegisterParams): Promise<RegisterResponse> {
    const { data } = await this.api.post<RegisterResponse>('/auth/register', params)
    return data
  }

  async changePassword(params: ChangePasswordParams): Promise<ChangePasswordResponse> {
    const { data } = await this.api.put<ChangePasswordResponse>('/user/me/password', params)
    return data
  }

  async setPassword(params: SetPasswordParams): Promise<SetPasswordResponse> {
    const { data } = await this.api.post<SetPasswordResponse>('/user/me/password/set', params)
    return data
  }

  async requestResetPassword(params: RequestResetPasswordParams): Promise<RequestResetPasswordResponse> {
    const { data } = await this.api.post<RequestResetPasswordResponse>('/auth/request-reset-password', params)
    return data
  }

  async resetPassword(params: ResetPasswordParams): Promise<ResetPasswordResponse> {
    const { data } = await this.api.post<ResetPasswordResponse>('/auth/reset-password', params)
    return data
  }
}
