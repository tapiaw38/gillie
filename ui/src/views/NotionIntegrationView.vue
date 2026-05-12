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

const searchNotionIntegration = computed(() =>
  assistantProfile.value?.integrations?.find((integration) => integration.name === 'notion'),
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

  if (assistantProfile.value?.id) {
    await checkStatus(assistantProfile.value.id)
  }

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
            :placeholder="savedClientId || 'secret_xxxxxxxxx'"
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
            :placeholder="hasSecret ? '••••••••••••' : t('integrations.notion.clientSecretPlaceholder')"
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

        <Button
          :label="t('integrations.notion.saveCredentials')"
          icon="pi pi-save"
          :loading="isLoading"
          @click="handleSaveCredentials"
        />
      </div>
    </div>

    <div class="panel">
      <div class="panel-header">
        <span class="step-badge">2</span>
        <div>
          <p class="panel-title">{{ t('integrations.notion.connectAccount') }}</p>
          <p class="panel-subtitle">{{ t('integrations.notion.connectAccountSubtitle') }}</p>
        </div>
      </div>

      <div class="panel-body">
        <div v-if="isConnected" class="connection-state connected">
          <p class="connection-state-title">{{ t('integrations.notion.connected') }}</p>
          <p class="connection-state-subtitle">
            {{ workspaceName || ownerName || t('integrations.notion.connectedDesc') }}
          </p>
        </div>
        <div v-else class="connection-state disconnected">
          <p class="connection-state-title">{{ t('integrations.notion.notConnected') }}</p>
          <p class="connection-state-subtitle">{{ t('integrations.notion.notConnectedDesc') }}</p>
        </div>

        <div class="button-row">
          <Button
            :label="t('integrations.notion.connectNotion')"
            icon="pi pi-link"
            @click="connectNotion"
          />
          <Button
            :label="t('integrations.notion.verify')"
            icon="pi pi-sync"
            severity="secondary"
            @click="assistantProfile?.id && checkStatus(assistantProfile.id)"
          />
          <Button
            :label="t('integrations.disconnect')"
            icon="pi pi-times"
            severity="contrast"
            outlined
            @click="handleDisconnect"
          />
        </div>
      </div>
    </div>

    <div class="panel">
      <div class="panel-header">
        <span class="step-badge">3</span>
        <div>
          <p class="panel-title">{{ t('integrations.notion.capabilities') }}</p>
          <p class="panel-subtitle">{{ t('integrations.notion.capabilitiesSubtitle') }}</p>
        </div>
      </div>
      <div class="panel-body">
        <ul class="capabilities-list">
          <li>{{ t('integrations.notion.capSearchPages') }}</li>
          <li>{{ t('integrations.notion.capReadPages') }}</li>
          <li>{{ t('integrations.notion.capReadBlocks') }}</li>
          <li>{{ t('integrations.notion.capSecureAccess') }}</li>
        </ul>
      </div>
    </div>

    <Toast />
  </div>
</template>

<style scoped>
.notion-icon {
  background: linear-gradient(135deg, #111827, #0f172a);
  color: #fff;
}

.capabilities-list {
  margin: 0;
  padding-left: 1rem;
}
</style>
