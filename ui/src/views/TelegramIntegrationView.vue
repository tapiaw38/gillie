<script setup lang="ts">
import type { IntegrationParams, TelegramIntegrationConfig } from '@/types/assistant'
import { onMounted, reactive, computed, watch, ref } from 'vue'
import { useAssistant } from '@/composables/useAssistant'
import { useClipboard } from '@/composables/useClipboard'
import { useTelegram } from '@/composables/useTelegram'
import { useErrorToast } from '@/composables/useErrorToast'
import { useI18n } from 'vue-i18n'
import Toast from 'primevue/toast'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'
import Message from 'primevue/message'
import InputSwitch from 'primevue/inputswitch'

const {
  addIntegration,
  getAssistantProfile,
  assistantProfile,
  isAddIntegrationError,
  addIntegrationError,
  isGetAssistantProfileError,
  getAssistantProfileError,
} = useAssistant()

const { t } = useI18n()
const { copyText } = useClipboard()
const { registerWebhook: registerTelegramWebhook, isRegisterWebhookPending: isRegisteringWebhook } =
  useTelegram()

const errorWatchers = [
  {
    flag: isAddIntegrationError,
    summary: t('systemCommands.errorSaveConfig'),
    detail: addIntegrationError,
  },
  {
    flag: isGetAssistantProfileError,
    summary: t('systemCommands.errorLoadProfile'),
    detail: getAssistantProfileError,
  },
]

const { toast } = useErrorToast(errorWatchers)

const telegramIntegration = reactive<IntegrationParams>({
  name: 'telegram',
  type: 'integration',
  activated: false,
  config: {
    bot_token: '',
    secret_token: '',
  } as TelegramIntegrationConfig,
})

const validationErrors = reactive({
  bot_token: '',
})

const saveConfig = async () => {
  const config = telegramIntegration.config as TelegramIntegrationConfig

  validationErrors.bot_token = !config.bot_token ? t('integrations.telegram.botTokenHelp') : ''

  if (validationErrors.bot_token) {
    toast.add({
      severity: 'warn',
      summary: t('common.requiredFields'),
      detail: t('common.completeRequired'),
      life: 3000,
    })
    return
  }

  try {
    await addIntegration(telegramIntegration)
    await getAssistantProfile()
    toast.add({ severity: 'success', summary: t('integrations.saveConfig'), life: 3000 })
  } catch (error) {
    console.error('Error al guardar la configuración:', error)
  }
}

const updateIntegration = async () => {
  try {
    await addIntegration(telegramIntegration)
    await getAssistantProfile()
  } catch (error) {
    console.error('Error al actualizar integración:', error)
  }
}

watch(
  () => telegramIntegration.activated,
  async () => {
    await updateIntegration()
  },
)

const currentIntegration = computed(() =>
  assistantProfile.value?.integrations?.find((i) => i.name === 'telegram'),
)

const publicUrl = ref('')
const webhookStatus = ref<'idle' | 'success' | 'error'>('idle')
const webhookStatusMessage = ref('')

const API_BASE = (
  (import.meta.env.VITE_ASSISTANT_BASE_URL as string) || 'http://localhost:8000'
).replace(/\/$/, '')

const apiBase = computed(() => {
  if (publicUrl.value.trim()) return publicUrl.value.trim().replace(/\/$/, '')
  return API_BASE
})

const webhookUrl = computed(() => `${apiBase.value}/api/telegram/webhook`)

const registerWebhook = async () => {
  if (!publicUrl.value.trim()) {
    webhookStatus.value = 'error'
    webhookStatusMessage.value = t('integrations.telegram.enterPublicUrl')
    return
  }
  webhookStatus.value = 'idle'
  try {
    const result = await registerTelegramWebhook(webhookUrl.value)
    webhookStatus.value = 'success'
    webhookStatusMessage.value =
      result.message || `${t('integrations.telegram.webhookRegistered')}: ${webhookUrl.value}`
  } catch (e: unknown) {
    webhookStatus.value = 'error'
    webhookStatusMessage.value = e instanceof Error ? e.message : t('common.unknownError')
  }
}

const copyWebhookUrl = async () => {
  const copied = await copyText(webhookUrl.value)
  if (!copied) {
    toast.add({
      severity: 'error',
      summary: t('common.error'),
      detail: t('common.unknownError'),
      life: 3000,
    })
  }
}

onMounted(async () => {
  await getAssistantProfile()
  assistantProfile.value?.integrations?.forEach((integration) => {
    if (integration.name === 'telegram') {
      telegramIntegration.activated = integration.activated || false
      const config = telegramIntegration.config as TelegramIntegrationConfig
      const saved = integration.config as unknown as TelegramIntegrationConfig
      config.bot_token = saved.bot_token || ''
      config.secret_token = saved.secret_token || ''
    }
  })
})
</script>

