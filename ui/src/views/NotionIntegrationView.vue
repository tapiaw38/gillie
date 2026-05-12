<script setup lang="ts">
import type { IntegrationParams, NotionIntegrationConfig } from '@/types/assistant'
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAssistant } from '@/composables/useAssistant'
import { useNotion } from '@/composables/useNotion'
import { useOAuthPopup } from '@/composables/useOAuthPopup'
import { useErrorToast } from '@/composables/useErrorToast'
import { useI18n } from 'vue-i18n'
import Toast from 'primevue/toast'
import Button from 'primevue/button'
import InputSwitch from 'primevue/inputswitch'
import InputText from 'primevue/inputtext'
import Password from 'primevue/password'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()

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
  getCredentials,
  saveCredentials,
  getAuthorizationUrl,
  checkStatus,
  disconnect,
  isConnected,
  workspaceName,
  ownerName,
  isSaveCredentialsPending: isLoading,
  savedClientId,
  savedRedirectUri,
  hasSecret,
  isSaveCredentialsError,
  saveCredentialsError,
  isGetAuthorizationUrlError: isGetAuthUrlError,
  getAuthorizationUrlError: getAuthUrlError,
  isCheckStatusError,
  checkStatusError,
} = useNotion()

const { openOAuthPopup } = useOAuthPopup()

const credentials = reactive({
  clientId: '',
  clientSecret: '',
  redirectUri: '',
})
const credentialsSaved = ref(false)

const notionIntegration = reactive<IntegrationParams>({
  name: 'notion',
  type: 'notion',
  activated: false,
  config: {
    profile_id: '',
    is_connected: false,
  } as NotionIntegrationConfig,
})

const errorWatchers = [
  {
    flag: isSaveCredentialsError,
    summary: t('integrations.notion.errorSaveCredentials'),
    detail: saveCredentialsError,
  },
  {
    flag: isAddIntegrationError,
    summary: t('integrations.notion.errorSaveConfig'),
    detail: addIntegrationError,
  },
  {
    flag: isGetAssistantProfileError,
    summary: t('integrations.notion.errorLoadProfile'),
    detail: getAssistantProfileError,
  },
  {
    flag: isGetAuthUrlError,
    summary: t('integrations.notion.errorGetAuthUrl'),
    detail: getAuthUrlError,
  },
  {
    flag: isCheckStatusError,
    summary: t('integrations.notion.errorCheckStatus'),
    detail: checkStatusError,
  },
]

const { toast } = useErrorToast(errorWatchers)

const handleSaveCredentials = async () => {
  if (!credentials.clientId || !credentials.clientSecret) {
    toast.add({
      severity: 'warn',
      summary: t('integrations.notion.clientIdRequired'),
      detail: t('integrations.notion.clientIdRequired'),
      life: 3000,
    })
    return
  }
  try {
    await saveCredentials(
      credentials.clientId,
      credentials.clientSecret,
      credentials.redirectUri || undefined,
    )
    credentialsSaved.value = true
    toast.add({
      severity: 'success',
      summary: t('integrations.notion.saved'),
      detail: t('integrations.notion.credentialsSavedMsg'),
      life: 3000,
    })
  } catch {
    // handled by watchers
  }
}

const updateIntegration = async () => {
  await addIntegration(notionIntegration)
  await getAssistantProfile()
}

watch(
  () => notionIntegration.activated,
  async () => {
    await updateIntegration()
  },
)

const connectNotion = async () => {
  if (!assistantProfile.value?.id) {
    toast.add({
      severity: 'error',
      summary: t('common.error'),
      detail: t('integrations.notion.errorGetProfileId'),
      life: 3000,
    })
    return
  }

  const config = notionIntegration.config as NotionIntegrationConfig
  config.profile_id = assistantProfile.value.id
  const authData = await getAuthorizationUrl(config.profile_id)
  if (authData?.authorization_url) {
    openOAuthPopup(authData.authorization_url, async () => {
      await activateAfterOAuth()
    })
    return
  }

  toast.add({
    severity: 'error',
    summary: t('common.error'),
    detail: t('integrations.notion.errorGetAuthUrlMsg'),
    life: 3000,
  })
}

