import { defineStore } from 'pinia'
import { useTelegramQueries } from '@/queries/telegram'
import type { ITelegramService } from '@/services/telegram/telegramService'

export const useTelegramStore = (telegramService: ITelegramService) =>
  defineStore('telegram', () => {
    const { registerWebhookMutation } = useTelegramQueries(telegramService)

    const registerWebhook = async (webhookUrl: string) => {
      return registerWebhookMutation.mutateAsync(webhookUrl)
    }

    return {
      registerWebhook,

      isRegisterWebhookPending: registerWebhookMutation.isPending,
      isRegisterWebhookError: registerWebhookMutation.isError,
      registerWebhookError: registerWebhookMutation.error,
    }
  })
