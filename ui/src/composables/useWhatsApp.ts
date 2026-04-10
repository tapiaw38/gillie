import { inject } from 'vue'
import { storeToRefs } from 'pinia'
import { useWhatsAppStore } from '@/stores/whatsappStore'
import type { IWhatsAppService } from '@/services/whatsapp/whatsappService'

export const useWhatsApp = () => {
  const services = inject<{ whatsappService: IWhatsAppService }>('services')
  if (!services) throw new Error('Services not provided')

  const store = useWhatsAppStore(services.whatsappService)
  const whatsappStore = store()

  const {
    devices,
    isListDevicesPending,
    isListDevicesError,
    listDevicesError,
    isCreateDevicePending,
    isCreateDeviceError,
    createDeviceError,
    isConnectDevicePending,
    isConnectDeviceError,
    connectDeviceError,
    isAuthenticateDevicePending,
    isAuthenticateDeviceError,
    authenticateDeviceError,
    isDisconnectDevicePending,
    isDisconnectDeviceError,
    isDeleteDevicePending,
    isDeleteDeviceError,
    isSendMessagePending,
    isSendMessageError,
    sendMessageError,
  } = storeToRefs(whatsappStore)

  const {
    listDevices,
    createDevice,
    connectDevice,
    authenticateDevice,
    disconnectDevice,
    deleteDevice,
    sendMessage,
  } = whatsappStore

  return {
    devices,
    isListDevicesPending,
    isListDevicesError,
    listDevicesError,
    isCreateDevicePending,
    isCreateDeviceError,
    createDeviceError,
    isConnectDevicePending,
    isConnectDeviceError,
    connectDeviceError,
    isAuthenticateDevicePending,
    isAuthenticateDeviceError,
    authenticateDeviceError,
    isDisconnectDevicePending,
    isDisconnectDeviceError,
    isDeleteDevicePending,
    isDeleteDeviceError,
    isSendMessagePending,
    isSendMessageError,
    sendMessageError,
    listDevices,
    createDevice,
    connectDevice,
    authenticateDevice,
    disconnectDevice,
    deleteDevice,
    sendMessage,
    reset: whatsappStore.$reset,
  }
}
