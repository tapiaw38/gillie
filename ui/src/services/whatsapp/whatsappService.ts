import type { AxiosInstance } from 'axios'

export interface WhatsAppDevice {
  id: string
  user_id: string
  phone_number: string
  device_name: string
  status: 'disconnected' | 'connecting' | 'connected' | 'authenticated'
  qr_code?: string
  pair_code?: string
  last_connected_at?: string
  created_at: string
  updated_at: string
}

export interface CreateDeviceRequest {
  phone_number: string
  device_name: string
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
