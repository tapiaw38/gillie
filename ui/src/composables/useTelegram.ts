import { ref } from 'vue'
import services from '@/services'
import { ApplicationError, getErrorMessage } from '@/types/error'

export const useTelegram = () => {
  const isRegisteringWebhook = ref(false)
  const registerWebhookError = ref<string | null>(null)

  const registerWebhook = async (webhookUrl: string) => {
    isRegisteringWebhook.value = true
    registerWebhookError.value = null
    try {
      return await services.telegramService.registerWebhook(webhookUrl)
    } catch (err) {
      registerWebhookError.value =
        err instanceof ApplicationError ? getErrorMessage(err) : 'Error registering webhook'
      throw err
    } finally {
      isRegisteringWebhook.value = false
    }
  }

  return {
    isRegisteringWebhook,
    registerWebhookError,
    registerWebhook,
  }
}
