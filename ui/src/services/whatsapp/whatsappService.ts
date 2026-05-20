import type { AxiosInstance } from 'axios'
import { ApplicationError } from '@/types/error'

export interface WhatsAppDevice {
  id: string
  user_id: string
  phone_number: string
  device_name: string
  device_policies: DevicePolicies
  status: 'disconnected' | 'connecting' | 'connected' | 'authenticated'
  qr_code?: string
  pair_code?: string
  last_connected_at?: string
  created_at: string
  updated_at: string
}

export interface DevicePolicies {
  allowed_numbers: string[]
  blocked_numbers: string[]
  incoming_filter_mode: 'off' | 'whitelist' | 'blacklist' | 'both'
  outgoing_filter_mode: 'off' | 'whitelist' | 'blacklist' | 'both'
}

export interface CreateDeviceRequest {
  phone_number: string
  device_name: string
  device_policies: DevicePolicies
}

export interface UpdateDevicePoliciesRequest {
  device_policies: DevicePolicies
}

export interface ConnectDeviceResponse {
  data: {
    id: string
    qr_code?: string
    pair_code?: string
    status: string
  }
}

export interface AuthenticateDeviceRequest {
  auth_method: 'qr' | 'pair'
  pair_code?: string
}

export interface SendMessageRequest {
  device_id: string
  recipient_phone: string
  content: string
}

export interface IWhatsAppService {
  listDevices(): Promise<WhatsAppDevice[]>
  getDevice(deviceId: string): Promise<WhatsAppDevice>
  createDevice(request: CreateDeviceRequest): Promise<WhatsAppDevice>
  updateDevicePolicies(
    deviceId: string,
    request: UpdateDevicePoliciesRequest
  ): Promise<WhatsAppDevice>
  connectDevice(deviceId: string, method: 'qr' | 'pair'): Promise<ConnectDeviceResponse>
  authenticateDevice(deviceId: string, request: AuthenticateDeviceRequest): Promise<WhatsAppDevice>
  disconnectDevice(deviceId: string): Promise<void>
  deleteDevice(deviceId: string): Promise<void>
  sendMessage(request: SendMessageRequest): Promise<void>
}

export class WhatsAppService implements IWhatsAppService {
  constructor(private readonly api: AxiosInstance) {}

  async listDevices(): Promise<WhatsAppDevice[]> {
    const { data } = await this.api.get<WhatsAppDevice[]>('/device')
    return data
  }

  async getDevice(deviceId: string): Promise<WhatsAppDevice> {
    const { data } = await this.api.get<WhatsAppDevice>(`/device/${deviceId}`)
    return data
  }

  async createDevice(request: CreateDeviceRequest): Promise<WhatsAppDevice> {
    const { data } = await this.api.post<WhatsAppDevice>(
      '/device/register',
      request
    )
    return data
  }

  async updateDevicePolicies(
    deviceId: string,
    request: UpdateDevicePoliciesRequest
  ): Promise<WhatsAppDevice> {
    try {
      const { data } = await this.api.patch<WhatsAppDevice>(`/device/${deviceId}/policies`, request)
      return data
    } catch (error) {
      if (error instanceof ApplicationError && (error.statusCode === 404 || error.statusCode === 405)) {
        const { data } = await this.api.post<WhatsAppDevice>(`/device/${deviceId}/policies`, request)
        return data
      }
      throw error
    }
  }

  async connectDevice(
    deviceId: string,
    method: 'qr' | 'pair' = 'qr'
  ): Promise<ConnectDeviceResponse> {
    const { data } = await this.api.post<ConnectDeviceResponse>(
      `/device/${deviceId}/connect`,
      { method }
    )
    return data
  }

  async authenticateDevice(
    deviceId: string,
    request: AuthenticateDeviceRequest
  ): Promise<WhatsAppDevice> {
    const { data } = await this.api.post<WhatsAppDevice>(`/device/${deviceId}/authenticate`, request)
    return data
  }

  async disconnectDevice(deviceId: string): Promise<void> {
    await this.api.post(`/device/${deviceId}/disconnect`)
  }

  async deleteDevice(deviceId: string): Promise<void> {
    await this.api.delete(`/device/${deviceId}`)
  }

  async sendMessage(request: SendMessageRequest): Promise<void> {
    await this.api.post('/message/send', request)
  }
}