const activateAfterOAuth = async () => {
  if (!assistantProfile.value?.id) return
  await checkStatus(assistantProfile.value.id)
  if (isConnected.value) {
    notionIntegration.activated = true
    const config = notionIntegration.config as NotionIntegrationConfig
    config.profile_id = assistantProfile.value.id
    config.is_connected = true
    await addIntegration(notionIntegration)
    toast.add({
      severity: 'success',
      summary: t('integrations.notion.connectedSuccess'),
      detail: t('integrations.notion.connectedSuccessDesc'),
      life: 4000,
    })
  }
}

const handleDisconnect = async () => {
  await disconnect()
  notionIntegration.activated = false
  const config = notionIntegration.config as NotionIntegrationConfig
  config.is_connected = false
  toast.add({
    severity: 'info',
    summary: t('integrations.notion.disconnected'),
    detail: t('integrations.notion.disconnectedDesc'),
    life: 3000,
  })
}

const checkConnectionStatus = async () => {
  if (!assistantProfile.value?.id) return
  await checkStatus(assistantProfile.value.id)
}

const searchNotionIntegration = computed(() =>
  assistantProfile.value?.integrations?.find((i) => i.name === 'notion'),
)

onMounted(async () => {
  await Promise.all([getAssistantProfile(), getCredentials()])

  assistantProfile.value?.integrations?.forEach((integration) => {
    if (integration.name === 'notion') {
      notionIntegration.activated = integration.activated || false
      const config = notionIntegration.config as NotionIntegrationConfig
      const integrationConfig = integration.config as unknown as NotionIntegrationConfig
      config.profile_id = integrationConfig.profile_id || assistantProfile.value?.id || ''
      config.is_connected = integrationConfig.is_connected || false
      config.workspace_name = integrationConfig.workspace_name || ''
      config.owner_name = integrationConfig.owner_name || ''
    }
  })

  await checkConnectionStatus()

  if (route.query.error) {
    toast.add({
      severity: 'error',
      summary: t('integrations.notion.connectionError'),
      detail: t('integrations.notion.connectionErrorDefault'),
      life: 5000,
    })
    router.replace({ query: {} })
  }
})
</script>

