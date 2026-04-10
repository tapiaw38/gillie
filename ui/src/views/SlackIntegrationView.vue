<script setup lang="ts">
import type { IntegrationParams, SlackIntegrationConfig } from '@/types/assistant'
import { onMounted, reactive, computed, watch } from 'vue'
import { useAssistant } from '@/composables/useAssistant'
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

const slackIntegration = reactive<IntegrationParams>({
  name: 'slack',
  type: 'integration',
  activated: false,
  config: {
    bot_token: '',
    signing_secret: '',
  } as SlackIntegrationConfig,
})

const validationErrors = reactive({
  bot_token: '',
})

const saveConfig = async () => {
  const config = slackIntegration.config as SlackIntegrationConfig

  validationErrors.bot_token = !config.bot_token ? t('integrations.slack.botTokenHelp') : ''

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
    await addIntegration(slackIntegration)
    await getAssistantProfile()
    toast.add({
      severity: 'success',
      summary: t('integrations.slack.credentialsSaved'),
      life: 3000,
    })
  } catch (error) {
    console.error('Error al guardar la configuración:', error)
  }
}

const updateIntegration = async () => {
  try {
    await addIntegration(slackIntegration)
    await getAssistantProfile()
  } catch (error) {
    console.error('Error al actualizar integración:', error)
  }
}

watch(
  () => slackIntegration.activated,
  async () => {
    await updateIntegration()
  },
)

const currentIntegration = computed(() =>
  assistantProfile.value?.integrations?.find((i) => i.name === 'slack'),
)

const API_BASE = (
  (import.meta.env.VITE_ASSISTANT_BASE_URL as string) || 'http://localhost:8000'
).replace(/\/$/, '')

const webhookUrl = computed(() => `${API_BASE}/api/slack/events`)

const copyWebhookUrl = async () => {
  try {
    await navigator.clipboard.writeText(webhookUrl.value)
    toast.add({
      severity: 'success',
      summary: t('integrations.copyUrl'),
      life: 2000,
    })
  } catch (error) {
    console.error('Error al copiar webhook URL:', error)
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
    if (integration.name === 'slack') {
      slackIntegration.activated = integration.activated || false
      const config = slackIntegration.config as SlackIntegrationConfig
      const saved = integration.config as unknown as SlackIntegrationConfig
      config.bot_token = saved.bot_token || ''
      config.signing_secret = saved.signing_secret || ''
    }
  })
})
</script>

<template>
  <div class="integration-container">
    <!-- Unified header row -->
    <div class="page-header">
      <div class="header-left">
        <div class="icon-wrapper slack-icon">
          <i class="pi pi-slack"></i>
        </div>
        <div class="header-text">
          <h1 class="page-title">{{ t('integrations.slack.title') }}</h1>
          <p class="page-subtitle">{{ t('integrations.slack.subtitle') }}</p>
        </div>
      </div>
      <div class="header-toggle">
        <span class="toggle-status" :class="{ active: slackIntegration.activated }">
          {{ slackIntegration.activated ? t('integrations.active') : t('integrations.inactive') }}
        </span>
        <InputSwitch v-model="slackIntegration.activated" />
      </div>
    </div>

    <!-- Step 1 — Credentials -->
    <div class="panel" :class="{ 'panel-disabled': !slackIntegration.activated }">
      <div class="panel-header">
        <span class="step-badge">1</span>
        <div>
          <p class="panel-title">{{ t('integrations.slack.credentialsTitle') }}</p>
          <p class="panel-subtitle">{{ t('integrations.slack.credentialsSubtitle') }}</p>
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
            v-model="(slackIntegration.config as SlackIntegrationConfig).bot_token"
            placeholder="xoxb-xxxxxxxxxxxx-xxxxxxxxxxxx-xxxxxxxxxxxxxxxxxxxxxxxx"
            :disabled="!slackIntegration.activated"
            :invalid="!!validationErrors.bot_token"
            class="w-full"
            type="password"
          />
          <Message v-if="validationErrors.bot_token" severity="error" class="field-error">
            {{ validationErrors.bot_token }}
          </Message>
          <small class="field-help">{{ t('integrations.slack.botTokenHelp') }}</small>
        </div>

        <div class="field-group">
          <label for="signing_secret" class="field-label">
            <i class="pi pi-lock field-icon"></i>
            Signing Secret
          </label>
          <InputText
            id="signing_secret"
            v-model="(slackIntegration.config as SlackIntegrationConfig).signing_secret"
            placeholder="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
            :disabled="!slackIntegration.activated"
            class="w-full"
            type="password"
          />
          <small class="field-help">{{ t('integrations.slack.signingSecretHelp') }}</small>
        </div>

        <div class="panel-footer">
          <div></div>
          <Button
            type="submit"
            :label="t('integrations.saveConfig')"
            icon="pi pi-save"
            severity="primary"
            :disabled="!slackIntegration.activated"
          />
        </div>
      </form>
    </div>

    <!-- Step 2 — Current state -->
    <div class="panel">
      <div class="panel-header">
        <span class="step-badge">2</span>
        <div>
          <p class="panel-title">{{ t('integrations.currentState') }}</p>
          <p class="panel-subtitle">{{ t('integrations.whatsapp.currentStateSubtitle') }}</p>
        </div>
      </div>

      <div class="panel-body">
        <div class="status-row">
          <div class="status-row-label">
            <i class="pi pi-link"></i>
            Webhook URL
          </div>
          <div class="status-row-value">
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
            <small class="field-help">{{ t('integrations.slack.webhookHelp') }}</small>
          </div>
        </div>

        <div class="status-row">
          <div class="status-row-label">
            <i class="pi pi-key"></i>
            Bot Token
          </div>
          <div class="status-row-value">
            <span class="status-value-text">
              {{
                currentIntegration
                  ? (currentIntegration.config as unknown as SlackIntegrationConfig).bot_token
                    ? '•••••••••••••••••••'
                    : t('integrations.notConfigured')
                  : t('integrations.notConfigured')
              }}
            </span>
          </div>
        </div>

        <div class="status-row">
          <div class="status-row-label">
            <i class="pi pi-lock"></i>
            Signing Secret
          </div>
          <div class="status-row-value">
            <span class="status-value-text">
              {{
                currentIntegration
                  ? (currentIntegration.config as unknown as SlackIntegrationConfig).signing_secret
                    ? '•••••••••••••••••••'
                    : t('integrations.notConfigured')
                  : t('integrations.notConfigured')
              }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- Step 3 — Setup guide -->
    <div class="panel">
      <div class="panel-header">
        <span class="step-badge">3</span>
        <div>
          <p class="panel-title">{{ t('integrations.setupGuide') }}</p>
          <p class="panel-subtitle">{{ t('integrations.slack.stepsSubtitle') }}</p>
        </div>
      </div>

      <ol class="steps-list">
        <li class="step-item">
          <span class="step-num">1</span>
          <span>{{ t('integrations.slack.guideStep1') }}</span>
        </li>
        <li class="step-item">
          <span class="step-num">2</span>
          <span>{{ t('integrations.slack.guideStep2') }}</span>
        </li>
        <li class="step-item">
          <span class="step-num">3</span>
          <span>{{ t('integrations.slack.guideStep3') }}</span>
        </li>
        <li class="step-item">
          <span class="step-num">4</span>
          <span>{{ t('integrations.slack.guideStep4') }}</span>
        </li>
        <li class="step-item">
          <span class="step-num">5</span>
          <span>{{ t('integrations.slack.guideStep5') }}</span>
        </li>
        <li class="step-item">
          <span class="step-num">6</span>
          <span>{{ t('integrations.slack.guideStep6') }}</span>
        </li>
      </ol>
    </div>

    <Toast position="top-right" />
  </div>
</template>

<style scoped>
.integration-container {
  max-width: 860px;
  margin: 0 auto;
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  background: var(--do-bg);
  box-sizing: border-box;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 1rem 1.25rem;
  border: 1px solid var(--do-border-light);
  border-radius: 0.75rem;
  background: rgba(255, 255, 255, 0.03);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 1rem;
  min-width: 0;
}

.icon-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 2rem;
  color: var(--do-blue);
  flex-shrink: 0;
}

