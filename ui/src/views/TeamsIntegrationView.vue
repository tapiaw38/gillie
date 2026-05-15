<script setup lang="ts">
import type { IntegrationParams, TeamsIntegrationConfig } from '@/types/assistant'
import { onMounted, reactive, computed, ref, watch } from 'vue'
import { useAssistant } from '@/composables/useAssistant'
import { useTeams } from '@/composables/useTeams'
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
  verifyResult,
  isVerifyConnectionPending,
  isVerifyConnectionError,
  verifyConnectionError,
} = useTeams()

const { t } = useI18n()
const verificationSucceeded = ref(false)

const errorWatchers = [
  { flag: isAddIntegrationError, summary: t('systemCommands.errorSaveConfig'), detail: addIntegrationError },
  { flag: isGetAssistantProfileError, summary: t('systemCommands.errorLoadProfile'), detail: getAssistantProfileError },
  {
    flag: isVerifyConnectionError,
    summary: t('integrations.teams.errorVerifyConnection'),
    detail: verifyConnectionError,
  },
]
const { toast } = useErrorToast(errorWatchers)

const teamsIntegration = reactive<IntegrationParams>({
  name: 'teams',
  type: 'integration',
  activated: false,
  config: {
    app_id: '',
    app_password: '',
  } as TeamsIntegrationConfig,
})

const validationErrors = reactive({ app_id: '', app_password: '' })

const saveConfig = async () => {
  const config = teamsIntegration.config as TeamsIntegrationConfig
  validationErrors.app_id = !config.app_id ? t('integrations.teams.appIdRequired') : ''
  validationErrors.app_password = !config.app_password ? t('integrations.teams.appPasswordRequired') : ''

  if (validationErrors.app_id || validationErrors.app_password) {
    toast.add({ severity: 'warn', summary: t('common.requiredFields'), detail: t('common.completeRequired'), life: 3000 })
    return
  }

  try {
    await addIntegration(teamsIntegration)
    await getAssistantProfile()
    verificationSucceeded.value = false
    toast.add({ severity: 'success', summary: t('integrations.teams.credentialsSaved'), life: 3000 })
  } catch (error) {
    console.error('Error saving Teams config:', error)
  }
}

const updateIntegration = async () => {
  try {
    await addIntegration(teamsIntegration)
    await getAssistantProfile()
    verificationSucceeded.value = false
  } catch (error) {
    console.error('Error updating Teams integration:', error)
  }
}

watch(() => teamsIntegration.activated, async () => { await updateIntegration() })

const handleVerifyConnection = async () => {
  try {
    await verifyConnection()
    verificationSucceeded.value = true
    toast.add({
      severity: 'success',
      summary: t('integrations.teams.connectedSuccess'),
      detail: verifyResult.value?.message || '',
      life: 3000,
    })
  } catch {
    verificationSucceeded.value = false
  }
}

const currentIntegration = computed(() =>
  assistantProfile.value?.integrations?.find((i) => i.name === 'teams'),
)

onMounted(async () => {
  await getAssistantProfile()
  assistantProfile.value?.integrations?.forEach((integration) => {
    if (integration.name === 'teams') {
      teamsIntegration.activated = integration.activated || false
      const config = teamsIntegration.config as TeamsIntegrationConfig
      const saved = integration.config as unknown as TeamsIntegrationConfig
      config.app_id = saved.app_id || ''
      config.app_password = saved.app_password || ''
      config.tenant_id = saved.tenant_id || ''
      config.bot_id = saved.bot_id || ''
      config.service_url = saved.service_url || ''
      verificationSucceeded.value = !!saved.tenant_id
    }
  })
})
</script>

