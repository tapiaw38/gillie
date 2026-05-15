<script setup lang="ts">
import type { IntegrationParams, ClickUpIntegrationConfig } from '@/types/assistant'
import { onMounted, reactive, computed, ref, watch } from 'vue'
import { useAssistant } from '@/composables/useAssistant'
import { useClickUp } from '@/composables/useClickUp'
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
  workspaces,
  isVerifyConnectionPending,
  isVerifyConnectionError,
  verifyConnectionError,
} = useClickUp()

const { t } = useI18n()
const verificationSucceeded = ref(false)

const errorWatchers = [
  { flag: isAddIntegrationError, summary: t('systemCommands.errorSaveConfig'), detail: addIntegrationError },
  { flag: isGetAssistantProfileError, summary: t('systemCommands.errorLoadProfile'), detail: getAssistantProfileError },
  {
    flag: isVerifyConnectionError,
    summary: t('integrations.clickup.errorVerifyConnection'),
    detail: verifyConnectionError,
  },
]
const { toast } = useErrorToast(errorWatchers)

const clickupIntegration = reactive<IntegrationParams>({
  name: 'clickup',
  type: 'integration',
  activated: false,
  config: {
    api_token: '',
  } as ClickUpIntegrationConfig,
})

const validationErrors = reactive({ api_token: '' })

const saveConfig = async () => {
  const config = clickupIntegration.config as ClickUpIntegrationConfig
  validationErrors.api_token = !config.api_token ? t('integrations.clickup.apiTokenHelp') : ''

  if (validationErrors.api_token) {
    toast.add({ severity: 'warn', summary: t('common.requiredFields'), detail: t('common.completeRequired'), life: 3000 })
    return
  }

  try {
    await addIntegration(clickupIntegration)
    await getAssistantProfile()
    verificationSucceeded.value = false
    toast.add({ severity: 'success', summary: t('integrations.clickup.credentialsSaved'), life: 3000 })
  } catch (error) {
    console.error('Error saving ClickUp config:', error)
  }
}

const updateIntegration = async () => {
  try {
    await addIntegration(clickupIntegration)
    await getAssistantProfile()
    verificationSucceeded.value = false
  } catch (error) {
    console.error('Error updating ClickUp integration:', error)
  }
}

watch(() => clickupIntegration.activated, async () => { await updateIntegration() })

const handleVerifyConnection = async () => {
  try {
    const result = await verifyConnection()
    verificationSucceeded.value = true
    toast.add({
      severity: 'success',
      summary: t('integrations.clickup.connectedSuccess'),
      detail: t('integrations.clickup.connectedSuccessDesc', { count: result.length }),
      life: 3000,
    })
  } catch {
    verificationSucceeded.value = false
  }
}

const currentIntegration = computed(() =>
  assistantProfile.value?.integrations?.find((i) => i.name === 'clickup'),
)

onMounted(async () => {
  await getAssistantProfile()
  assistantProfile.value?.integrations?.forEach((integration) => {
    if (integration.name === 'clickup') {
      clickupIntegration.activated = integration.activated || false
      const config = clickupIntegration.config as ClickUpIntegrationConfig
      const saved = integration.config as unknown as ClickUpIntegrationConfig
      config.api_token = saved.api_token || ''
    }
  })
})
</script>

