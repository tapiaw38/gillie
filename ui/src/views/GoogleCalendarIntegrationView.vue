<script setup lang="ts">
import type { IntegrationParams, GoogleCalendarIntegrationConfig } from '@/types/assistant'
import { onMounted, reactive, computed, watch, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAssistant } from '@/composables/useAssistant'
import { useCalendar } from '@/composables/useCalendar'
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
} = useCalendar()

const handleDisconnect = async () => {
  await disconnect()
  calendarIntegration.activated = false
  const config = calendarIntegration.config as GoogleCalendarIntegrationConfig
  config.is_connected = false
  toast.add({
    severity: 'info',
    summary: t('integrations.googleCalendar.disconnected'),
    detail: t('integrations.googleCalendar.disconnectedDesc'),
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
      summary: t('integrations.googleCalendar.clientIdRequired'),
      detail: t('integrations.googleCalendar.clientIdRequired'),
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
      summary: t('integrations.googleCalendar.saved'),
      detail: t('integrations.googleCalendar.credentialsSavedMsg'),
      life: 3000,
    })
  } catch {
    // handled by errorWatchers
  }
}

const errorWatchers = [
  {
    flag: isSaveCredentialsError,
    summary: t('integrations.googleCalendar.errorSaveCredentials'),
    detail: saveCredentialsError,
  },
  {
    flag: isAddIntegrationError,
    summary: t('integrations.googleCalendar.errorSaveConfig'),
    detail: addIntegrationError,
  },
  {
    flag: isGetAssistantProfileError,
    summary: t('integrations.googleCalendar.errorLoadProfile'),
    detail: getAssistantProfileError,
  },
  {
    flag: isGetAuthUrlError,
    summary: t('integrations.googleCalendar.errorGetAuthUrl'),
    detail: getAuthUrlError,
  },
  {
    flag: isCheckStatusError,
    summary: t('integrations.googleCalendar.errorCheckStatus'),
    detail: checkStatusError,
  },
]

const { toast } = useErrorToast(errorWatchers)

const calendarIntegration = reactive<IntegrationParams>({
  name: 'google_calendar',
  type: 'calendar',
  activated: false,
  config: {
    profile_id: '',
    is_connected: false,
  } as GoogleCalendarIntegrationConfig,
})

const connectGoogleCalendar = async () => {
  try {
    if (!assistantProfile.value?.id) {
      toast.add({
        severity: 'error',
        summary: t('common.error'),
        detail: t('integrations.googleCalendar.errorGetProfileId'),
        life: 3000,
      })
      return
    }

    const config = calendarIntegration.config as GoogleCalendarIntegrationConfig
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
        detail: t('integrations.googleCalendar.errorGetAuthUrlMsg'),
        life: 3000,
      })
    }
  } catch (error) {
    console.error('Error connecting Google Calendar:', error)
  }
}

const updateIntegration = async () => {
  try {
    await addIntegration(calendarIntegration)
    await getAssistantProfile()
  } catch (error) {
    console.error('Error updating integration:', error)
  }
}

watch(
  () => calendarIntegration.activated,
  async () => {
    await updateIntegration()
  },
)