<template>
  <div class="integration-container">
    <!-- Header -->
    <div class="page-header">
      <div class="header-left">
        <div class="icon-wrapper teams-icon">
          <svg viewBox="0 0 32 32" width="36" height="36" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect x="2" y="10" width="18" height="16" rx="3" fill="#5059C9"/>
            <rect x="12" y="4" width="18" height="16" rx="3" fill="#7B83EB"/>
            <circle cx="21" cy="8" r="4" fill="#5059C9"/>
            <circle cx="9" cy="14" r="4" fill="#fff" opacity="0.9"/>
            <text x="9" y="17.5" font-size="5" font-weight="700" fill="#5059C9" text-anchor="middle">T</text>
          </svg>
        </div>
        <div class="header-text">
          <h1 class="page-title">{{ t('integrations.teams.title') }}</h1>
          <p class="page-subtitle">{{ t('integrations.teams.subtitle') }}</p>
        </div>
      </div>
      <div class="header-toggle">
        <span class="toggle-status" :class="{ active: teamsIntegration.activated }">
          {{ teamsIntegration.activated ? t('integrations.active') : t('integrations.inactive') }}
        </span>
        <InputSwitch v-model="teamsIntegration.activated" />
      </div>
    </div>

    <!-- Step 1 — Credentials -->
    <div class="panel" :class="{ 'panel-disabled': !teamsIntegration.activated }">
      <div class="panel-header">
        <span class="step-badge">1</span>
        <div>
          <p class="panel-title">{{ t('integrations.teams.credentialsTitle') }}</p>
          <p class="panel-subtitle">{{ t('integrations.teams.credentialsSubtitle') }}</p>
        </div>
      </div>

      <form class="panel-body" @submit.prevent="saveConfig">
        <div class="field-group">
          <label for="app_id" class="field-label">
            <i class="pi pi-id-card field-icon"></i>
            {{ t('integrations.teams.appIdLabel') }}
            <span class="required">*</span>
          </label>
          <InputText
            id="app_id"
            v-model="(teamsIntegration.config as TeamsIntegrationConfig).app_id"
            placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
            :disabled="!teamsIntegration.activated"
            :invalid="!!validationErrors.app_id"
            class="w-full"
          />
          <Message v-if="validationErrors.app_id" severity="error" class="field-error">{{ validationErrors.app_id }}</Message>
          <small class="field-help">{{ t('integrations.teams.appIdHelp') }}</small>
        </div>

        <div class="field-group">
          <label for="app_password" class="field-label">
            <i class="pi pi-key field-icon"></i>
            {{ t('integrations.teams.appPasswordLabel') }}
            <span class="required">*</span>
          </label>
          <InputText
            id="app_password"
            v-model="(teamsIntegration.config as TeamsIntegrationConfig).app_password"
            placeholder="Client secret del registro de Azure"
            :disabled="!teamsIntegration.activated"
            :invalid="!!validationErrors.app_password"
            class="w-full"
            type="password"
          />
          <Message v-if="validationErrors.app_password" severity="error" class="field-error">{{ validationErrors.app_password }}</Message>
          <small class="field-help">{{ t('integrations.teams.appPasswordHelp') }}</small>
        </div>

        <div class="panel-footer">
          <div></div>
          <Button
            type="submit"
            :label="t('integrations.saveConfig')"
            icon="pi pi-save"
            severity="primary"
            :disabled="!teamsIntegration.activated"
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
          <p class="panel-subtitle">{{ t('integrations.teams.currentStateSubtitle') }}</p>
        </div>
      </div>

      <div class="panel-body">
        <div class="status-row">
          <div class="status-row-label"><i class="pi pi-id-card"></i> {{ t('integrations.teams.appIdLabel') }}</div>
          <div class="status-row-value">
            <span class="status-value-text">
              {{ (currentIntegration?.config as unknown as TeamsIntegrationConfig)?.app_id || t('integrations.notConfigured') }}
            </span>
          </div>
        </div>

        <div class="status-row">
          <div class="status-row-label"><i class="pi pi-key"></i> {{ t('integrations.teams.appPasswordLabel') }}</div>
          <div class="status-row-value">
            <span class="status-value-text">
              {{
                (currentIntegration?.config as unknown as TeamsIntegrationConfig)?.app_password
                  ? '•••••••••••••••••••'
                  : t('integrations.notConfigured')
              }}
            </span>
          </div>
        </div>

        <div class="status-row">
          <div class="status-row-label"><i class="pi pi-check-circle"></i> {{ t('integrations.status') }}</div>
          <div class="status-row-value">
            <span class="status-value-text" :class="currentIntegration?.activated ? 'text-success' : 'text-muted'">
              {{ currentIntegration?.activated ? t('integrations.active') : t('integrations.inactive') }}
            </span>
          </div>
        </div>

        <div class="status-row">
          <div class="status-row-label"><i class="pi pi-building"></i> {{ t('integrations.teams.tenantLabel') }}</div>
          <div class="status-row-value">
            <span class="status-value-text">
              {{ (currentIntegration?.config as unknown as TeamsIntegrationConfig)?.tenant_id || t('integrations.notConfigured') }}
            </span>
          </div>
        </div>

        <div class="status-row">
          <div class="status-row-label"><i class="pi pi-user"></i> {{ t('integrations.teams.botIdLabel') }}</div>
          <div class="status-row-value">
            <span class="status-value-text">
              {{ (currentIntegration?.config as unknown as TeamsIntegrationConfig)?.bot_id || t('integrations.notConfigured') }}
            </span>
          </div>
        </div>

        <div class="status-row">
          <div class="status-row-label"><i class="pi pi-link"></i> {{ t('integrations.status') }}</div>
          <div class="status-row-value">
            <span class="status-value-text" :class="verificationSucceeded ? 'text-success' : 'text-muted'">
              {{
                verificationSucceeded
                  ? t('integrations.teams.statusConnected')
                  : t('integrations.teams.statusNotVerified')
              }}
            </span>
          </div>
        </div>
      </div>

      <div class="panel-footer">
        <div></div>
        <Button
          :label="t('integrations.teams.verify')"
          icon="pi pi-check-circle"
          severity="secondary"
          :loading="isVerifyConnectionPending"
          :disabled="
            !teamsIntegration.activated ||
            !(teamsIntegration.config as TeamsIntegrationConfig).app_id ||
            !(teamsIntegration.config as TeamsIntegrationConfig).app_password
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
          <p class="panel-subtitle">{{ t('integrations.teams.stepsSubtitle') }}</p>
        </div>
      </div>

      <ol class="steps-list">
        <li class="step-item"><span class="step-num">1</span><span>{{ t('integrations.teams.guideStep1') }}</span></li>
        <li class="step-item"><span class="step-num">2</span><span>{{ t('integrations.teams.guideStep2') }}</span></li>
        <li class="step-item"><span class="step-num">3</span><span>{{ t('integrations.teams.guideStep3') }}</span></li>
        <li class="step-item"><span class="step-num">4</span><span>{{ t('integrations.teams.guideStep4') }}</span></li>
        <li class="step-item"><span class="step-num">5</span><span>{{ t('integrations.teams.guideStep5') }}</span></li>
      </ol>
    </div>

    <Toast position="top-right" />
  </div>
</template>

<style scoped>
.integration-container { max-width: 860px; margin: 0 auto; padding: 1.25rem; display: flex; flex-direction: column; gap: 1rem; background: var(--do-bg); box-sizing: border-box; }
.page-header { display: flex; align-items: center; justify-content: space-between; gap: 1rem; padding: 1rem 1.25rem; border: 1px solid var(--do-border-light); border-radius: 0.75rem; background: rgba(255, 255, 255, 0.03); }
.header-left { display: flex; align-items: center; gap: 1rem; min-width: 0; }
.icon-wrapper { display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.teams-icon { color: #5059c9; }
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
