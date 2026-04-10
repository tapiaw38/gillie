import { useQuery, useMutation } from '@tanstack/vue-query'
import type { IWhatsAppService } from '@/services/whatsapp/whatsappService'
import type {
  CreateDeviceRequest,
  AuthenticateDeviceRequest,
  SendMessageRequest,
} from '@/services/whatsapp/whatsappService'

export const useWhatsAppQueries = (whatsappService: IWhatsAppService) => {
  const listDevicesQuery = useQuery({
    queryKey: ['whatsappDevices'],
    queryFn: whatsappService.listDevices.bind(whatsappService),
  })

  const createDeviceMutation = useMutation({
    mutationFn: (request: CreateDeviceRequest) => whatsappService.createDevice(request),
  })

  const connectDeviceMutation = useMutation({
    mutationFn: ({ deviceId, method }: { deviceId: string; method: 'qr' | 'pair' }) =>
      whatsappService.connectDevice(deviceId, method),
  })

  const authenticateDeviceMutation = useMutation({
    mutationFn: ({
      deviceId,
      request,
    }: {
      deviceId: string
      request: AuthenticateDeviceRequest
    }) => whatsappService.authenticateDevice(deviceId, request),
  })

  const disconnectDeviceMutation = useMutation({
    mutationFn: (deviceId: string) => whatsappService.disconnectDevice(deviceId),
  })

  const deleteDeviceMutation = useMutation({
    mutationFn: (deviceId: string) => whatsappService.deleteDevice(deviceId),
  })

  const sendMessageMutation = useMutation({
    mutationFn: (request: SendMessageRequest) => whatsappService.sendMessage(request),
  })

  return {
    listDevicesQuery,
    createDeviceMutation,
    connectDeviceMutation,
    authenticateDeviceMutation,
    disconnectDeviceMutation,
    deleteDeviceMutation,
    sendMessageMutation,
  }
}