const searchCalendarIntegration = computed(() => {
  return assistantProfile.value?.integrations?.find(
    (integration) => integration.name === 'google_calendar',
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
    calendarIntegration.activated = true
    const config = calendarIntegration.config as GoogleCalendarIntegrationConfig
    config.profile_id = assistantProfile.value.id
    config.is_connected = true
    await addIntegration(calendarIntegration)
    toast.add({
      severity: 'success',
      summary: t('integrations.googleCalendar.connectedSuccess'),
      detail: t('integrations.googleCalendar.connectedSuccessDesc'),
      life: 4000,
    })
  }
}

onMounted(async () => {
  await Promise.all([getAssistantProfile(), getCredentials()])

  assistantProfile.value?.integrations?.forEach((integration) => {
    if (integration.name === 'google_calendar') {
      calendarIntegration.activated = integration.activated || false
      const config = calendarIntegration.config as GoogleCalendarIntegrationConfig
      const integrationConfig = integration.config as unknown as GoogleCalendarIntegrationConfig

      config.profile_id = integrationConfig.profile_id || assistantProfile.value?.id || ''
      config.is_connected = integrationConfig.is_connected || false
    }
  })

  await checkConnectionStatus()

  if (route.query.success === 'true') {
    toast.add({
      severity: 'success',
      summary: t('integrations.googleCalendar.connectedSuccess'),
      detail: t('integrations.googleCalendar.connectedSuccessDesc'),
      life: 5000,
    })
    await checkConnectionStatus()
    router.replace({ query: {} })
  } else if (route.query.error) {
    const errorMessages: Record<string, string> = {
      invalid_request: t('integrations.googleCalendar.invalidRequest'),
      auth_failed: t('integrations.googleCalendar.authFailed'),
    }
    const errorDetail =
      errorMessages[route.query.error as string] ||
      t('integrations.googleCalendar.connectionErrorDefault')

    toast.add({
      severity: 'error',
      summary: t('integrations.googleCalendar.connectionError'),
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
        <div class="icon-wrapper calendar-icon">
          <i class="pi pi-calendar"></i>
        </div>
        <div class="header-text">
          <h1 class="page-title">Google Calendar</h1>
          <p class="page-subtitle">{{ t('integrations.googleCalendar.subtitle') }}</p>
        </div>
      </div>
      <div class="header-toggle">
        <span class="toggle-status" :class="{ active: calendarIntegration.activated }">
          {{
            calendarIntegration.activated ? t('integrations.active') : t('integrations.inactive')
          }}
        </span>
        <InputSwitch v-model="calendarIntegration.activated" />
      </div>
    </div>

    <!-- Step 1 — OAuth credentials -->
    <div class="panel">
      <div class="panel-header">
        <span class="step-badge">1</span>
        <div>
          <p class="panel-title">{{ t('integrations.googleCalendar.oauthCredentials') }}</p>
          <p class="panel-subtitle">{{ t('integrations.googleCalendar.oauthSubtitle') }}</p>
        </div>
      </div>

      <div class="panel-body">
        <div v-if="savedClientId && !credentialsSaved" class="credentials-saved-notice">
          <i class="pi pi-check-circle"></i>
          {{ t('integrations.googleCalendar.credentialsSaved') }}
          <strong>{{ savedClientId }}</strong>
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
            :placeholder="
              savedRedirectUri || 'http://localhost:8000/api/v1/calendar/oauth/callback'
            "
            class="w-full"
          />
        </div>

        <div class="panel-footer">
          <span v-if="credentialsSaved" class="saved-badge">
            <i class="pi pi-check-circle"></i> {{ t('integrations.googleCalendar.saved') }}
          </span>
          <span v-else class="spacer"></span>
          <Button
            :label="t('integrations.googleCalendar.saveCredentials')"
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
    <div class="panel" :class="{ 'panel-disabled': !calendarIntegration.activated }">
      <div class="panel-header">
        <span class="step-badge">2</span>
        <div>
          <p class="panel-title">{{ t('integrations.googleCalendar.connectAccount') }}</p>
          <p class="panel-subtitle">
            {{ t('integrations.googleCalendar.connectAccountSubtitle') }}
          </p>
        </div>
      </div>

      <div class="panel-body">
        <!-- Connected state -->
        <div v-if="isConnected" class="connection-state connected">
          <div class="connection-state-icon">
            <i class="pi pi-check-circle"></i>
          </div>
          <div class="connection-state-text">
            <p class="connection-state-title">{{ t('integrations.googleCalendar.connected') }}</p>
            <p class="connection-state-subtitle">
              {{ t('integrations.googleCalendar.connectedDesc') }}
            </p>
          </div>
        </div>

        <!-- Disconnected state -->
        <div v-else class="connection-state disconnected">
          <div class="connection-state-icon">
            <i class="pi pi-times-circle"></i>
          </div>
          <div class="connection-state-text">
            <p class="connection-state-title">
              {{ t('integrations.googleCalendar.notConnected') }}
            </p>
            <p class="connection-state-subtitle">
              {{ t('integrations.googleCalendar.notConnectedDesc') }}
            </p>
          </div>
        </div>

        <div class="panel-footer">
          <div class="connection-meta">
            <span class="meta-dot" :class="{ 'meta-dot-ok': isConnected }"></span>
            <span class="meta-label">
              {{
                isConnected
                  ? t('integrations.googleCalendar.statusConnected')
                  : searchCalendarIntegration
                    ? t('integrations.googleCalendar.statusConfigured')
                    : t('integrations.googleCalendar.statusNoConnection')
              }}
            </span>
          </div>

          <div class="connection-actions">
            <Button
              v-if="!isConnected"
              :label="t('integrations.googleCalendar.connectGoogle')"
              icon="pi pi-google"
              severity="primary"
              :disabled="!calendarIntegration.activated"
              @click="connectGoogleCalendar"
            />
            <template v-else>
              <Button
                :label="t('integrations.googleCalendar.verify')"
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
          <p class="panel-title">{{ t('integrations.googleCalendar.capabilities') }}</p>
          <p class="panel-subtitle">{{ t('integrations.googleCalendar.capabilitiesSubtitle') }}</p>
        </div>
      </div>

      <div class="capabilities-grid">
        <div class="capability-item">
          <i class="pi pi-plus-circle capability-icon"></i>
          <span>{{ t('integrations.googleCalendar.createEvents') }}</span>
        </div>
        <div class="capability-item">
          <i class="pi pi-list capability-icon"></i>
          <span>{{ t('integrations.googleCalendar.listEvents') }}</span>
        </div>
        <div class="capability-item">
          <i class="pi pi-pencil capability-icon"></i>
          <span>{{ t('integrations.googleCalendar.updateEvents') }}</span>
        </div>
        <div class="capability-item">
          <i class="pi pi-trash capability-icon"></i>
          <span>{{ t('integrations.googleCalendar.deleteEvents') }}</span>
        </div>
        <div class="capability-item">
          <i class="pi pi-users capability-icon"></i>
          <span>{{ t('integrations.googleCalendar.addAttendees') }}</span>
        </div>
        <div class="capability-item">
          <i class="pi pi-sync capability-icon"></i>
          <span>{{ t('integrations.googleCalendar.autoSync') }}</span>
        </div>
      </div>
    </div>

    <Toast position="top-right" />
  </div>
</template>

<style scoped>
/* ── View-specific styles ────────────────────────────────── */
.calendar-icon {
  color: #4285f4;
}

:deep(.w-full.p-password) {
  width: 100%;
}

:deep(.w-full.p-password .p-inputtext) {
  width: 100%;
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
  .capabilities-grid {
    grid-template-columns: 1fr;
  }
}
</style>