<template>
  <div class="integration-container">
    <!-- Unified header row -->
    <div class="page-header">
      <div class="header-left">
        <div class="icon-wrapper tg-icon">
          <i class="pi pi-send"></i>
        </div>
        <div class="header-text">
          <h1 class="page-title">{{ t('integrations.telegram.title') }}</h1>
          <p class="page-subtitle">{{ t('integrations.telegram.subtitle') }}</p>
        </div>
      </div>
      <div class="header-toggle">
        <span class="toggle-status" :class="{ active: telegramIntegration.activated }">
          {{
            telegramIntegration.activated ? t('integrations.active') : t('integrations.inactive')
          }}
        </span>
        <InputSwitch v-model="telegramIntegration.activated" />
      </div>
    </div>

    <!-- Step 1 — Bot credentials -->
    <div class="panel" :class="{ 'panel-disabled': !telegramIntegration.activated }">
      <div class="panel-header">
        <span class="step-badge">1</span>
        <div>
          <p class="panel-title">{{ t('integrations.telegram.botCredentials') }}</p>
          <p class="panel-subtitle">{{ t('integrations.telegram.botCredentialsSubtitle') }}</p>
        </div>
      </div>

      <form class="panel-body" @submit.prevent="saveConfig">
        <div class="field-group">
          <label for="bot_token" class="field-label">
            <i class="pi pi-key field-icon"></i>
            Bot Token
            <span class="required">*</span>
          </label>
          <InputText
            id="bot_token"
            v-model="(telegramIntegration.config as TelegramIntegrationConfig).bot_token"
            placeholder="123456789:ABCDefghIJKlmnoPQRstUVwxyz"
            :disabled="!telegramIntegration.activated || isRegisteringWebhook"
            :invalid="!!validationErrors.bot_token"
            class="w-full"
            type="password"
          />
          <Message v-if="validationErrors.bot_token" severity="error" class="field-error">
            {{ validationErrors.bot_token }}
          </Message>
          <small class="field-help">{{ t('integrations.telegram.botTokenHelp') }}</small>
        </div>

        <div class="field-group">
          <label for="secret_token" class="field-label">
            <i class="pi pi-lock field-icon"></i>
            Secret Token
            <span class="optional">{{ t('integrations.telegram.optional') }}</span>
          </label>
          <InputText
            id="secret_token"
            v-model="(telegramIntegration.config as TelegramIntegrationConfig).secret_token"
            :placeholder="t('integrations.telegram.secretTokenPlaceholder')"
            :disabled="!telegramIntegration.activated || isRegisteringWebhook"
            class="w-full"
          />
          <small class="field-help">{{ t('integrations.telegram.secretTokenHelp') }}</small>
        </div>

        <div class="panel-footer">
          <div class="saved-state">
            <template v-if="currentIntegration">
              <span
                class="saved-dot"
                :class="{
                  configured: !!(currentIntegration.config as unknown as TelegramIntegrationConfig)
                    .bot_token,
                }"
              ></span>
              <span class="saved-label">
                {{
                  (currentIntegration.config as unknown as TelegramIntegrationConfig).bot_token
                    ? t('integrations.telegram.tokenConfigured')
                    : t('integrations.telegram.noToken')
                }}
              </span>
            </template>
          </div>
          <Button
            type="submit"
            :label="t('common.save')"
            icon="pi pi-save"
            severity="primary"
            :disabled="!telegramIntegration.activated"
          />
        </div>
      </form>
    </div>

    <!-- Step 2 — Webhook setup -->
    <div class="panel">
      <div class="panel-header">
        <span class="step-badge">2</span>
        <div>
          <p class="panel-title">{{ t('integrations.telegram.registerWebhook') }}</p>
          <p class="panel-subtitle">{{ t('integrations.telegram.registerWebhookSubtitle') }}</p>
        </div>
      </div>

      <div class="panel-body">
        <div class="field-group">
          <label class="field-label">
            <i class="pi pi-globe field-icon"></i>
            {{ t('integrations.telegram.publicUrl') }}
            <span class="optional"
              >ngrok / cloudflare / {{ t('integrations.telegram.publicUrl') }}</span
            >
          </label>
          <InputText
            v-model="publicUrl"
            :placeholder="t('integrations.telegram.publicUrlPlaceholder')"
            class="w-full"
          />
          <small class="field-help">{{ t('integrations.telegram.publicUrlHelp') }}</small>
        </div>

        <div class="webhook-row">
          <div class="field-group webhook-field">
            <label class="field-label">
              <i class="pi pi-link field-icon"></i>
              {{ t('integrations.webhookUrl') }}
            </label>
            <div class="webhook-url-wrap">
              <code class="webhook-url-text">{{ webhookUrl }}</code>
              <button
                class="copy-btn"
                type="button"
                :title="t('integrations.copyUrl')"
                @click="copyWebhookUrl"
              >
                <i class="pi pi-copy"></i>
              </button>
            </div>
          </div>
        </div>

        <div class="panel-footer">
          <div class="webhook-feedback">
            <Message v-if="webhookStatus === 'success'" severity="success" :closable="false">
              {{ webhookStatusMessage }}
            </Message>
            <Message v-if="webhookStatus === 'error'" severity="error" :closable="false">
              {{ webhookStatusMessage }}
            </Message>
          </div>
          <Button
            :label="t('integrations.telegram.registerBtn')"
            icon="pi pi-check"
            severity="primary"
            :loading="isRegisteringWebhook"
            :disabled="!currentIntegration?.activated"
            @click="registerWebhook"
          />
        </div>
      </div>
    </div>

    <!-- Step 3 — Setup guide -->
    <div class="panel">
      <div class="panel-header">
        <span class="step-badge">3</span>
        <div>
          <p class="panel-title">{{ t('integrations.setupGuide') }}</p>
          <p class="panel-subtitle">{{ t('integrations.telegram.registerWebhookSubtitle') }}</p>
        </div>
      </div>

      <ol class="steps-list">
        <li class="step-item">
          <span class="step-num">1</span>
          <span>Abrí Telegram y hablá con <strong>@BotFather</strong></span>
        </li>
        <li class="step-item">
          <span class="step-num">2</span>
          <span>Enviá <code>/newbot</code> y seguí las instrucciones para crear el bot</span>
        </li>
        <li class="step-item">
          <span class="step-num">3</span>
          <span>Copiá el <strong>Bot Token</strong> que te da BotFather y guardalo arriba</span>
        </li>
        <li class="step-item">
          <span class="step-num">4</span>
          <span>Activá la integración con el toggle del encabezado</span>
        </li>
        <li class="step-item">
          <span class="step-num">5</span>
          <span>Si estás en local, iniciá un túnel: <code>ngrok http 8000</code></span>
        </li>
        <li class="step-item">
          <span class="step-num">6</span>
          <span
            >Pegá la URL de ngrok en el paso 2 y hacé clic en
            <strong>Registrar en Telegram</strong></span
          >
        </li>
      </ol>
    </div>

    <Toast position="top-right" />
  </div>
