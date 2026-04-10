<script setup lang="ts">
import type { IntegrationParams, GoogleGmailIntegrationConfig } from '@/types/assistant'
import { onMounted, reactive, computed, watch, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAssistant } from '@/composables/useAssistant'
import { useGmail } from '@/composables/useGmail'
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
  connectedEmail,
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
} = useGmail()

const handleDisconnect = async () => {
  await disconnect()
  gmailIntegration.activated = false
  const config = gmailIntegration.config as GoogleGmailIntegrationConfig
  config.is_connected = false
  toast.add({
    severity: 'info',
    summary: t('integrations.googleGmail.disconnected'),
    detail: t('integrations.googleGmail.disconnectedDesc'),
    life: 3000,
  })
}

const { openOAuthPopup } = useOAuthPopup()

const credentials = reactive({
  clientId: '',
  clientSecret: '',
  redirectUri: '',
})
const credentialsSaved = ref(false)

const handleSaveCredentials = async () => {
  if (!credentials.clientId || !credentials.clientSecret) {
    toast.add({
      severity: 'warn',
      summary: t('integrations.googleGmail.clientIdRequired'),
      detail: t('integrations.googleGmail.clientIdRequired'),
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
      summary: t('integrations.googleGmail.saved'),
      detail: t('integrations.googleGmail.credentialsSavedMsg'),
      life: 3000,
    })
  } catch {
    // handled by errorWatchers
  }
}

const errorWatchers = [
  {
    flag: isSaveCredentialsError,
    summary: t('integrations.googleGmail.errorSaveCredentials'),
    detail: saveCredentialsError,
  },
  {
    flag: isAddIntegrationError,
    summary: t('integrations.googleGmail.errorSaveConfig'),
    detail: addIntegrationError,
  },
  {
    flag: isGetAssistantProfileError,
    summary: t('integrations.googleGmail.errorLoadProfile'),
    detail: getAssistantProfileError,
  },
  {
    flag: isGetAuthUrlError,
    summary: t('integrations.googleGmail.errorGetAuthUrl'),
    detail: getAuthUrlError,
  },
  {
    flag: isCheckStatusError,
    summary: t('integrations.googleGmail.errorCheckStatus'),
    detail: checkStatusError,
  },
]

const { toast } = useErrorToast(errorWatchers)

const gmailIntegration = reactive<IntegrationParams>({
  name: 'google_gmail',
  type: 'gmail',
  activated: false,
  config: {
    profile_id: '',
    is_connected: false,
  } as GoogleGmailIntegrationConfig,
})

const connectGoogleGmail = async () => {
  try {
    if (!assistantProfile.value?.id) {
      toast.add({
        severity: 'error',
        summary: t('common.error'),
        detail: t('integrations.googleGmail.errorGetProfileId'),
        life: 3000,
      })
      return
    }

    const config = gmailIntegration.config as GoogleGmailIntegrationConfig
    config.profile_id = assistantProfile.value.id

    const authData = await getAuthorizationUrl(config.profile_id)

    if (authData && authData.authorization_url) {
      openOAuthPopup(authData.authorization_url, async () => {
        await activateAfterOAuth()
      })
    } else {
      toast.add({
        severity: 'error',
        summary: t('common.error'),
        detail: t('integrations.googleGmail.errorGetAuthUrlMsg'),
        life: 3000,
      })
    }
  } catch (error) {
    console.error('Error connecting Google Gmail:', error)
  }
}

const updateIntegration = async () => {
  try {
    await addIntegration(gmailIntegration)
    await getAssistantProfile()
  } catch (error) {
    console.error('Error updating integration:', error)
  }
}

watch(
  () => gmailIntegration.activated,
  async () => {
    await updateIntegration()
  },
)

const searchGmailIntegration = computed(() => {
  return assistantProfile.value?.integrations?.find(
    (integration) => integration.name === 'google_gmail',
  )
})

const checkConnectionStatus = async () => {
  if (!assistantProfile.value?.id) return
  try {
    await checkStatus(assistantProfile.value.id)
  } catch (error) {
    console.error('Error checking connection status:', error)
  }
}

