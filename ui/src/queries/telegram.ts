import { useMutation } from '@tanstack/vue-query'
import type { ITelegramService } from '@/services/telegram/telegramService'

export const useTelegramQueries = (telegramService: ITelegramService) => {
  const registerWebhookMutation = useMutation({
    mutationFn: (webhookUrl: string) => telegramService.registerWebhook(webhookUrl),
  })

  return {
    registerWebhookMutation,
  }
}
