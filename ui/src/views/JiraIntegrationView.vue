<script setup lang="ts">
import type { IntegrationParams, JiraIntegrationConfig } from '@/types/assistant'
import { onMounted, reactive, computed, ref, watch } from 'vue'
import { useAssistant } from '@/composables/useAssistant'
import { useJira } from '@/composables/useJira'
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
  projects,
  isVerifyConnectionPending,
  isVerifyConnectionError,
  verifyConnectionError,
} = useJira()

const { t } = useI18n()
const verificationSucceeded = ref(false)

const errorWatchers = [
  { flag: isAddIntegrationError, summary: t('systemCommands.errorSaveConfig'), detail: addIntegrationError },
  { flag: isGetAssistantProfileError, summary: t('systemCommands.errorLoadProfile'), detail: getAssistantProfileError },
  {
    flag: isVerifyConnectionError,
    summary: t('integrations.jira.errorVerifyConnection'),
    detail: verifyConnectionError,
  },
]
const { toast } = useErrorToast(errorWatchers)

const jiraIntegration = reactive<IntegrationParams>({
  name: 'jira',
  type: 'integration',
  activated: false,
  config: {
    domain: '',
    email: '',
    api_token: '',
  } as JiraIntegrationConfig,
})

const validationErrors = reactive({ domain: '', email: '', api_token: '' })

const saveConfig = async () => {
  const config = jiraIntegration.config as JiraIntegrationConfig
  validationErrors.domain = !config.domain ? t('integrations.jira.domainRequired') : ''
  validationErrors.email = !config.email ? t('integrations.jira.emailRequired') : ''
  validationErrors.api_token = !config.api_token ? t('integrations.jira.apiTokenHelp') : ''

  if (validationErrors.domain || validationErrors.email || validationErrors.api_token) {
    toast.add({ severity: 'warn', summary: t('common.requiredFields'), detail: t('common.completeRequired'), life: 3000 })
    return
  }

  try {
    await addIntegration(jiraIntegration)
    await getAssistantProfile()
    verificationSucceeded.value = false
    toast.add({ severity: 'success', summary: t('integrations.jira.credentialsSaved'), life: 3000 })
  } catch (error) {
    console.error('Error saving Jira config:', error)
  }
}

const updateIntegration = async () => {
  try {
    await addIntegration(jiraIntegration)
    await getAssistantProfile()
    verificationSucceeded.value = false
  } catch (error) {
    console.error('Error updating Jira integration:', error)
  }
}

watch(() => jiraIntegration.activated, async () => { await updateIntegration() })

const handleVerifyConnection = async () => {
  try {
    const result = await verifyConnection()
    verificationSucceeded.value = true
    toast.add({
      severity: 'success',
      summary: t('integrations.jira.connectedSuccess'),
      detail: t('integrations.jira.connectedSuccessDesc', { count: result.length }),
      life: 3000,
    })
  } catch {
    verificationSucceeded.value = false
  }
}

const currentIntegration = computed(() =>
  assistantProfile.value?.integrations?.find((i) => i.name === 'jira'),
)