const activateAfterOAuth = async () => {
  if (!assistantProfile.value?.id) return
  await checkStatus(assistantProfile.value.id)
  if (isConnected.value) {
    gmailIntegration.activated = true
    const config = gmailIntegration.config as GoogleGmailIntegrationConfig
    config.profile_id = assistantProfile.value.id
    config.is_connected = true
    await addIntegration(gmailIntegration)
    toast.add({
      severity: 'success',
      summary: t('integrations.googleGmail.connectedSuccess'),
      detail: t('integrations.googleGmail.connectedSuccessDesc'),
      life: 4000,
    })
  }
}

onMounted(async () => {
  await Promise.all([getAssistantProfile(), getCredentials()])

  assistantProfile.value?.integrations?.forEach((integration) => {
    if (integration.name === 'google_gmail') {
      gmailIntegration.activated = integration.activated || false
      const config = gmailIntegration.config as GoogleGmailIntegrationConfig
      const integrationConfig = integration.config as unknown as GoogleGmailIntegrationConfig

      config.profile_id = integrationConfig.profile_id || assistantProfile.value?.id || ''
      config.is_connected = integrationConfig.is_connected || false
    }
  })

  await checkConnectionStatus()

  if (route.query.success === 'true') {
    toast.add({
      severity: 'success',
      summary: t('integrations.googleGmail.connectedSuccess'),
      detail: t('integrations.googleGmail.connectedSuccessDesc'),
      life: 5000,
    })
    await checkConnectionStatus()
    router.replace({ query: {} })
  } else if (route.query.error) {
    const errorMessages: Record<string, string> = {
      invalid_request: t('integrations.googleGmail.invalidRequest'),
      auth_failed: t('integrations.googleGmail.authFailed'),
    }
    const errorDetail =
      errorMessages[route.query.error as string] ||
      t('integrations.googleGmail.connectionErrorDefault')

    toast.add({
      severity: 'error',
      summary: t('integrations.googleGmail.connectionError'),
      detail: errorDetail,
      life: 5000,
    })
    router.replace({ query: {} })
  }
})
</script>