<template>
  <div class="integration-container">
    <!-- Header -->
    <div class="page-header">
      <div class="header-left">
        <div class="icon-wrapper notion-icon">
          <i class="pi pi-book"></i>
        </div>
        <div class="header-text">
          <h1 class="page-title">Notion</h1>
          <p class="page-subtitle">{{ t('integrations.notion.subtitle') }}</p>
        </div>
      </div>
      <div class="header-toggle">
        <span class="toggle-status" :class="{ active: notionIntegration.activated }">
          {{ notionIntegration.activated ? t('integrations.active') : t('integrations.inactive') }}
        </span>
        <InputSwitch v-model="notionIntegration.activated" />
      </div>
    </div>

    <!-- Step 1 — OAuth credentials -->
    <div class="panel">
      <div class="panel-header">
        <span class="step-badge">1</span>
        <div>
          <p class="panel-title">{{ t('integrations.notion.oauthCredentials') }}</p>
          <p class="panel-subtitle">{{ t('integrations.notion.oauthSubtitle') }}</p>
        </div>
      </div>

      <div class="panel-body">
        <div v-if="savedClientId && !credentialsSaved" class="credentials-saved-notice">
          <i class="pi pi-check-circle"></i>
          {{ t('integrations.notion.credentialsSaved') }} <strong>{{ savedClientId }}</strong>
        </div>

        <div class="field-group">
          <label class="field-label">Client ID <span class="required">*</span></label>
          <InputText
            v-model="credentials.clientId"
            :placeholder="savedClientId || 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'"
            class="w-full"
          />
        </div>

        <div class="field-group">
          <label class="field-label">Client Secret <span class="required">*</span></label>
          <Password
            v-model="credentials.clientSecret"
            :feedback="false"
            toggle-mask
            fluid
            :placeholder="hasSecret ? '••••••••••••' : 'secret_xxxxxxxxx'"
          />
        </div>

        <div class="field-group">
          <label class="field-label">
            Redirect URI
            <span class="optional">{{ t('integrations.telegram.optional') }}</span>
          </label>
          <InputText
            v-model="credentials.redirectUri"
            :placeholder="savedRedirectUri || 'http://localhost:8000/api/v1/notion/oauth/callback'"
            class="w-full"
          />
        </div>

        <div class="panel-footer">
          <span v-if="credentialsSaved" class="saved-badge">
            <i class="pi pi-check-circle"></i> {{ t('integrations.notion.saved') }}
          </span>
          <span v-else class="spacer"></span>
          <Button
            :label="t('integrations.notion.saveCredentials')"
            icon="pi pi-save"
            severity="primary"
            :loading="isLoading"
            :disabled="(!credentials.clientId && !savedClientId) || (!credentials.clientSecret && !hasSecret)"
            @click="handleSaveCredentials"
          />
        </div>
      </div>
    </div>

    <!-- Step 2 — Connect account -->
    <div class="panel" :class="{ 'panel-disabled': !notionIntegration.activated }">
      <div class="panel-header">
        <span class="step-badge">2</span>
        <div>
          <p class="panel-title">{{ t('integrations.notion.connectAccount') }}</p>
          <p class="panel-subtitle">{{ t('integrations.notion.connectAccountSubtitle') }}</p>
        </div>
      </div>

      <div class="panel-body">
        <!-- Connected state -->
        <div v-if="isConnected" class="connection-state connected">
          <div class="connection-state-icon">
            <i class="pi pi-check-circle"></i>
          </div>
          <div class="connection-state-text">
            <p class="connection-state-title">{{ t('integrations.notion.connected') }}</p>
            <p class="connection-state-subtitle">
              {{ workspaceName || ownerName || t('integrations.notion.connectedDesc') }}
            </p>
          </div>
        </div>

        <!-- Disconnected state -->
        <div v-else class="connection-state disconnected">
          <div class="connection-state-icon">
            <i class="pi pi-times-circle"></i>
          </div>
          <div class="connection-state-text">
            <p class="connection-state-title">{{ t('integrations.notion.notConnected') }}</p>
            <p class="connection-state-subtitle">{{ t('integrations.notion.notConnectedDesc') }}</p>
          </div>
        </div>

        <div class="panel-footer">
          <div class="connection-meta">
            <span class="meta-dot" :class="{ 'meta-dot-ok': isConnected }"></span>
            <span class="meta-label">
              {{
                isConnected
                  ? t('integrations.notion.statusConnected')
                  : searchNotionIntegration
                    ? t('integrations.notion.statusConfigured')
                    : t('integrations.notion.statusNoConnection')
              }}
            </span>
          </div>

          <div class="connection-actions">
            <Button
              v-if="!isConnected"
              :label="t('integrations.notion.connectNotion')"
              icon="pi pi-link"
              severity="primary"
              :disabled="!notionIntegration.activated"
              @click="connectNotion"
            />
            <template v-else>
              <Button
                :label="t('integrations.notion.verify')"
                icon="pi pi-refresh"
                severity="secondary"
                @click="checkConnectionStatus"
              />
              <Button
                :label="t('integrations.disconnect')"
                icon="pi pi-sign-out"
                severity="danger"
                :loading="isLoading"
                @click="handleDisconnect"
              />
            </template>
          </div>
        </div>
      </div>
    </div>

    <!-- Step 3 — Capabilities -->
    <div class="panel">
      <div class="panel-header">
        <span class="step-badge">3</span>
        <div>
          <p class="panel-title">{{ t('integrations.notion.capabilities') }}</p>
          <p class="panel-subtitle">{{ t('integrations.notion.capabilitiesSubtitle') }}</p>
        </div>
      </div>

      <div class="capabilities-grid">
        <div class="capability-item">
          <i class="pi pi-search capability-icon"></i>
          <span>{{ t('integrations.notion.capSearchPages') }}</span>
        </div>
        <div class="capability-item">
          <i class="pi pi-file capability-icon"></i>
          <span>{{ t('integrations.notion.capReadPages') }}</span>
        </div>
        <div class="capability-item">
          <i class="pi pi-sitemap capability-icon"></i>
          <span>{{ t('integrations.notion.capReadBlocks') }}</span>
        </div>
        <div class="capability-item">
          <i class="pi pi-lock capability-icon"></i>
          <span>{{ t('integrations.notion.capSecureAccess') }}</span>
        </div>
      </div>
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
  flex-shrink: 0;
}