onMounted(async () => {
  await getAssistantProfile()
  assistantProfile.value?.integrations?.forEach((integration) => {
    if (integration.name === 'jira') {
      jiraIntegration.activated = integration.activated || false
      const config = jiraIntegration.config as JiraIntegrationConfig
      const saved = integration.config as unknown as JiraIntegrationConfig
      config.domain = saved.domain || ''
      config.email = saved.email || ''
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
        <div class="icon-wrapper jira-icon">
          <svg viewBox="0 0 32 32" width="36" height="36" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M28 4H16.5L28 15.5V4Z" fill="#2684FF" opacity="0.4"/>
            <path d="M16 4L4 16L10 22L16 16L22 22L28 16L16 4Z" fill="#2684FF"/>
            <path d="M10 22L16 28L22 22L16 16L10 22Z" fill="#2684FF"/>
          </svg>
        </div>
        <div class="header-text">
          <h1 class="page-title">{{ t('integrations.jira.title') }}</h1>
          <p class="page-subtitle">{{ t('integrations.jira.subtitle') }}</p>
        </div>
      </div>
      <div class="header-toggle">
        <span class="toggle-status" :class="{ active: jiraIntegration.activated }">
          {{ jiraIntegration.activated ? t('integrations.active') : t('integrations.inactive') }}
        </span>
        <InputSwitch v-model="jiraIntegration.activated" />
      </div>
    </div>

    <!-- Step 1 — Credentials -->
    <div class="panel" :class="{ 'panel-disabled': !jiraIntegration.activated }">
      <div class="panel-header">
        <span class="step-badge">1</span>
        <div>
          <p class="panel-title">{{ t('integrations.jira.credentialsTitle') }}</p>
          <p class="panel-subtitle">{{ t('integrations.jira.credentialsSubtitle') }}</p>
        </div>
      </div>

      <form class="panel-body" @submit.prevent="saveConfig">
        <div class="field-group">
          <label for="domain" class="field-label">
            <i class="pi pi-globe field-icon"></i>
            {{ t('integrations.jira.domainLabel') }}
            <span class="required">*</span>
          </label>
          <InputText
            id="domain"
            v-model="(jiraIntegration.config as JiraIntegrationConfig).domain"
            placeholder="miempresa.atlassian.net"
            :disabled="!jiraIntegration.activated"
            :invalid="!!validationErrors.domain"
            class="w-full"
          />
          <Message v-if="validationErrors.domain" severity="error" class="field-error">{{ validationErrors.domain }}</Message>
          <small class="field-help">{{ t('integrations.jira.domainHelp') }}</small>
        </div>

        <div class="field-group">
          <label for="email" class="field-label">
            <i class="pi pi-envelope field-icon"></i>
            Email
            <span class="required">*</span>
          </label>
          <InputText
            id="email"
            v-model="(jiraIntegration.config as JiraIntegrationConfig).email"
            placeholder="usuario@empresa.com"
            :disabled="!jiraIntegration.activated"
            :invalid="!!validationErrors.email"
            class="w-full"
          />
          <Message v-if="validationErrors.email" severity="error" class="field-error">{{ validationErrors.email }}</Message>
          <small class="field-help">{{ t('integrations.jira.emailHelp') }}</small>
        </div>

        <div class="field-group">
          <label for="jira_api_token" class="field-label">
            <i class="pi pi-key field-icon"></i>
            API Token
            <span class="required">*</span>
          </label>
          <InputText
            id="jira_api_token"
            v-model="(jiraIntegration.config as JiraIntegrationConfig).api_token"
            placeholder="ATATT3xFfGF0..."
            :disabled="!jiraIntegration.activated"
            :invalid="!!validationErrors.api_token"
            class="w-full"
            type="password"
          />
          <Message v-if="validationErrors.api_token" severity="error" class="field-error">{{ validationErrors.api_token }}</Message>
          <small class="field-help">{{ t('integrations.jira.apiTokenHelp') }}</small>
        </div>

        <div class="panel-footer">
          <div></div>
          <Button
            type="submit"
            :label="t('integrations.saveConfig')"
            icon="pi pi-save"
            severity="primary"
            :disabled="!jiraIntegration.activated"
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
          <p class="panel-subtitle">{{ t('integrations.jira.currentStateSubtitle') }}</p>
        </div>
      </div>

      <div class="panel-body">
        <div class="status-row">
          <div class="status-row-label"><i class="pi pi-globe"></i> {{ t('integrations.jira.domainLabel') }}</div>
          <div class="status-row-value">
            <span class="status-value-text">
              {{ (currentIntegration?.config as unknown as JiraIntegrationConfig)?.domain || t('integrations.notConfigured') }}
            </span>
          </div>
        </div>

        <div class="status-row">
          <div class="status-row-label"><i class="pi pi-envelope"></i> Email</div>
          <div class="status-row-value">
            <span class="status-value-text">
              {{ (currentIntegration?.config as unknown as JiraIntegrationConfig)?.email || t('integrations.notConfigured') }}
            </span>
          </div>
        </div>

        <div class="status-row">
          <div class="status-row-label"><i class="pi pi-key"></i> API Token</div>
          <div class="status-row-value">
            <span class="status-value-text">
              {{
                (currentIntegration?.config as unknown as JiraIntegrationConfig)?.api_token
                  ? '•••••••••••••••••••'
                  : t('integrations.notConfigured')
              }}
            </span>
          </div>
        </div>

        <div class="status-row">
          <div class="status-row-label"><i class="pi pi-folder"></i> {{ t('integrations.jira.projectsLabel') }}</div>
          <div class="status-row-value">
            <span class="status-value-text">
              {{
                verificationSucceeded
                  ? t('integrations.jira.projectsCount', { count: projects?.length || 0 })
                  : t('integrations.notConfigured')
              }}
            </span>
          </div>
        </div>

        <div class="status-row">
          <div class="status-row-label"><i class="pi pi-link"></i> {{ t('integrations.status') }}</div>
          <div class="status-row-value">
            <span class="status-value-text" :class="verificationSucceeded ? 'text-success' : 'text-muted'">
              {{
                verificationSucceeded
                  ? t('integrations.jira.statusConnected')
                  : t('integrations.jira.statusNotVerified')
              }}
            </span>
          </div>
        </div>
      </div>

      <div class="panel-footer">
        <div></div>
        <Button
          :label="t('integrations.jira.verify')"
          icon="pi pi-check-circle"
          severity="secondary"
          :loading="isVerifyConnectionPending"
          :disabled="
            !jiraIntegration.activated ||
            !(jiraIntegration.config as JiraIntegrationConfig).domain ||
            !(jiraIntegration.config as JiraIntegrationConfig).email ||
            !(jiraIntegration.config as JiraIntegrationConfig).api_token
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
          <p class="panel-subtitle">{{ t('integrations.jira.stepsSubtitle') }}</p>
        </div>
      </div>

      <ol class="steps-list">
        <li class="step-item"><span class="step-num">1</span><span>{{ t('integrations.jira.guideStep1') }}</span></li>
        <li class="step-item"><span class="step-num">2</span><span>{{ t('integrations.jira.guideStep2') }}</span></li>
        <li class="step-item"><span class="step-num">3</span><span>{{ t('integrations.jira.guideStep3') }}</span></li>
        <li class="step-item"><span class="step-num">4</span><span>{{ t('integrations.jira.guideStep4') }}</span></li>
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
.jira-icon { color: #2684ff; }
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
