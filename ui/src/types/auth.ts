export interface Role {
  id: string
  name: string
}

export interface User {
  id: string
  first_name: string
  last_name: string
  email: string
  phone_number: string | null
  picture: string | null
  address: string | null
  is_active: boolean
  verified_email: boolean
  token_version: number
  roles: Role[]
  auth_method: 'password' | 'google' | 'hybrid'
}

export interface LoginParams {
  email?: string
  password?: string
  ssoType?: string
  ssoCode?: string
}

export interface LoginResponse {
  token: string
  data: User
}

export interface MeUserResponse {
  data: User
}

export interface RegisterParams {
  first_name: string
  last_name: string
  email: string
  password: string
}

export interface RegisterResponse {
  data: User
}

export interface ChangePasswordParams {
  old_password: string
  new_password: string
}

export interface ChangePasswordResponse {
  message: string
}

export interface SetPasswordParams {
  new_password: string
}

export interface SetPasswordResponse {
  message: string
}

export interface RequestResetPasswordParams {
  email: string
}

export interface RequestResetPasswordResponse {
  data: {
    email: string
    message: string
  }
}

export interface ResetPasswordParams {
  token: string
  password: string
}

export interface ResetPasswordResponse {
  data: {
    message: string
  }
}
