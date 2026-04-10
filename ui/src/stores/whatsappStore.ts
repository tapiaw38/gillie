import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useWhatsAppQueries } from '@/queries/whatsapp'
import type { IWhatsAppService } from '@/services/whatsapp/whatsappService'
import type {
  WhatsAppDevice,
  CreateDeviceRequest,
  AuthenticateDeviceRequest,
  SendMessageRequest,
} from '@/services/whatsapp/whatsappService'

export const useWhatsAppStore = (whatsappService: IWhatsAppService) =>
  defineStore('whatsapp', () => {
    const devices = ref<WhatsAppDevice[]>([])

    const {
      listDevicesQuery,
      createDeviceMutation,
      connectDeviceMutation,
      authenticateDeviceMutation,
      disconnectDeviceMutation,
      deleteDeviceMutation,
      sendMessageMutation,
    } = useWhatsAppQueries(whatsappService)

    const listDevices = async () => {
      const { data } = await listDevicesQuery.refetch()
      devices.value = data ?? []
      return data ?? []
    }

    const createDevice = async (request: CreateDeviceRequest) => {
      const device = await createDeviceMutation.mutateAsync(request)
      devices.value.push(device)
      return device
    }

    const connectDevice = async (deviceId: string, method: 'qr' | 'pair' = 'qr') => {
      return connectDeviceMutation.mutateAsync({ deviceId, method })
    }

    const authenticateDevice = async (
      deviceId: string,
      request: AuthenticateDeviceRequest,
    ) => {
      const device = await authenticateDeviceMutation.mutateAsync({ deviceId, request })
      const index = devices.value.findIndex((d) => d.id === deviceId)
      if (index !== -1) devices.value[index] = device
      return device
    }

    const disconnectDevice = async (deviceId: string) => {
      await disconnectDeviceMutation.mutateAsync(deviceId)
    }

    const deleteDevice = async (deviceId: string) => {
      await deleteDeviceMutation.mutateAsync(deviceId)
      devices.value = devices.value.filter((d) => d.id !== deviceId)
    }

    const sendMessage = async (request: SendMessageRequest) => {
      await sendMessageMutation.mutateAsync(request)
    }

    return {
      devices,

      listDevices,
      createDevice,
      connectDevice,
      authenticateDevice,
      disconnectDevice,
      deleteDevice,
      sendMessage,

      isListDevicesPending: listDevicesQuery.isPending,
      isListDevicesError: listDevicesQuery.isError,
      listDevicesError: listDevicesQuery.error,

      isCreateDevicePending: createDeviceMutation.isPending,
      isCreateDeviceError: createDeviceMutation.isError,
      createDeviceError: createDeviceMutation.error,

      isConnectDevicePending: connectDeviceMutation.isPending,
      isConnectDeviceError: connectDeviceMutation.isError,
      connectDeviceError: connectDeviceMutation.error,

      isAuthenticateDevicePending: authenticateDeviceMutation.isPending,
      isAuthenticateDeviceError: authenticateDeviceMutation.isError,
      authenticateDeviceError: authenticateDeviceMutation.error,

      isDisconnectDevicePending: disconnectDeviceMutation.isPending,
      isDisconnectDeviceError: disconnectDeviceMutation.isError,

      isDeleteDevicePending: deleteDeviceMutation.isPending,
      isDeleteDeviceError: deleteDeviceMutation.isError,

      isSendMessagePending: sendMessageMutation.isPending,
      isSendMessageError: sendMessageMutation.isError,
      sendMessageError: sendMessageMutation.error,
    }
  })