.notion-icon {
  background: linear-gradient(135deg, #111827, #0f172a);
  color: #fff;
  width: 3rem;
  height: 3rem;
  border-radius: 0.625rem;
  font-size: 1.25rem;
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

.required {
  color: var(--color-danger);
}

.optional {
  font-size: 0.75rem;
  font-weight: 400;
  color: var(--do-text-muted);
  margin-left: 0.25rem;
}

.w-full {
  width: 100%;
}

:deep(.w-full.p-password) {
  width: 100%;
}

:deep(.w-full.p-password .p-inputtext) {
  width: 100%;
}

.credentials-saved-notice {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.825rem;
  color: var(--color-success);
  background: rgba(34, 197, 94, 0.07);
  border: 1px solid rgba(34, 197, 94, 0.2);
  border-radius: 0.75rem;
  padding: 0.6rem 0.875rem;
}

.saved-badge {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.825rem;
  font-weight: 500;
  color: var(--color-success);
}

.spacer {
  flex: 1;
}

.connection-state {
  display: flex;
  align-items: flex-start;
  gap: 1rem;
  padding: 1rem;
  border-radius: 0.75rem;
  border: 1px solid var(--do-border-light);
}

.connection-state.connected {
  background: rgba(34, 197, 94, 0.05);
  border-color: rgba(34, 197, 94, 0.2);
}

.connection-state.disconnected {
  background: rgba(255, 255, 255, 0.03);
}

.connection-state-icon {
  font-size: 1.5rem;
  flex-shrink: 0;
  line-height: 1;
}

.connected .connection-state-icon {
  color: var(--color-success);
}

.disconnected .connection-state-icon {
  color: var(--do-text-muted);
}

.connection-state-title {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--do-text);
  margin: 0 0 0.25rem;
}

.connection-state-subtitle {
  font-size: 0.825rem;
  color: var(--do-text-muted);
  margin: 0;
  line-height: 1.45;
}

.connection-meta {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.meta-dot {
  width: 0.5rem;
  height: 0.5rem;
  border-radius: 50%;
  background: var(--color-danger);
  transition: background 0.25s;
}

.meta-dot.meta-dot-ok {
  background: var(--color-success);
}

.meta-label {
  font-size: 0.8rem;
  color: var(--do-text-muted);
}

.connection-actions {
  display: flex;
  gap: 0.75rem;
}

.capabilities-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.625rem;
  padding: 1.25rem;
}

.capability-item {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  font-size: 0.825rem;
  color: var(--do-text-muted);
  padding: 0.6rem 0.75rem;
  border: 1px solid var(--do-border-light);
  border-radius: 0.75rem;
  background: rgba(255, 255, 255, 0.025);
}

.capability-icon {
  color: var(--color-success);
  font-size: 0.875rem;
  flex-shrink: 0;
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

  .capabilities-grid {
    grid-template-columns: 1fr;
  }

  .panel-footer {
    flex-direction: column-reverse;
    align-items: stretch;
  }

  .connection-actions {
    flex-direction: column;
    width: 100%;
  }

  .connection-actions :deep(button) {
    width: 100%;
  }

  .panel-footer :deep(button) {
    width: 100%;
  }
}
</style>
