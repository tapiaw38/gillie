<script setup lang="ts">
import type { IntegrationParams, SlackIntegrationConfig } from '@/types/assistant'
import { onMounted, reactive, computed, ref, watch } from 'vue'
import { useAssistant } from '@/composables/useAssistant'
import { useSlack } from '@/composables/useSlack'
import { useClipboard } from '@/composables/useClipboard'
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
const {
  verifyConnection,
  authData,
  isVerifyConnectionPending,
  isVerifyConnectionError,
  verifyConnectionError,
} = useSlack()

const { t } = useI18n()
const { copyText } = useClipboard()
const verificationSucceeded = ref(false)

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
  {
    flag: isVerifyConnectionError,
    summary: t('integrations.slack.errorVerifyConnection'),
    detail: verifyConnectionError,
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
  signing_secret: '',
})

const saveConfig = async () => {
  const config = slackIntegration.config as SlackIntegrationConfig

  validationErrors.bot_token = !config.bot_token ? t('integrations.slack.botTokenRequired') : ''
  validationErrors.signing_secret = !config.signing_secret
    ? t('integrations.slack.signingSecretRequired')
    : ''

  if (validationErrors.bot_token || validationErrors.signing_secret) {
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
    verificationSucceeded.value = false
    toast.add({
      severity: 'success',
      summary: t('integrations.slack.credentialsSaved'),
      life: 3000,
    })
  } catch (error) {
    console.error('Error saving configuration:', error)
  }
}

const updateIntegration = async () => {
  try {
    await addIntegration(slackIntegration)
    await getAssistantProfile()
    verificationSucceeded.value = false
  } catch (error) {
    console.error('Error updating integration:', error)
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
    const copied = await copyText(webhookUrl.value)
    if (!copied) {
      throw new Error('clipboard_unavailable')
    }
    toast.add({
      severity: 'success',
      summary: t('integrations.copyUrl'),
      life: 2000,
    })
  } catch (error) {
    console.error('Error copying webhook URL:', error)
    toast.add({
      severity: 'error',
      summary: t('common.error'),
      detail: t('common.unknownError'),
      life: 3000,
    })
  }
}

const handleVerifyConnection = async () => {
  try {
    const result = await verifyConnection()
    const config = slackIntegration.config as SlackIntegrationConfig
    config.team_id = result.team_id
    config.team_name = result.team
    config.bot_user_id = result.user_id
    await addIntegration(slackIntegration)
    await getAssistantProfile()
    verificationSucceeded.value = true
    toast.add({
      severity: 'success',
      summary: t('integrations.slack.connectedSuccess'),
      detail: t('integrations.slack.connectedSuccessDesc', { team: result.team }),
      life: 3000,
    })
  } catch (error) {
    console.error('Error verifying Slack:', error)
    verificationSucceeded.value = false
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
      config.team_id = saved.team_id || ''
      config.team_name = saved.team_name || ''
      config.bot_user_id = saved.bot_user_id || ''
      verificationSucceeded.value = !!saved.team_id
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
            :disabled="!slackIntegration.activated || isVerifyConnectionPending"
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
            :disabled="!slackIntegration.activated || isVerifyConnectionPending"
            :invalid="!!validationErrors.signing_secret"
            class="w-full"
            type="password"
          />
          <Message v-if="validationErrors.signing_secret" severity="error" class="field-error">
            {{ validationErrors.signing_secret }}
          </Message>
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
          <p class="panel-subtitle">{{ t('integrations.slack.currentStateSubtitle') }}</p>
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

        <div class="status-row">
          <div class="status-row-label">
            <i class="pi pi-building"></i>
            {{ t('integrations.slack.workspaceLabel') }}
          </div>
          <div class="status-row-value">
            <span class="status-value-text">
              {{
                (currentIntegration?.config as unknown as SlackIntegrationConfig)?.team_name
                  || authData?.team
                  || t('integrations.notConfigured')
              }}
            </span>
          </div>
        </div>

        <div class="status-row">
          <div class="status-row-label">
            <i class="pi pi-check-circle"></i>
            {{ t('integrations.status') }}
          </div>
          <div class="status-row-value">
            <span class="status-value-text" :class="verificationSucceeded ? 'text-success' : 'text-muted'">
              {{
                verificationSucceeded
                  ? t('integrations.slack.statusConnected')
                  : t('integrations.slack.statusNotVerified')
              }}
            </span>
          </div>
        </div>
      </div>

      <div class="panel-footer">
        <div></div>
        <Button
          :label="t('integrations.slack.verify')"
          icon="pi pi-check-circle"
          severity="secondary"
          :loading="isVerifyConnectionPending"
          :disabled="
            !slackIntegration.activated ||
            !(slackIntegration.config as SlackIntegrationConfig).bot_token ||
            !(slackIntegration.config as SlackIntegrationConfig).signing_secret
          "
          @click="handleVerifyConnection"
        />
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
/* ── View-specific styles ────────────────────────────────── */
.slack-icon {
  color: #611f69;
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

</style>
