<script setup lang="ts">
import type { IntegrationParams, GoogleDriveIntegrationConfig } from '@/types/assistant'
import { onMounted, reactive, computed, watch, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAssistant } from '@/composables/useAssistant'
import { useDrive } from '@/composables/useDrive'
import { useOAuthPopup } from '@/composables/useOAuthPopup'
import { useErrorToast } from '@/composables/useErrorToast'
import { useI18n } from 'vue-i18n'
import Toast from 'primevue/toast'
import Button from 'primevue/button'
import Card from 'primevue/card'
import Message from 'primevue/message'
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
  isLoading,
  savedClientId,
  savedRedirectUri,
  hasSecret,
  isSaveCredentialsError,
  saveCredentialsError,
  isGetAuthUrlError,
  getAuthUrlError,
  isCheckStatusError,
  checkStatusError,
} = useDrive()

const handleDisconnect = async () => {
  await disconnect()
  driveIntegration.activated = false
  const config = driveIntegration.config as GoogleDriveIntegrationConfig
  config.is_connected = false
  toast.add({
    severity: 'info',
    summary: t('integrations.googleDrive.disconnected'),
    detail: t('integrations.googleDrive.disconnectedDesc'),
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
      summary: t('integrations.googleDrive.clientIdRequired'),
      detail: t('integrations.googleDrive.clientIdRequired'),
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
      summary: t('integrations.googleDrive.saved'),
      detail: t('integrations.googleDrive.credentialsSavedMsg'),
      life: 3000,
    })
  } catch {
    // handled by errorWatchers
  }
}

const errorWatchers = [
  {
    flag: isSaveCredentialsError,
    summary: t('integrations.googleDrive.errorSaveCredentials'),
    detail: saveCredentialsError,
  },
  {
    flag: isAddIntegrationError,
    summary: t('integrations.googleDrive.errorSaveConfig'),
    detail: addIntegrationError,
  },
  {
    flag: isGetAssistantProfileError,
    summary: t('integrations.googleDrive.errorLoadProfile'),
    detail: getAssistantProfileError,
  },
  {
    flag: isGetAuthUrlError,
    summary: t('integrations.googleDrive.errorGetAuthUrl'),
    detail: getAuthUrlError,
  },
  {
    flag: isCheckStatusError,
    summary: t('integrations.googleDrive.errorCheckStatus'),
    detail: checkStatusError,
  },
]

const { toast } = useErrorToast(errorWatchers)

const driveIntegration = reactive<IntegrationParams>({
  name: 'google_drive',
  type: 'drive',
  activated: false,
  config: {
    profile_id: '',
    is_connected: false,
  } as GoogleDriveIntegrationConfig,
})

const connectGoogleDrive = async () => {
  try {
    if (!assistantProfile.value?.id) {
      toast.add({
        severity: 'error',
        summary: t('common.error'),
        detail: t('integrations.googleDrive.errorGetProfileId'),
        life: 3000,
      })
      return
    }

    const config = driveIntegration.config as GoogleDriveIntegrationConfig
    config.profile_id = assistantProfile.value.id

    // Get authorization URL
    const authData = await getAuthorizationUrl(config.profile_id)

    if (authData && authData.authorization_url) {
      openOAuthPopup(authData.authorization_url, async () => {
        await checkConnectionStatus()
      })
    } else {
      toast.add({
        severity: 'error',
        summary: t('common.error'),
        detail: t('integrations.googleDrive.errorGetAuthUrlMsg'),
        life: 3000,
      })
    }
  } catch (error) {
    console.error('Error al conectar Google Drive:', error)
  }
}

const updateIntegration = async () => {
  try {
    await addIntegration(driveIntegration)
    await getAssistantProfile()
  } catch (error) {
    console.error('Error al actualizar integración:', error)
  }
}

watch(
  () => driveIntegration.activated,
  async () => {
    await updateIntegration()
  },
)

const searchDriveIntegration = computed(() => {
  return assistantProfile.value?.integrations?.find(
    (integration) => integration.name === 'google_drive',
  )
})

const checkConnectionStatus = async () => {
  if (!assistantProfile.value?.id) return

  try {
    const wasConnected = isConnected.value
    await checkStatus(assistantProfile.value.id)
    if (!wasConnected && isConnected.value) {
      // Auto-activate integration when OAuth connection is confirmed
      driveIntegration.activated = true
      const config = driveIntegration.config as GoogleDriveIntegrationConfig
      config.profile_id = assistantProfile.value.id
      config.is_connected = true
      await addIntegration(driveIntegration)
      toast.add({
        severity: 'success',
        summary: t('integrations.googleDrive.connectedSuccess'),
        detail: t('integrations.googleDrive.connectedSuccessDesc'),
        life: 4000,
      })
    }
  } catch (error) {
    console.error('Error al verificar estado de conexión:', error)
  }
}