.slack-icon {
  color: #611f69;
}

.header-text {
  min-width: 0;
}

.page-title {
  font-size: 1.35rem;
  font-weight: 700;
  color: var(--do-text);
  margin: 0 0 0.2rem;
  line-height: 1.2;
}

.page-subtitle {
  font-size: 0.875rem;
  color: var(--do-text-muted);
  margin: 0;
}

.header-toggle {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-shrink: 0;
}

.toggle-status {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--color-danger);
  transition: color 0.25s;
  white-space: nowrap;
}

.toggle-status.active {
  color: var(--color-success);
}

.panel {
  border: 1px solid var(--do-border-light);
  border-radius: 0.75rem;
  overflow: hidden;
  background: var(--do-bg);
}

.panel-disabled {
  opacity: 0.55;
  filter: grayscale(0.4);
  pointer-events: none;
}

.panel-header {
  display: flex;
  align-items: center;
  gap: 0.875rem;
  padding: 0.875rem 1.25rem;
  border-bottom: 1px solid var(--do-border-light);
  background: rgba(255, 255, 255, 0.025);
}

.step-badge {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.75rem;
  height: 1.75rem;
  border-radius: 50%;
  background: var(--gradient-primary, var(--color-primary));
  color: #fff;
  font-size: 0.8rem;
  font-weight: 700;
  flex-shrink: 0;
}

.panel-title {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--do-text);
  margin: 0 0 0.15rem;
}

.panel-subtitle {
  font-size: 0.8rem;
  color: var(--do-text-muted);
  margin: 0;
}

.panel-body {
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.panel-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding-top: 1rem;
  border-top: 1px solid var(--do-border-light);
  margin-top: 0.25rem;
}

.field-group {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.field-label {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--do-text);
}

.field-icon {
  color: var(--color-primary);
  font-size: 0.875rem;
}

.required {
  color: var(--color-danger);
}

.field-help {
  font-size: 0.8rem;
  color: var(--do-text-muted);
  font-style: italic;
}

.field-error {
  margin-top: 0.25rem;
}

.w-full {
  width: 100%;
}

.status-row {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 0.75rem;
  background: rgba(255, 255, 255, 0.025);
  border: 1px solid var(--do-border-light);
  border-radius: 0.6rem;
}

.status-row-label {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--do-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.status-row-label i {
  color: var(--color-primary);
}

.status-row-value {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.status-value-text {
  font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
  font-size: 0.85rem;
  color: var(--do-text);
}

.webhook-url-wrap {
  display: flex;
  align-items: center;
  border: 1px solid var(--do-border-light);
  border-radius: 0.6rem;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.04);
}

.webhook-url-text {
  flex: 1;
  padding: 0.5rem 0.75rem;
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
  padding: 0 0.75rem;
  min-height: 2.1rem;
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

@media (max-width: 600px) {
  .integration-container {
    padding: 0.75rem;
  }

  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.875rem;
  }

  .header-toggle {
    align-self: flex-end;
  }

  .panel-footer {
    flex-direction: column-reverse;
    align-items: stretch;
  }

  .panel-footer :deep(button) {
    width: 100%;
  }
}
</style>