<template>
  <div class="integration-container">
    <!-- Unified header row -->
    <div class="page-header">
      <div class="header-left">
        <div class="icon-wrapper gmail-icon">
          <i class="pi pi-envelope"></i>
        </div>
        <div class="header-text">
          <h1 class="page-title">Gmail</h1>
          <p class="page-subtitle">{{ t('integrations.googleGmail.subtitle') }}</p>
        </div>
      </div>
      <div class="header-toggle">
        <span class="toggle-status" :class="{ active: gmailIntegration.activated }">
          {{ gmailIntegration.activated ? t('integrations.active') : t('integrations.inactive') }}
        </span>
        <InputSwitch v-model="gmailIntegration.activated" />
      </div>
    </div>

    <!-- Step 1 — OAuth credentials -->
    <div class="panel">
      <div class="panel-header">
        <span class="step-badge">1</span>
        <div>
          <p class="panel-title">{{ t('integrations.googleGmail.oauthCredentials') }}</p>
          <p class="panel-subtitle">{{ t('integrations.googleGmail.oauthSubtitle') }}</p>
        </div>
      </div>

      <div class="panel-body">
        <div v-if="savedClientId && !credentialsSaved" class="credentials-saved-notice">
          <i class="pi pi-check-circle"></i>
          {{ t('integrations.googleGmail.credentialsSaved') }} <strong>{{ savedClientId }}</strong>
        </div>

        <div class="field-group">
          <label class="field-label">
            Client ID
            <span class="required">*</span>
          </label>
          <InputText
            v-model="credentials.clientId"
            :placeholder="savedClientId || 'xxxxxxxx.apps.googleusercontent.com'"
            class="w-full"
          />
        </div>

        <div class="field-group">
          <label class="field-label">
            Client Secret
            <span class="required">*</span>
          </label>
          <Password
            v-model="credentials.clientSecret"
            :placeholder="hasSecret ? '••••••••••••• (ya configurado)' : 'GOCSPX-...'"
            class="w-full"
            :feedback="false"
            toggleMask
          />
        </div>

        <div class="field-group">
          <label class="field-label">
            Redirect URI
            <span class="optional">{{ t('integrations.telegram.optional') }}</span>
          </label>
          <InputText
            v-model="credentials.redirectUri"
            :placeholder="savedRedirectUri || 'http://localhost:8000/api/v1/gmail/oauth/callback'"
            class="w-full"
          />
        </div>

        <div class="panel-footer">
          <span v-if="credentialsSaved" class="saved-badge">
            <i class="pi pi-check-circle"></i> {{ t('integrations.googleGmail.saved') }}
          </span>
          <span v-else class="spacer"></span>
          <Button
            :label="t('integrations.googleGmail.saveCredentials')"
            icon="pi pi-save"
            severity="primary"
            :loading="isLoading"
            :disabled="
              (!credentials.clientId && !savedClientId) || (!credentials.clientSecret && !hasSecret)
            "
            @click="handleSaveCredentials"
          />
        </div>
      </div>
    </div>

    <!-- Step 2 — Connect account -->
    <div class="panel" :class="{ 'panel-disabled': !gmailIntegration.activated }">
      <div class="panel-header">
        <span class="step-badge">2</span>
        <div>
          <p class="panel-title">{{ t('integrations.googleGmail.connectAccount') }}</p>
          <p class="panel-subtitle">{{ t('integrations.googleGmail.connectAccountSubtitle') }}</p>
        </div>
      </div>

      <div class="panel-body">
        <!-- Connected state -->
        <div v-if="isConnected" class="connection-state connected">
          <div class="connection-state-icon">
            <i class="pi pi-check-circle"></i>
          </div>
          <div class="connection-state-text">
            <p class="connection-state-title">{{ t('integrations.googleGmail.connected') }}</p>
            <p class="connection-state-subtitle">
              {{ connectedEmail ? connectedEmail : t('integrations.googleGmail.connectedDesc') }}
            </p>
          </div>
        </div>

        <!-- Disconnected state -->
        <div v-else class="connection-state disconnected">
          <div class="connection-state-icon">
            <i class="pi pi-times-circle"></i>
          </div>
          <div class="connection-state-text">
            <p class="connection-state-title">{{ t('integrations.googleGmail.notConnected') }}</p>
            <p class="connection-state-subtitle">
              {{ t('integrations.googleGmail.notConnectedDesc') }}
            </p>
          </div>
        </div>

        <div class="panel-footer">
          <div class="connection-meta">
            <span class="meta-dot" :class="{ 'meta-dot-ok': isConnected }"></span>
            <span class="meta-label">
              {{
                isConnected
                  ? t('integrations.googleGmail.statusConnected')
                  : searchGmailIntegration
                    ? t('integrations.googleGmail.statusConfigured')
                    : t('integrations.googleGmail.statusNoConnection')
              }}
            </span>
          </div>

          <div class="connection-actions">
            <Button
              v-if="!isConnected"
              :label="t('integrations.googleGmail.connectGoogle')"
              icon="pi pi-google"
              severity="primary"
              :disabled="!gmailIntegration.activated"
              @click="connectGoogleGmail"
            />
            <template v-else>
              <Button
                :label="t('integrations.googleGmail.verify')"
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
          <p class="panel-title">{{ t('integrations.googleGmail.capabilities') }}</p>
          <p class="panel-subtitle">{{ t('integrations.googleGmail.capabilitiesSubtitle') }}</p>
        </div>
      </div>

      <div class="capabilities-grid">
        <div class="capability-item">
          <i class="pi pi-inbox capability-icon"></i>
          <span>{{ t('integrations.googleGmail.capReadInbox') }}</span>
        </div>
        <div class="capability-item">
          <i class="pi pi-send capability-icon"></i>
          <span>{{ t('integrations.googleGmail.capSendEmails') }}</span>
        </div>
        <div class="capability-item">
          <i class="pi pi-reply capability-icon"></i>
          <span>{{ t('integrations.googleGmail.capReplyEmails') }}</span>
        </div>
        <div class="capability-item">
          <i class="pi pi-search capability-icon"></i>
          <span>{{ t('integrations.googleGmail.capSearchEmails') }}</span>
        </div>
        <div class="capability-item">
          <i class="pi pi-trash capability-icon"></i>
          <span>{{ t('integrations.googleGmail.capDeleteEmails') }}</span>
        </div>
        <div class="capability-item">
          <i class="pi pi-lock capability-icon"></i>
          <span>{{ t('integrations.googleGmail.capSecureAccess') }}</span>
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
  color: var(--do-blue);
  flex-shrink: 0;
}

.gmail-icon {
  color: #ea4335;
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