onMounted(async () => {
  await Promise.all([getAssistantProfile(), getCredentials()])

  assistantProfile.value?.integrations?.forEach((integration) => {
    if (integration.name === 'google_drive') {
      driveIntegration.activated = integration.activated || false
      const config = driveIntegration.config as GoogleDriveIntegrationConfig
      const integrationConfig = integration.config as unknown as GoogleDriveIntegrationConfig

      config.profile_id = integrationConfig.profile_id || assistantProfile.value?.id || ''
      config.is_connected = integrationConfig.is_connected || false
    }
  })

  await checkConnectionStatus()

  if (route.query.success === 'true') {
    toast.add({
      severity: 'success',
      summary: t('integrations.googleDrive.connectedSuccess'),
      detail: t('integrations.googleDrive.connectedSuccessDesc'),
      life: 5000,
    })
    await checkConnectionStatus()
    router.replace({ query: {} })
  } else if (route.query.error) {
    const errorMessages: Record<string, string> = {
      invalid_request: t('integrations.googleDrive.invalidRequest'),
      auth_failed: t('integrations.googleDrive.authFailed'),
    }
    const errorDetail =
      errorMessages[route.query.error as string] ||
      t('integrations.googleDrive.connectionErrorDefault')

    toast.add({
      severity: 'error',
      summary: t('integrations.googleDrive.connectionError'),
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
        <div class="icon-wrapper drive-icon">
          <i class="pi pi-folder-open"></i>
        </div>
        <div class="header-text">
          <h1 class="page-title">Google Drive</h1>
          <p class="page-subtitle">{{ t('integrations.googleDrive.subtitle') }}</p>
        </div>
      </div>
      <div class="header-toggle">
        <span class="toggle-status" :class="{ active: driveIntegration.activated }">
          {{ driveIntegration.activated ? t('integrations.active') : t('integrations.inactive') }}
        </span>
        <InputSwitch v-model="driveIntegration.activated" />
      </div>
    </div>

    <!-- Step 1 — OAuth credentials -->
    <div class="panel">
      <div class="panel-header">
        <span class="step-badge">1</span>
        <div>
          <p class="panel-title">{{ t('integrations.googleDrive.oauthCredentials') }}</p>
          <p class="panel-subtitle">{{ t('integrations.googleDrive.oauthSubtitle') }}</p>
        </div>
      </div>

      <div class="panel-body">
        <div v-if="savedClientId && !credentialsSaved" class="credentials-saved-notice">
          <i class="pi pi-check-circle"></i>
          {{ t('integrations.googleDrive.credentialsSaved') }} <strong>{{ savedClientId }}</strong>
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
            :placeholder="savedRedirectUri || 'http://localhost:8000/api/v1/drive/oauth/callback'"
            class="w-full"
          />
        </div>

        <div class="panel-footer">
          <span v-if="credentialsSaved" class="saved-badge">
            <i class="pi pi-check-circle"></i> {{ t('integrations.googleDrive.saved') }}
          </span>
          <span v-else class="spacer"></span>
          <Button
            :label="t('integrations.googleDrive.saveCredentials')"
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
    <div class="panel" :class="{ 'panel-disabled': !driveIntegration.activated }">
      <div class="panel-header">
        <span class="step-badge">2</span>
        <div>
          <p class="panel-title">{{ t('integrations.googleDrive.connectAccount') }}</p>
          <p class="panel-subtitle">{{ t('integrations.googleDrive.connectAccountSubtitle') }}</p>
        </div>
      </div>

      <div class="panel-body">
        <!-- Connected state -->
        <div v-if="isConnected" class="connection-state connected">
          <div class="connection-state-icon">
            <i class="pi pi-check-circle"></i>
          </div>
          <div class="connection-state-text">
            <p class="connection-state-title">{{ t('integrations.googleDrive.connected') }}</p>
            <p class="connection-state-subtitle">
              {{ t('integrations.googleDrive.connectedDesc') }}
            </p>
          </div>
        </div>

        <!-- Disconnected state -->
        <div v-else class="connection-state disconnected">
          <div class="connection-state-icon">
            <i class="pi pi-times-circle"></i>
          </div>
          <div class="connection-state-text">
            <p class="connection-state-title">{{ t('integrations.googleDrive.notConnected') }}</p>
            <p class="connection-state-subtitle">
              {{ t('integrations.googleDrive.notConnectedDesc') }}
            </p>
          </div>
        </div>

        <div class="panel-footer">
          <div class="connection-meta">
            <span class="meta-dot" :class="{ 'meta-dot-ok': isConnected }"></span>
            <span class="meta-label">
              {{
                isConnected
                  ? t('integrations.googleDrive.statusConnected')
                  : searchDriveIntegration
                    ? t('integrations.googleDrive.statusConfigured')
                    : t('integrations.googleDrive.statusNoConnection')
              }}
            </span>
          </div>

          <div class="connection-actions">
            <Button
              v-if="!isConnected"
              :label="t('integrations.googleDrive.connectGoogle')"
              icon="pi pi-google"
              severity="primary"
              :disabled="!driveIntegration.activated"
              @click="connectGoogleDrive"
            />
            <template v-else>
              <Button
                :label="t('integrations.googleDrive.verify')"
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
              <Button
                :label="t('integrations.googleDrive.viewFiles')"
                icon="pi pi-folder-open"
                severity="info"
                @click="$router.push('/drive/files')"
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
          <p class="panel-title">{{ t('integrations.googleDrive.capabilities') }}</p>
          <p class="panel-subtitle">{{ t('integrations.googleDrive.capabilitiesSubtitle') }}</p>
        </div>
      </div>

      <div class="capabilities-grid">
        <div class="capability-item">
          <i class="pi pi-file-pdf capability-icon"></i>
          <span>{{ t('integrations.googleDrive.capReadDocs') }}</span>
        </div>
        <div class="capability-item">
          <i class="pi pi-search capability-icon"></i>
          <span>{{ t('integrations.googleDrive.capSearchFiles') }}</span>
        </div>
        <div class="capability-item">
          <i class="pi pi-database capability-icon"></i>
          <span>{{ t('integrations.googleDrive.capIndexDocs') }}</span>
        </div>
        <div class="capability-item">
          <i class="pi pi-folder capability-icon"></i>
          <span>{{ t('integrations.googleDrive.capListFiles') }}</span>
        </div>
        <div class="capability-item">
          <i class="pi pi-sync capability-icon"></i>
          <span>{{ t('integrations.googleDrive.capSyncDrive') }}</span>
        </div>
        <div class="capability-item">
          <i class="pi pi-shield capability-icon"></i>
          <span>{{ t('integrations.googleDrive.capSecureAccess') }}</span>
        </div>
      </div>

      <div class="formats-row">
        <span class="formats-label">{{ t('integrations.googleDrive.supportedFormats') }}</span>
        <span class="format-tag">Docs</span>
        <span class="format-tag">Sheets</span>
        <span class="format-tag">PDF</span>
        <span class="format-tag">Images</span>
        <span class="format-tag">{{ t('integrations.googleDrive.formatMore') }}</span>
      </div>
    </div>

    <Toast position="top-right" />
  </div>
</template>

<style scoped>
/* ── Layout ─────────────────────────────────────────────── */
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

/* ── Page header ─────────────────────────────────────────── */
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
  flex-shrink: 0;
  width: 3rem;
  height: 3rem;
  border-radius: 0.75rem;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.4rem;
  color: #fff;
}

.drive-icon {
  background: linear-gradient(135deg, #1a73e8 0%, #0d47a1 100%);
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

/* ── Panel ───────────────────────────────────────────────── */
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

/* ── Form fields ─────────────────────────────────────────── */
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

/* ── Credentials saved notice ────────────────────────────── */
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

/* ── Connection state ────────────────────────────────────── */
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

/* ── Connection footer ───────────────────────────────────── */
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

/* ── Capabilities grid ───────────────────────────────────── */
.capabilities-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.625rem;
  padding: 1.25rem 1.25rem 0;
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

/* ── Formats row ─────────────────────────────────────────── */
.formats-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.5rem;
  padding: 1rem 1.25rem 1.25rem;
}

.formats-label {
  font-size: 0.8rem;
  color: var(--do-text-muted);
  font-weight: 600;
  margin-right: 0.25rem;
}

.format-tag {
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--do-text-muted);
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--do-border-light);
  border-radius: 0.4rem;
  padding: 0.2rem 0.55rem;
}

/* ── Responsive ──────────────────────────────────────────── */
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
