import { inject } from 'vue'
import services from '@/services'
import type {
  WhatsAppDevice,
  CreateDeviceRequest,
  SendMessageRequest,
  AuthenticateDeviceRequest
} from '@/services/whatsapp'

export function useWhatsApp() {
  const whatsappService = inject('services', services).whatsappService

  const listDevices = async (): Promise<WhatsAppDevice[]> => {
    return await whatsappService.listDevices()
  }

  const getDevice = async (deviceId: string): Promise<WhatsAppDevice> => {
    return await whatsappService.getDevice(deviceId)
  }

  const createDevice = async (request: CreateDeviceRequest): Promise<WhatsAppDevice> => {
    return await whatsappService.createDevice(request)
  }

  const connectDevice = async (deviceId: string, method: 'qr' | 'pair' = 'qr') => {
    return await whatsappService.connectDevice(deviceId, method)
  }

  const authenticateDevice = async (
    deviceId: string,
    request: AuthenticateDeviceRequest
  ): Promise<WhatsAppDevice> => {
    return await whatsappService.authenticateDevice(deviceId, request)
  }

  const disconnectDevice = async (deviceId: string): Promise<void> => {
    return await whatsappService.disconnectDevice(deviceId)
  }

  const deleteDevice = async (deviceId: string): Promise<void> => {
    return await whatsappService.deleteDevice(deviceId)
  }

  const sendMessage = async (request: SendMessageRequest): Promise<void> => {
    return await whatsappService.sendMessage(request)
  }

  return {
    listDevices,
    getDevice,
    createDevice,
    connectDevice,
    authenticateDevice,
    disconnectDevice,
    deleteDevice,
    sendMessage
  }
}
