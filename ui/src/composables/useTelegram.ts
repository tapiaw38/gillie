import { inject } from 'vue'
import { storeToRefs } from 'pinia'
import { useTelegramStore } from '@/stores/telegramStore'
import type { ITelegramService } from '@/services/telegram/telegramService'

export const useTelegram = () => {
  const services = inject<{ telegramService: ITelegramService }>('services')
  if (!services) throw new Error('Services not provided')

  const store = useTelegramStore(services.telegramService)
  const telegramStore = store()

  const { isRegisterWebhookPending, isRegisterWebhookError, registerWebhookError } =
    storeToRefs(telegramStore)

  const { registerWebhook } = telegramStore

  return {
    isRegisterWebhookPending,
    isRegisterWebhookError,
    registerWebhookError,
    registerWebhook,
    reset: telegramStore.$reset,
  }
}