</template>

<style scoped>
/* ── View-specific styles ────────────────────────────────── */
.tg-icon {
  color: #0088cc;
}

.field-icon {
  color: var(--color-primary);
  font-size: 0.875rem;
}

.field-help {
  font-size: 0.8rem;
  color: var(--do-text-muted);
  font-style: italic;
}

.field-error {
  margin-top: 0.25rem;
}

.saved-state {
  display: flex;
  align-items: center;
  gap: 0.45rem;
}

.saved-dot {
  width: 0.55rem;
  height: 0.55rem;
  border-radius: 50%;
  background: var(--color-danger);
  transition: background 0.25s;
}

.saved-dot.configured {
  background: var(--color-success);
}

.saved-label {
  font-size: 0.8rem;
  color: var(--do-text-muted);
}

.webhook-row {
  margin-top: 0.25rem;
}

.webhook-field {
  width: 100%;
}

.webhook-url-wrap {
  display: flex;
  align-items: center;
  gap: 0;
  border: 1px solid var(--do-border-light);
  border-radius: 0.75rem;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.04);
}

.webhook-url-text {
  flex: 1;
  padding: 0.55rem 0.875rem;
  font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
  font-size: 0.8rem;
  color: #3fa7d6;
  word-break: break-all;
  background: transparent;
  border: none;
}

.copy-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 0.875rem;
  height: 100%;
  min-height: 2.2rem;
  background: rgba(255, 255, 255, 0.05);
  border: none;
  border-left: 1px solid var(--do-border-light);
  color: var(--do-text-muted);
  cursor: pointer;
  transition:
    color 0.2s,
    background 0.2s;
  font-size: 0.875rem;
}

.copy-btn:hover {
  color: var(--color-primary);
  background: rgba(255, 255, 255, 0.08);
}

.webhook-feedback {
  flex: 1;
  min-width: 0;
}

.steps-list {
  list-style: none;
  margin: 0;
  padding: 1rem 1.25rem 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}

.step-item {
  display: flex;
  align-items: baseline;
  gap: 0.75rem;
  font-size: 0.875rem;
  color: var(--do-text-muted);
}

.step-num {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.4rem;
  height: 1.4rem;
  border-radius: 50%;
  border: 1px solid var(--do-border-light);
  font-size: 0.7rem;
  font-weight: 700;
  color: var(--do-text-muted);
  flex-shrink: 0;
}

.step-item code {
  background: rgba(255, 255, 255, 0.07);
  padding: 0.1rem 0.35rem;
  border-radius: 0.3rem;
  font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
  font-size: 0.78rem;
  color: var(--do-text);
}

</style>