<template>
  <div class="integration-container">
    <!-- Header -->
    <div class="page-header">
      <div class="header-left">
        <div class="icon-wrapper clickup-icon">
          <svg viewBox="0 0 32 32" width="36" height="36" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M2 22.5L7.5 17.5C10 22 12.5 24 16 24C19.5 24 22 22 24.5 17.5L30 22.5C26.5 28 21.5 31 16 31C10.5 31 5.5 28 2 22.5Z" fill="#7B68EE"/>
            <path d="M16 4L7 13L10.5 16.5L16 11L21.5 16.5L25 13L16 4Z" fill="url(#cu-grad)"/>
            <defs>
              <linearGradient id="cu-grad" x1="7" y1="4" x2="25" y2="16.5" gradientUnits="userSpaceOnUse">
                <stop stop-color="#7B68EE"/>
                <stop offset="1" stop-color="#FF6B6B"/>
              </linearGradient>
            </defs>
          </svg>
        </div>
        <div class="header-text">
          <h1 class="page-title">{{ t('integrations.clickup.title') }}</h1>
          <p class="page-subtitle">{{ t('integrations.clickup.subtitle') }}</p>
        </div>
      </div>
      <div class="header-toggle">
        <span class="toggle-status" :class="{ active: clickupIntegration.activated }">
          {{ clickupIntegration.activated ? t('integrations.active') : t('integrations.inactive') }}
        </span>
        <InputSwitch v-model="clickupIntegration.activated" />
      </div>
    </div>

    <!-- Step 1 — Credentials -->
    <div class="panel" :class="{ 'panel-disabled': !clickupIntegration.activated }">
      <div class="panel-header">
        <span class="step-badge">1</span>
        <div>
          <p class="panel-title">{{ t('integrations.clickup.credentialsTitle') }}</p>
          <p class="panel-subtitle">{{ t('integrations.clickup.credentialsSubtitle') }}</p>
        </div>
      </div>

      <form class="panel-body" @submit.prevent="saveConfig">
        <div class="field-group">
          <label for="api_token" class="field-label">
            <i class="pi pi-key field-icon"></i>
            API Token
            <span class="required">*</span>
          </label>
          <InputText
            id="api_token"
            v-model="(clickupIntegration.config as ClickUpIntegrationConfig).api_token"
            placeholder="pk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
            :disabled="!clickupIntegration.activated"
            :invalid="!!validationErrors.api_token"
            class="w-full"
            type="password"
          />
          <Message v-if="validationErrors.api_token" severity="error" class="field-error">
            {{ validationErrors.api_token }}
          </Message>
          <small class="field-help">{{ t('integrations.clickup.apiTokenHelp') }}</small>
        </div>

        <div class="panel-footer">
          <div></div>
          <Button
            type="submit"
            :label="t('integrations.saveConfig')"
            icon="pi pi-save"
            severity="primary"
            :disabled="!clickupIntegration.activated"
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
          <p class="panel-subtitle">{{ t('integrations.clickup.currentStateSubtitle') }}</p>
        </div>
      </div>

      <div class="panel-body">
        <div class="status-row">
          <div class="status-row-label">
            <i class="pi pi-key"></i>
            API Token
          </div>
          <div class="status-row-value">
            <span class="status-value-text">
              {{
                currentIntegration
                  ? (currentIntegration.config as unknown as ClickUpIntegrationConfig).api_token
                    ? '•••••••••••••••••••'
                    : t('integrations.notConfigured')
                  : t('integrations.notConfigured')
              }}
            </span>
          </div>
        </div>

        <div class="status-row">
          <div class="status-row-label">
            <i class="pi pi-briefcase"></i>
            {{ t('integrations.clickup.workspacesLabel') }}
          </div>
          <div class="status-row-value">
            <span class="status-value-text">
              {{
                verificationSucceeded
                  ? t('integrations.clickup.workspacesCount', { count: workspaces?.length || 0 })
                  : t('integrations.notConfigured')
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
            <span class="status-value-text" :class="currentIntegration?.activated ? 'text-success' : 'text-muted'">
              {{ currentIntegration?.activated ? t('integrations.active') : t('integrations.inactive') }}
            </span>
          </div>
        </div>

        <div class="status-row">
          <div class="status-row-label">
            <i class="pi pi-link"></i>
            {{ t('integrations.status') }}
          </div>
          <div class="status-row-value">
            <span class="status-value-text" :class="verificationSucceeded ? 'text-success' : 'text-muted'">
              {{
                verificationSucceeded
                  ? t('integrations.clickup.statusConnected')
                  : t('integrations.clickup.statusNotVerified')
              }}
            </span>
          </div>
        </div>
      </div>

      <div class="panel-footer">
        <div></div>
        <Button
          :label="t('integrations.clickup.verify')"
          icon="pi pi-check-circle"
          severity="secondary"
          :loading="isVerifyConnectionPending"
          :disabled="!clickupIntegration.activated || !(clickupIntegration.config as ClickUpIntegrationConfig).api_token"
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
          <p class="panel-subtitle">{{ t('integrations.clickup.stepsSubtitle') }}</p>
        </div>
      </div>

      <ol class="steps-list">
        <li class="step-item"><span class="step-num">1</span><span>{{ t('integrations.clickup.guideStep1') }}</span></li>
        <li class="step-item"><span class="step-num">2</span><span>{{ t('integrations.clickup.guideStep2') }}</span></li>
        <li class="step-item"><span class="step-num">3</span><span>{{ t('integrations.clickup.guideStep3') }}</span></li>
        <li class="step-item"><span class="step-num">4</span><span>{{ t('integrations.clickup.guideStep4') }}</span></li>
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
.header-left { display: flex; align-items: center; gap: 1rem; min-width: 0; }
.icon-wrapper { display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.clickup-icon { color: #7b68ee; }
.header-text { min-width: 0; }
.page-title { font-size: 1.35rem; font-weight: 700; color: var(--do-text); margin: 0 0 0.2rem; line-height: 1.2; }
.page-subtitle { font-size: 0.875rem; color: var(--do-text-muted); margin: 0; }
.header-toggle { display: flex; align-items: center; gap: 0.75rem; flex-shrink: 0; }
.toggle-status { font-size: 0.8rem; font-weight: 600; color: var(--color-danger); transition: color 0.25s; white-space: nowrap; }
.toggle-status.active { color: var(--color-success); }
.panel { border: 1px solid var(--do-border-light); border-radius: 0.75rem; overflow: hidden; background: var(--do-bg); }
.panel-disabled { opacity: 0.55; filter: grayscale(0.4); pointer-events: none; }
.panel-header { display: flex; align-items: center; gap: 0.875rem; padding: 0.875rem 1.25rem; border-bottom: 1px solid var(--do-border-light); background: rgba(255, 255, 255, 0.025); }
.step-badge { display: flex; align-items: center; justify-content: center; width: 1.75rem; height: 1.75rem; border-radius: 50%; background: var(--gradient-primary, var(--color-primary)); color: #fff; font-size: 0.8rem; font-weight: 700; flex-shrink: 0; }
.panel-title { font-size: 0.95rem; font-weight: 600; color: var(--do-text); margin: 0 0 0.15rem; }
.panel-subtitle { font-size: 0.8rem; color: var(--do-text-muted); margin: 0; }
.panel-body { padding: 1.25rem; display: flex; flex-direction: column; gap: 1rem; }
.panel-footer { display: flex; align-items: center; justify-content: space-between; gap: 1rem; padding-top: 1rem; border-top: 1px solid var(--do-border-light); margin-top: 0.25rem; }
.field-group { display: flex; flex-direction: column; gap: 0.4rem; }
.field-label { display: flex; align-items: center; gap: 0.4rem; font-size: 0.875rem; font-weight: 600; color: var(--do-text); }
.field-icon { color: var(--color-primary); font-size: 0.875rem; }
.required { color: var(--color-danger); }
.field-help { font-size: 0.8rem; color: var(--do-text-muted); font-style: italic; }
.field-error { margin-top: 0.25rem; }
.w-full { width: 100%; }
.status-row { display: flex; flex-direction: column; gap: 0.5rem; padding: 0.75rem; background: rgba(255, 255, 255, 0.025); border: 1px solid var(--do-border-light); border-radius: 0.6rem; }
.status-row-label { display: flex; align-items: center; gap: 0.4rem; font-size: 0.78rem; font-weight: 600; color: var(--do-text-muted); text-transform: uppercase; letter-spacing: 0.03em; }
.status-row-label i { color: var(--color-primary); }
.status-row-value { display: flex; flex-direction: column; gap: 0.35rem; }
.status-value-text { font-family: 'SF Mono', 'Monaco', 'Consolas', monospace; font-size: 0.85rem; color: var(--do-text); }
.text-success { color: var(--color-success) !important; }
.text-muted { color: var(--do-text-muted) !important; }
.steps-list { list-style: none; margin: 0; padding: 1rem 1.25rem 1.25rem; display: flex; flex-direction: column; gap: 0.6rem; }
.step-item { display: flex; align-items: baseline; gap: 0.75rem; font-size: 0.875rem; color: var(--do-text-muted); }
.step-num { display: flex; align-items: center; justify-content: center; width: 1.4rem; height: 1.4rem; border-radius: 50%; border: 1px solid var(--do-border-light); font-size: 0.7rem; font-weight: 700; color: var(--do-text-muted); flex-shrink: 0; }
@media (max-width: 600px) {
  .integration-container { padding: 0.75rem; }
  .page-header { flex-direction: column; align-items: flex-start; gap: 0.875rem; }
  .header-toggle { align-self: flex-end; }
  .panel-footer { flex-direction: column-reverse; align-items: stretch; }
  .panel-footer :deep(button) { width: 100%; }
}
</style>
