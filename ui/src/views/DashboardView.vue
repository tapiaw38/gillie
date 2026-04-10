<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch, inject } from 'vue'
import ToggleSwitch from 'primevue/toggleswitch'
import Card from 'primevue/card'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import LoadingSpinner from '@/components/core/LoadingSpinner/LoadingSpinner.vue'
import DefaultModal from '@/components/core/shared/DefaultModal/DefaultModal.vue'
import Toast from 'primevue/toast'
import type { AssistantProfileParams, ProviderOption } from '@/types/assistant.ts'
import { useToogle } from '@/composables/useToogle'
import { useAssistant } from '@/composables/useAssistant'
import { useConversation } from '@/composables/useConversation'
import { useErrorToast } from '@/composables/useErrorToast'
import { useI18n } from 'vue-i18n'
import type { IAssistantService } from '@/services/assistant/assistantService'

type IntegrationItem = {
  name: string
  description: string
  icon: string
  tone: string
  to: string
  enabled: boolean
}

type SkillGroup = {
  id: string
  name: string
  icon: string
  tone: string
  items: IntegrationItem[]
}

const { t } = useI18n()

const { toogleValue: isVisible } = useToogle(false)

const {
  conversations,
  getUserConversation,
  isGetUserConversationError,
  isGetUserConversationSuccess,
  getUserConversationError,
} = useConversation()

const {
  addAssistantProfile,
  getAssistantProfile,
  updateAssistantProfile,

  isAddAssistantProfilePending,
  isAddAssistantProfileSuccess,
  isAddAssistantProfileError,
  addAssistantProfileError,

  isGetAssistantProfileSuccess,
  isGetAssistantProfileError,
  getAssistantProfileError,
  isGetAssistantProfilePending,

  isUpdateAssistantProfilePending,
  isUpdateAssistantProfileSuccess,
  isUpdateAssistantProfileError,
  updateAssistantProfileError,

  assistantProfile,
} = useAssistant()

const services = inject<{ assistantService: IAssistantService }>('services')

const ttsEnabled = computed(() => assistantProfile.value?.tts_enabled ?? false)
const responseLang = ref<'en' | 'es'>('en')

const providerOptions = ref<ProviderOption[]>([])
const aiProvider = ref<string>('')
const pendingApiKey = ref<string>('')
const showApiKeyInput = ref(false)
const pendingProvider = ref<string>('')
const pendingProviderHasKey = computed(() =>
  providerOptions.value.find((x) => x.key === pendingProvider.value)?.api_key_set ?? false,
)

const showAddProvider = ref(false)
const newProvider = reactive({
  name: '',
  base_url: '',
  model: '',
  auth_type: 'api_key',
  api_key: '',
})

watch(
  () => assistantProfile.value?.response_language,
  (lang) => {
    if (lang === 'en' || lang === 'es') responseLang.value = lang
  },
  { immediate: true },
)

const toggleTts = async (value: boolean) => {
  try {
    await updateAssistantProfile({ tts_enabled: value })
    toast.add({
      severity: 'success',
      summary: value ? t('dashboard.audioEnabled') : t('dashboard.audioDisabled'),
      life: 2000,
    })
  } catch {
    toast.add({ severity: 'error', summary: t('dashboard.errorAudio'), life: 3000 })
  }
}

const onProviderSelect = (key: string) => {
  if (!key) {
    applyProvider(key)
    return
  }
  const p = providerOptions.value.find((x) => x.key === key)
  if (p && p.auth_type !== 'none' && !p.api_key_set) {
    pendingProvider.value = key
    pendingApiKey.value = ''
    showApiKeyInput.value = true
  } else {
    applyProvider(key)
  }
}

const openUpdateKeyInput = () => {
  const key = aiProvider.value
  if (!key) return
  pendingProvider.value = key
  pendingApiKey.value = ''
  showApiKeyInput.value = true
}

const applyProvider = async (key: string, apiKey?: string) => {
  const prev = aiProvider.value
  aiProvider.value = key
  showApiKeyInput.value = false
  try {
    await services!.assistantService.setProvider(key, apiKey)
    if (apiKey) {
      const p = providerOptions.value.find((x) => x.key === key)
      if (p) p.api_key_set = true
    }
    toast.add({ severity: 'success', summary: t('dashboard.aiModelUpdated'), life: 2000 })
  } catch {
    aiProvider.value = prev
    toast.add({ severity: 'error', summary: t('dashboard.errorAiModel'), life: 3000 })
  }
}

const submitApiKey = () => {
  if (!pendingApiKey.value.trim()) return
  applyProvider(pendingProvider.value, pendingApiKey.value.trim())
}

const cancelApiKey = () => {
  showApiKeyInput.value = false
  pendingProvider.value = ''
  pendingApiKey.value = ''
}

const submitNewProvider = async () => {
  if (!newProvider.name || !newProvider.base_url || !newProvider.model) return
  try {
    await services!.assistantService.addProvider({ ...newProvider })
    const opts = await services!.assistantService.getOptions()
    providerOptions.value = opts.data.providers ?? []
    showAddProvider.value = false
    Object.assign(newProvider, {
      name: '',
      base_url: '',
      model: '',
      auth_type: 'api_key',
      api_key: '',
    })
    toast.add({ severity: 'success', summary: t('dashboard.providerAdded'), life: 2000 })
  } catch {
    toast.add({ severity: 'error', summary: t('dashboard.errorAiModel'), life: 3000 })
  }
}

const setResponseLanguage = async (lang: 'en' | 'es') => {
  const prev = responseLang.value
  responseLang.value = lang
  try {
    await updateAssistantProfile({ response_language: lang })
    toast.add({
      severity: 'success',
      summary: t('myAccount.configSaved'),
      detail: lang === 'en' ? t('myAccount.langSetEn') : t('myAccount.langSetEs'),
      life: 2000,
    })
  } catch {
    responseLang.value = prev
    toast.add({ severity: 'error', summary: t('dashboard.errorAudio'), life: 3000 })
  }
}

const errorWatchers = [
  {
    flag: isAddAssistantProfileError,
    summary: t('dashboard.errorAddAssistant'),
    detail: addAssistantProfileError,
  },
  {
    flag: isUpdateAssistantProfileError,
    summary: t('dashboard.errorUpdateAssistant'),
    detail: updateAssistantProfileError,
  },
  {
    flag: isGetAssistantProfileError,
    summary: t('dashboard.errorGetProfile'),
    detail: getAssistantProfileError,
  },
  {
    flag: isGetUserConversationError,
    summary: t('dashboard.errorGetConversations'),
    detail: getUserConversationError,
  },
]

const { toast } = useErrorToast(errorWatchers)

onMounted(async () => {
  try {
    await getAssistantProfile()
    if (isGetAssistantProfileSuccess.value) {
      await getUserConversation()
    }
    if (services?.assistantService) {
      const opts = await services.assistantService.getOptions()
      providerOptions.value = opts.data.providers ?? []
      aiProvider.value = opts.data.active_provider ?? ''
    }
  } catch (error) {
    console.error('Error loading dashboard data:', error)
  }
})

const modalTitle = computed(() => t('dashboard.modalTitle'))
const changeVisible = (value: boolean) => {
  isVisible.value = value
}

const assistantProfileParams = reactive<AssistantProfileParams>({
  assistant_name: '',
  functions: '',
})

const addAssistant = async () => {
  await addAssistantProfile(assistantProfileParams)
  if (isAddAssistantProfileSuccess.value) {
    await getAssistantProfile()
    toast.add({
      severity: 'success',
      summary: t('dashboard.assistantAdded'),
      detail: t('dashboard.assistantAddedDesc'),
      life: 3000,
    })
  }
  isVisible.value = false
}

const isEditingName = ref(false)
const editingNameValue = ref('')

const startEditName = () => {
  editingNameValue.value = assistantProfile.value?.assistant_name || ''
  isEditingName.value = true
}

const saveEditName = async () => {
  const trimmed = editingNameValue.value.trim()
  if (!trimmed || trimmed === assistantProfile.value?.assistant_name) {
    isEditingName.value = false
    return
  }
  await updateAssistantProfile({ assistant_name: trimmed })
  if (isUpdateAssistantProfileSuccess.value) {
    await getAssistantProfile()
    toast.add({ severity: 'success', summary: t('dashboard.nameUpdated'), life: 2000 })
  }
  isEditingName.value = false
}

const cancelEditName = () => {
  isEditingName.value = false
}

const totalMessagesInConversation = computed(() => {
  return conversations.value?.reduce((acc, curr) => {
    return acc + (curr?.messages?.length || 0)
  }, 0)
})

const integrations = computed<IntegrationItem[]>(() => [
  {
    name: t('dashboard.integrations.storage.name'),
    description: t('dashboard.integrations.storage.description'),
    icon: 'pi pi-file',
    tone: 'primary',
    to: 'store-integration',
    enabled: true,
  },
  {
    name: t('dashboard.integrations.whatsapp.name'),
    description: t('dashboard.integrations.whatsapp.description'),
    icon: 'pi pi-whatsapp',
    tone: 'success',
    to: 'whatsapp-integration',
    enabled: true,
  },
  {
    name: t('dashboard.integrations.whatsappDevices.name'),
    description: t('dashboard.integrations.whatsappDevices.description'),
    icon: 'pi pi-whatsapp',
    tone: 'success',
    to: 'whatsapp-devices',
    enabled: true,
  },
  {
    name: t('dashboard.integrations.googleCalendar.name'),
    description: t('dashboard.integrations.googleCalendar.description'),
    icon: 'pi pi-calendar',
    tone: 'warning',
    to: 'google-calendar-integration',
    enabled: true,
  },
  {
    name: t('dashboard.integrations.googleDrive.name'),
    description: t('dashboard.integrations.googleDrive.description'),
    icon: 'pi pi-folder-open',
    tone: 'info',
    to: 'google-drive-integration',
    enabled: true,
  },
  {
    name: t('dashboard.integrations.googleGmail.name'),
    description: t('dashboard.integrations.googleGmail.description'),
    icon: 'pi pi-envelope',
    tone: 'danger',
    to: 'google-gmail-integration',
    enabled: true,
  },
  {
    name: t('dashboard.integrations.sqlDatabase.name'),
    description: t('dashboard.integrations.sqlDatabase.description'),
    icon: 'pi pi-database',
    tone: 'info',
    to: 'sqldatabase-integration',
    enabled: true,
  },
  {
    name: t('dashboard.integrations.slack.name'),
    description: t('dashboard.integrations.slack.description'),
    icon: 'pi pi-slack',
    tone: 'primary',
    to: 'slack-integration',
    enabled: true,
  },
  {
    name: t('dashboard.integrations.telegram.name'),
    description: t('dashboard.integrations.telegram.description'),
    icon: 'pi pi-send',
    tone: 'info',
    to: 'telegram-integration',
    enabled: true,
  },
  {
    name: t('dashboard.integrations.systemCommands.name'),
    description: t('dashboard.integrations.systemCommands.description'),
    icon: 'pi pi-server',
    tone: 'danger',
    to: 'system-commands',
    enabled: true,
  },
  {
    name: t('dashboard.integrations.cronJobs.name'),
    description: t('dashboard.integrations.cronJobs.description'),
    icon: 'pi pi-clock',
    tone: 'warning',
    to: 'cron-jobs',
    enabled: true,
  },
  {
    name: t('dashboard.integrations.toolPrompts.name'),
    description: t('dashboard.integrations.toolPrompts.description'),
    icon: 'pi pi-sliders-h',
    tone: 'primary',
    to: 'tool-prompts',
    enabled: true,
  },
  {
    name: t('dashboard.integrations.functions.name'),
    description: t('dashboard.integrations.functions.description'),
    icon: 'pi pi-code',
    tone: 'primary',
    to: 'functions',
    enabled: true,
  },
  {
    name: t('dashboard.integrations.apiKeys.name'),
    description: t('dashboard.integrations.apiKeys.description'),
    icon: 'pi pi-key',
    tone: 'warning',
    to: 'my-account',
    enabled: true,
  },
])

const openGroups = ref(new Set<string>())
const toggleGroup = (id: string) => {
  if (openGroups.value.has(id)) {
    openGroups.value.delete(id)
    openGroups.value = new Set(openGroups.value)
  } else {
    openGroups.value = new Set([...openGroups.value, id])
  }
}

const MESSAGING_ROUTES = [
  'whatsapp-integration',
  'whatsapp-devices',
  'slack-integration',
  'telegram-integration',
]
const PRODUCTIVITY_ROUTES = [
  'google-calendar-integration',
  'google-drive-integration',
  'google-gmail-integration',
  'store-integration',
  'sqldatabase-integration',
]
const AUTOMATION_ROUTES = [
  'system-commands',
  'cron-jobs',
  'tool-prompts',
  'functions',
  'my-account',
]

const skillGroups = computed<SkillGroup[]>(() => [
  {
    id: 'messaging',
    name: t('dashboard.skillGroups.messaging'),
    icon: 'pi pi-comments',
    tone: 'success',
    items: integrations.value.filter((i: IntegrationItem) => MESSAGING_ROUTES.includes(i.to)),
  },
  {
    id: 'productivity',
    name: t('dashboard.skillGroups.productivity'),
    icon: 'pi pi-briefcase',
    tone: 'info',
    items: integrations.value.filter((i: IntegrationItem) => PRODUCTIVITY_ROUTES.includes(i.to)),
  },
  {
    id: 'automation',
    name: t('dashboard.skillGroups.automation'),
    icon: 'pi pi-cog',
    tone: 'warning',
    items: integrations.value.filter((i: IntegrationItem) => AUTOMATION_ROUTES.includes(i.to)),
  },
])
</script>

<template>
  <div class="dashboard-container">
    <!-- Header Section -->
    <div class="dashboard-header">
      <div class="header-content">
        <div class="icon-wrapper">
          <i class="pi pi-th-large"></i>
        </div>
        <div class="title-section">
          <h1 class="dashboard-title">{{ t('dashboard.title') }}</h1>
          <p class="dashboard-subtitle">{{ t('dashboard.subtitle') }}</p>
        </div>
      </div>
    </div>

    <!-- Main Content Grid -->
    <div class="content-grid">
      <!-- Assistant Profile Section -->
      <div class="profile-section">
        <!-- Loading State -->
        <div v-if="isGetAssistantProfilePending" class="loading-card">
          <Card>
            <template #content>
              <div class="loading-state">
                <LoadingSpinner />
                <p>{{ t('dashboard.loadingProfile') }}</p>
              </div>
            </template>
          </Card>
        </div>

        <!-- No Assistant State -->
        <div v-else-if="!assistantProfile" class="empty-card">
          <Card>
            <template #content>
              <div class="empty-state">
                <i class="pi pi-robot"></i>
                <h3>{{ t('dashboard.noAssistant') }}</h3>
                <p>{{ t('dashboard.noAssistantDesc') }}</p>
                <Button
                  :label="t('dashboard.createAssistant')"
                  icon="pi pi-plus"
                  class="create-button"
                  @click="isVisible = true"
                />
              </div>
            </template>
          </Card>
        </div>

        <!-- Assistant Profile Card -->
        <Card v-else class="profile-card p-2">
          <template #header>
            <div class="profile-header">
              <div class="profile-info">
                <div class="profile-icon">
                  <i class="pi pi-sparkles"></i>
                </div>
                <div class="profile-details">
                  <div v-if="isEditingName" class="name-edit">
                    <InputText
                      v-model="editingNameValue"
                      size="small"
                      autofocus
                      @keyup.enter="saveEditName"
                      @keyup.escape="cancelEditName"
                      @blur="saveEditName"
                    />
                    <i
                      v-if="isUpdateAssistantProfilePending"
                      class="pi pi-spin pi-spinner name-edit-spinner"
                    />
                  </div>
                  <h3
                    v-else
                    class="name-clickable"
                    @click="startEditName"
                    :title="t('dashboard.clickToEdit')"
                  >
                    {{ assistantProfile?.assistant_name }}
                    <i class="pi pi-pencil name-pencil-icon" />
                  </h3>
                  <p>{{ t('dashboard.virtualAssistant') }}</p>
                </div>
              </div>
            </div>
          </template>
          <template #content>
            <div class="profile-content">
              <div class="tts-row">
                <div class="tts-info">
                  <i class="pi pi-volume-up tts-icon"></i>
                  <span class="tts-label">{{ t('dashboard.audioResponses') }}</span>
                </div>
                <ToggleSwitch :modelValue="ttsEnabled" @update:modelValue="toggleTts" />
              </div>

              <div class="tts-row">
                <div class="tts-info">
                  <i class="pi pi-language tts-icon"></i>
                  <span class="tts-label">{{ t('myAccount.responseLanguage') }}</span>
                </div>
                <div class="lang-toggle">
                  <button
                    class="lang-opt"
                    :class="{ 'lang-opt--active': responseLang === 'en' }"
                    :disabled="isUpdateAssistantProfilePending"
                    @click="setResponseLanguage('en')"
                  >
                    EN
                  </button>
                  <button
                    class="lang-opt"
                    :class="{ 'lang-opt--active': responseLang === 'es' }"
                    :disabled="isUpdateAssistantProfilePending"
                    @click="setResponseLanguage('es')"
                  >
                    ES
                  </button>
                </div>
              </div>

              <div class="tts-row">
                <div class="tts-info">
                  <i class="pi pi-microchip-ai tts-icon"></i>
                  <span class="tts-label">{{ t('dashboard.aiModel') }}</span>
                </div>
                <div class="provider-select-row">
                  <select
                    class="provider-select"
                    :value="aiProvider"
                    :disabled="isUpdateAssistantProfilePending"
                    @change="onProviderSelect(($event.target as HTMLSelectElement).value)"
                  >
                    <option value="">{{ t('dashboard.aiModelDefault') }}</option>
                    <option v-for="p in providerOptions" :key="p.key" :value="p.key">
                      {{ p.key }} — {{ p.model }}
                    </option>
                  </select>
                  <button
                    v-if="aiProvider && providerOptions.find((p) => p.key === aiProvider)?.auth_type !== 'none'"
                    type="button"
                    class="add-provider-toggle"
                    :title="t('dashboard.updateProviderKey')"
                    @click="openUpdateKeyInput"
                  >
                    <i class="pi pi-key"></i>
                  </button>
                  <button
                    type="button"
                    class="add-provider-toggle"
                    :title="t('dashboard.addProvider')"
                    @click="showAddProvider = !showAddProvider"
                  >
                    <i :class="showAddProvider ? 'pi pi-times' : 'pi pi-plus-circle'"></i>
                  </button>
                </div>
              </div>

              <!-- API Key input -->
              <div v-if="showApiKeyInput" class="tts-row provider-apikey-row">
                <div class="tts-info">
                  <i class="pi pi-key tts-icon"></i>
                  <span class="tts-label"
                    >{{ t('dashboard.providerApiKey') }} ({{ pendingProvider }})</span
                  >
                </div>
                <div class="provider-apikey-actions">
                  <InputText
                    v-model="pendingApiKey"
                    size="small"
                    :placeholder="pendingProviderHasKey ? t('dashboard.providerApiKeyKeepPlaceholder') : t('dashboard.providerApiKeyPlaceholder')"
                    type="password"
                    @keyup.enter="submitApiKey"
                    @keyup.escape="cancelApiKey"
                  />
                  <Button
                    icon="pi pi-check"
                    size="small"
                    severity="success"
                    :disabled="!pendingProviderHasKey && !pendingApiKey.trim()"
                    @click="submitApiKey"
                  />
                  <Button
                    icon="pi pi-times"
                    size="small"
                    severity="secondary"
                    @click="cancelApiKey"
                  />
                </div>
              </div>

              <!-- Add custom provider form -->
              <div v-if="showAddProvider" class="add-provider-form">
                <div class="add-provider-fields">
                  <InputText
                    v-model="newProvider.name"
                    size="small"
                    :placeholder="t('dashboard.providerName')"
                  />
                  <InputText
                    v-model="newProvider.base_url"
                    size="small"
                    :placeholder="t('dashboard.providerBaseUrl')"
                  />
                  <InputText
                    v-model="newProvider.model"
                    size="small"
                    :placeholder="t('dashboard.providerModel')"
                  />
                  <InputText
                    v-model="newProvider.api_key"
                    size="small"
                    :placeholder="t('dashboard.providerApiKeyPlaceholder')"
                    type="password"
                  />
                </div>
                <div class="add-provider-actions">
                  <Button
                    :label="t('dashboard.applyProvider')"
                    size="small"
                    :disabled="!newProvider.name || !newProvider.base_url || !newProvider.model"
                    @click="submitNewProvider"
                  />
                  <Button
                    :label="t('common.cancel')"
                    size="small"
                    severity="secondary"
                    @click="showAddProvider = false"
                  />
                </div>
              </div>
            </div>
          </template>
        </Card>

        <!-- Quick Access Card -->
        <Card v-if="assistantProfile" class="quick-access-card">
          <template #header>
            <div class="quick-access-header">
              <div class="quick-access-icon"><i class="pi pi-comments"></i></div>
              <div>
                <h3>{{ t('dashboard.chat') }}</h3>
                <p>{{ t('dashboard.chatDesc') }}</p>
              </div>
            </div>
          </template>
          <template #content>
            <div class="quick-access-actions">
              <RouterLink class="qa-btn qa-btn--primary" :to="{ name: 'sandbox' }">
                <i class="pi pi-comment"></i>
                <div>
                  <span class="qa-btn-label">Chat UI</span>
                  <span class="qa-btn-desc">{{ t('dashboard.chatUIDesc') }}</span>
                </div>
              </RouterLink>
              <RouterLink class="qa-btn qa-btn--secondary" :to="{ name: 'conversation' }">
                <i class="pi pi-list"></i>
                <div>
                  <span class="qa-btn-label">{{ t('dashboard.conversations') }}</span>
                  <span class="qa-btn-desc">{{ t('dashboard.conversationsDesc') }}</span>
                </div>
              </RouterLink>
            </div>
          </template>
        </Card>

        <!-- Skills Section -->
        <div class="skills-section">
          <div class="section-header">
            <h2>{{ t('dashboard.availableSkills') }}</h2>
            <p>{{ t('dashboard.skillsDesc') }}</p>
          </div>

          <div class="skill-groups">
            <div v-for="group in skillGroups" :key="group.id" class="skill-group">
              <button
                type="button"
                class="skill-group-header"
                :class="{ 'is-open': openGroups.has(group.id) }"
                @click="toggleGroup(group.id)"
              >
                <div class="skill-group-title">
                  <div class="skill-group-icon" :class="`tone-${group.tone}`">
                    <i :class="group.icon"></i>
                  </div>
                  <span class="skill-group-name">{{ group.name }}</span>
                  <span class="skill-group-count">{{ group.items.length }}</span>
                </div>
                <i
                  class="pi pi-chevron-down skill-chevron"
                  :class="{ 'is-rotated': openGroups.has(group.id) }"
                ></i>
              </button>

              <div v-show="openGroups.has(group.id)" class="skill-group-content">
                <div class="integrations-grid">
                  <button
                    v-for="integration in group.items"
                    :key="integration.name"
                    type="button"
                    class="integration-button"
                    :class="{ 'is-disabled': !integration.enabled }"
                    :disabled="!integration.enabled"
                    @click="integration.enabled && $router.push({ name: integration.to })"
                  >
                    <div class="integration-content">
                      <div class="integration-main">
                        <div
                          class="integration-icon"
                          :class="integration.enabled ? `tone-${integration.tone}` : 'disabled'"
                        >
                          <i :class="integration.icon"></i>
                        </div>
                        <div class="integration-info">
                          <h3>{{ integration.name }}</h3>
                        </div>
                      </div>

                      <div class="integration-actions">
                        <span v-if="integration.enabled" class="integration-action-label">{{
                          t('common.configure')
                        }}</span>
                        <span v-else class="integration-action-label">{{
                          t('common.comingSoon')
                        }}</span>
                      </div>

                      <div class="integration-legend">{{ integration.description }}</div>
                    </div>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Stats Card (moved down) -->
      <Card v-if="isGetUserConversationSuccess" class="stats-card p-2">
        <template #header>
          <div class="stats-header">
            <div class="stats-icon">
              <i class="pi pi-chart-bar"></i>
            </div>
            <div class="stats-info">
              <h3>{{ t('dashboard.stats') }}</h3>
              <p>{{ t('dashboard.statsDesc') }}</p>
            </div>
          </div>
        </template>
        <template #content>
          <div class="stats-grid">
            <div class="stat-item">
              <div class="stat-value">{{ conversations?.length || 0 }}</div>
              <div class="stat-label">{{ t('dashboard.conversations') }}</div>
              <div class="stat-icon">
                <i class="pi pi-comments"></i>
              </div>
            </div>
            <div class="stat-item">
              <div class="stat-value">{{ totalMessagesInConversation || 0 }}</div>
              <div class="stat-label">{{ t('common.messages') }}</div>
              <div class="stat-icon">
                <i class="pi pi-envelope"></i>
              </div>
            </div>
            <div class="stat-item">
              <div class="stat-value">{{ assistantProfile?.iteration_limit || 0 }}</div>
              <div class="stat-label">{{ t('dashboard.remainingIterations') }}</div>
              <div class="stat-icon">
                <i class="pi pi-clock"></i>
              </div>
            </div>
          </div>
          <div class="stats-actions">
            <RouterLink class="view-conversations-button" :to="{ name: 'conversation' }">
              <i class="pi pi-eye"></i>
              {{ t('dashboard.viewConversations') }}
            </RouterLink>
          </div>
        </template>
      </Card>
    </div>

    <!-- Modals -->
    <DefaultModal :isVisible="isVisible" :title="modalTitle" @update:visible="changeVisible">
      <form @submit.prevent="addAssistant" class="modal-form">
        <div class="form-field">
          <label for="assistant_name">{{ t('dashboard.assistantName') }}</label>
          <InputText
            id="assistant_name"
            v-model="assistantProfileParams.assistant_name"
            :placeholder="t('dashboard.assistantNamePlaceholder')"
            required
          />
        </div>

        <div class="modal-actions">
          <Button
            type="button"
            :label="t('common.cancel')"
            severity="secondary"
            @click="() => changeVisible(false)"
          />
          <Button
            type="submit"
            :label="t('dashboard.createAssistant')"
            :loading="isAddAssistantProfilePending"
          />
        </div>
      </form>
    </DefaultModal>
  </div>

  <Toast />
</template>

<style scoped>
/* Dashboard Container */
.dashboard-container {
  padding: 1rem;
  padding-top: calc(3.25rem + 0.9rem);
  min-height: 100vh;
  background: var(--do-bg);
}

/* Header Section */
.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: rgba(255, 255, 255, 0.03);
  padding: 0.85rem 1rem;
  border-radius: 0.75rem;
  box-shadow: none;
  border: 1px solid rgba(255, 255, 255, 0.07);
  margin-bottom: 1rem;
}

.header-content {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.icon-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 2rem;
  color: var(--do-blue);
  flex-shrink: 0;
}

.title-section {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.dashboard-title {
  font-size: 1.35rem;
  font-weight: 800;
  color: var(--do-text);
  margin: 0;
  line-height: 1.2;
}

.dashboard-subtitle {
  font-size: 0.85rem;
  color: var(--do-text-secondary);
  margin: 0;
  line-height: 1.5;
}

/* Content Grid */
.content-grid {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-bottom: 1rem;
}

/* Profile Section */
.profile-section {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
}

.profile-section > * {
  min-width: 0;
}

.section-header {
  text-align: center;
  margin-bottom: 0.85rem;
}

.section-header h2 {
  font-size: 1.2rem;
  font-weight: 700;
  color: var(--do-text);
  margin-bottom: 0.4rem;
}

.section-header p {
  font-size: 0.85rem;
  color: var(--do-text-secondary);
  line-height: 1.6;
}

.integrations-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 0.65rem;
}

/* Skills Section */
.skill-groups {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.skill-group {
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 0.6rem;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.02);
}

.skill-group-header {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.65rem 0.85rem;
  background: transparent;
  border: none;
  cursor: pointer;
  font-family: inherit;
  transition: background var(--transition-fast);
  gap: 0.5rem;
}

.skill-group-header:hover {
  background: rgba(255, 255, 255, 0.04);
}

.skill-group-header.is-open {
  background: rgba(255, 255, 255, 0.04);
  border-bottom: 1px solid rgba(255, 255, 255, 0.07);
}

.skill-group-title {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}

.skill-group-icon {
  width: 1.7rem;
  height: 1.7rem;
  border-radius: 0.4rem;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.8rem;
  flex-shrink: 0;
}

.skill-group-icon.tone-success {
  color: var(--do-success);
  background: rgba(34, 197, 94, 0.12);
}

.skill-group-icon.tone-info {
  color: var(--do-info);
  background: rgba(6, 182, 212, 0.12);
}

.skill-group-icon.tone-warning {
  color: var(--do-warning);
  background: rgba(245, 158, 11, 0.12);
}

.skill-group-name {
  font-size: 0.88rem;
  font-weight: 600;
  color: var(--do-text);
}

.skill-group-count {
  font-size: 0.72rem;
  font-weight: 600;
  color: var(--do-text-muted);
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 999px;
  padding: 0.1rem 0.45rem;
}

.skill-chevron {
  font-size: 0.75rem;
  color: var(--do-text-muted);
  transition: transform 0.2s ease;
  flex-shrink: 0;
}

.skill-chevron.is-rotated {
  transform: rotate(180deg);
}

.skill-group-content {
  padding: 0.65rem;
}

/* Profile Card */
.profile-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.profile-info {
  display: flex;
  align-items: center;
  gap: 0.65rem;
}

.profile-icon {
  width: 2rem;
  height: 2rem;
  border-radius: 0.5rem;
  background: var(--gradient-success);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--vt-c-white);
  font-size: 0.85rem;
}

.profile-details h3 {
  font-size: 1rem;
  font-weight: 700;
  color: var(--do-text);
  margin: 0 0 0.25rem 0;
}

.profile-details p {
  color: var(--do-text-secondary);
  margin: 0;
}

.profile-content {
  display: flex;
  flex-direction: column;
  gap: 0.7rem;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.info-item label {
  font-weight: 600;
  color: var(--do-text-secondary);
  font-size: 0.875rem;
}

.info-item span {
  color: var(--do-text);
  font-size: 1rem;
}

.context-scroll {
  max-height: 110px;
}

.context-scroll p {
  margin: 0;
  color: var(--do-text-muted);
  line-height: 1.6;
}

.tts-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.5rem 0;
  border-top: 1px solid rgba(255, 255, 255, 0.07);
}

.tts-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.tts-icon {
  color: var(--do-blue);
  font-size: 0.9rem;
}

.tts-label {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--do-text);
}

.lang-toggle {
  display: flex;
  border: 1px solid var(--do-border-light);
  border-radius: 0.4rem;
  overflow: hidden;
}

.lang-opt {
  padding: 0.25rem 0.7rem;
  font-size: 0.75rem;
  font-weight: 600;
  background: transparent;
  color: var(--do-text-muted);
  border: none;
  cursor: pointer;
  transition:
    background 0.15s,
    color 0.15s;
}

.lang-opt:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.06);
  color: var(--do-text);
}

.lang-opt--active {
  background: rgba(59, 130, 246, 0.18) !important;
  color: var(--do-blue) !important;
}

.lang-opt:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.provider-select {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--do-border-light);
  border-radius: 0.4rem;
  color: var(--do-text);
  font-size: 0.78rem;
  font-weight: 500;
  padding: 0.25rem 0.5rem;
  cursor: pointer;
  max-width: 180px;
  appearance: auto;
}

.provider-select:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.provider-select option {
  background: var(--do-navy, #0d1117);
  color: var(--do-text);
}

.provider-apikey-row {
  flex-direction: column;
  align-items: flex-start;
  gap: 0.5rem;
  padding-top: 0.5rem;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.provider-apikey-actions {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  width: 100%;
}

.provider-apikey-actions .p-inputtext {
  flex: 1;
  min-width: 0;
}

.add-provider-form {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 0.5rem;
  padding: 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-top: 0.25rem;
}

.add-provider-fields {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.add-provider-fields .p-inputtext {
  width: 100%;
}

.add-provider-actions {
  display: flex;
  gap: 0.4rem;
  justify-content: flex-end;
}

.provider-select-row {
  display: flex;
  align-items: center;
  gap: 0.35rem;
}

.add-provider-toggle {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--do-accent, #5b9cf6);
  font-size: 0.85rem;
  display: flex;
  align-items: center;
  padding: 0.2rem;
  opacity: 0.7;
  transition: opacity 0.2s;
  flex-shrink: 0;
}

.add-provider-toggle:hover {
  opacity: 1;
}

.profile-actions {
  margin-top: 0.65rem;
  padding-top: 0.65rem;
  border-top: 1px solid rgba(255, 255, 255, 0.07);
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.sandbox-button {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  color: var(--vt-c-white);
  text-decoration: none;
  border-radius: 0.5rem;
  font-weight: 600;
  font-size: 0.8rem;
  transition: all 0.3s ease;
  flex: 1;
  justify-content: center;
  min-width: fit-content;
}

.sandbox-button {
  background: var(--gradient-warning);
  box-shadow: 0 4px 14px var(--shadow-light);
}

.sandbox-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px var(--shadow-medium);
  color: var(--vt-c-white);
}

.sandbox-button i {
  font-size: 1.1rem;
}

/* Quick Access Card */
.quick-access-card {
  margin-top: 1rem;
}

.quick-access-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem 1rem 0;
}

.quick-access-header h3 {
  margin: 0;
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--do-text);
}

.quick-access-header p {
  margin: 0;
  font-size: 0.75rem;
  color: var(--do-text-muted);
}

.quick-access-icon {
  width: 2.2rem;
  height: 2.2rem;
  border-radius: 0.5rem;
  background: linear-gradient(135deg, #3b82f6, #06b6d4);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-size: 1rem;
  color: #fff;
}

.quick-access-actions {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.qa-btn {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.65rem 0.85rem;
  border-radius: 0.5rem;
  text-decoration: none;
  transition:
    background 0.15s,
    transform 0.15s;
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.qa-btn i {
  font-size: 1.1rem;
  flex-shrink: 0;
}

.qa-btn-label {
  display: block;
  font-size: 0.85rem;
  font-weight: 600;
}

.qa-btn-desc {
  display: block;
  font-size: 0.72rem;
  opacity: 0.6;
}

.qa-btn--primary {
  background: rgba(59, 130, 246, 0.12);
  color: #60a5fa;
}

.qa-btn--primary:hover {
  background: rgba(59, 130, 246, 0.22);
  transform: translateX(3px);
}

.qa-btn--secondary {
  background: rgba(255, 255, 255, 0.04);
  color: var(--do-text-secondary);
}

.qa-btn--secondary:hover {
  background: rgba(255, 255, 255, 0.08);
  transform: translateX(3px);
}

/* Stats Card */
.stats-header {
  display: flex;
  align-items: center;
  gap: 0.65rem;
}

.stats-icon {
  width: 2rem;
  height: 2rem;
  border-radius: 0.5rem;
  background: var(--gradient-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 0.85rem;
}

.stats-info h3 {
  font-size: 1rem;
  font-weight: 700;
  color: var(--do-text);
  margin: 0 0 0.25rem 0;
}

.stats-info p {
  color: var(--do-text-muted);
  margin: 0;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.7rem;
  margin-bottom: 0.85rem;
}

.stat-item {
  text-align: center;
  padding: 0.65rem;
  background: rgba(255, 255, 255, 0.04);
  border-radius: 0.5rem;
  border: 1px solid rgba(255, 255, 255, 0.07);
  position: relative;
}

.stat-value {
  font-size: 1.25rem;
  font-weight: 800;
  color: var(--do-text);
  margin-bottom: 0.2rem;
}

.stat-label {
  font-size: 0.75rem;
  color: var(--do-text-secondary);
  font-weight: 500;
}

.stat-icon {
  position: absolute;
  top: 0.5rem;
  right: 0.5rem;
  color: var(--do-blue);
  font-size: 1rem;
}

.stats-actions {
  text-align: center;
}

.view-conversations-button {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  background: var(--gradient-primary);
  color: var(--vt-c-white);
  text-decoration: none;
  border-radius: 0.5rem;
  font-weight: 600;
  font-size: 0.8rem;
  transition: all 0.3s ease;
  box-shadow: 0 4px 14px var(--shadow-light);
}

.view-conversations-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px var(--shadow-medium);
  color: var(--vt-c-white);
}

/* Integration Buttons */
.integration-button {
  position: relative;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.03);
  width: 100%;
  text-align: left;
  padding: 0.55rem 0.7rem;
  border-radius: 0.5rem;
  cursor: pointer;
  font-family: inherit;
  min-height: 52px;
  transition:
    border-color var(--transition-fast),
    box-shadow var(--transition-fast),
    transform var(--transition-fast),
    background var(--transition-fast);
}

.integration-button:not(.is-disabled):hover,
.integration-button:not(.is-disabled):focus-visible {
  border-color: rgba(59, 130, 246, 0.4);
  background: rgba(59, 130, 246, 0.06);
  box-shadow: 0 0 0 1px rgba(59, 130, 246, 0.2);
  outline: none;
}

.integration-button.is-disabled {
  cursor: not-allowed;
  opacity: 0.85;
}

.integration-button.is-disabled:hover {
  transform: none;
}

.integration-content {
  display: grid;
  grid-template-columns: 1fr auto;
  align-items: center;
  gap: 0.5rem;
}

.integration-main {
  display: flex;
  align-items: center;
  gap: 0.55rem;
}

.integration-actions {
  display: flex;
}

.integration-action-label {
  font-size: 0.72rem;
  font-weight: 600;
  color: var(--do-text-secondary);
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.05);
  border-radius: 999px;
  padding: 0.15rem 0.45rem;
}

.integration-button.is-disabled .integration-action-label {
  color: var(--do-text-muted);
}

.integration-legend {
  position: absolute;
  left: 0.875rem;
  right: 0.875rem;
  bottom: calc(100% + 0.5rem);
  background: var(--do-navy);
  color: var(--vt-c-white);
  padding: 0.5rem 0.625rem;
  border-radius: 0.5rem;
  font-size: 0.75rem;
  line-height: 1.3;
  opacity: 0;
  visibility: hidden;
  transform: translateY(4px);
  transition: all var(--transition-fast);
  pointer-events: none;
  box-shadow: 0 6px 14px var(--shadow-medium);
  z-index: 2;
}

.integration-legend::after {
  content: '';
  position: absolute;
  left: 1rem;
  top: 100%;
  border-width: 6px;
  border-style: solid;
  border-color: var(--do-navy) transparent transparent transparent;
}

.integration-button:hover .integration-legend,
.integration-button:focus-visible .integration-legend {
  opacity: 1;
  visibility: visible;
  transform: translateY(0);
}

.integration-icon {
  width: 1.75rem;
  height: 1.75rem;
  border-radius: 0.4rem;
  background: var(--do-bg);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.78rem;
  border: 1px solid var(--do-border-light);
}

.integration-icon.tone-primary {
  color: var(--do-blue);
  background: var(--vt-c-gray-50);
}

.integration-icon.tone-success {
  color: var(--do-success);
  background: var(--vt-c-gray-50);
}

.integration-icon.tone-warning {
  color: var(--do-warning);
  background: var(--vt-c-gray-50);
}

.integration-icon.tone-info {
  color: var(--do-info);
  background: var(--vt-c-gray-50);
}

.integration-icon.tone-danger {
  color: var(--do-danger);
  background: var(--vt-c-gray-50);
}

.integration-icon.disabled {
  color: var(--do-text-muted);
  background: var(--vt-c-gray-100);
}

.integration-info h3 {
  margin: 0;
  font-size: 0.86rem;
  font-weight: 600;
  color: var(--do-text);
  line-height: 1.2;
}

/* Loading and Empty States */
.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  text-align: center;
  padding: 1rem;
}

.loading-state p,
.empty-state p {
  color: var(--do-text-muted);
  margin: 0;
}

.empty-state i {
  font-size: 2rem;
  color: var(--do-blue);
}

.empty-state h3 {
  font-size: 1rem;
  font-weight: 700;
  color: var(--do-text);
  margin: 0;
}

.create-button {
  background: var(--gradient-success);
  border: none;
  color: var(--vt-c-white);
  padding: 0.55rem 0.8rem;
  border-radius: 0.5rem;
  font-weight: 600;
  font-size: 0.82rem;
  transition: all 0.3s ease;
  box-shadow: 0 4px 14px var(--shadow-light);
}

.create-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px var(--shadow-medium);
}

/* Modal Styles */
.modal-form {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
  margin-bottom: 1rem;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-field label {
  font-weight: 600;
  color: var(--do-text-secondary);
  font-size: 0.875rem;
}

:deep(.form-field .p-inputtext),
:deep(.form-field .p-inputtextarea) {
  background: rgba(255, 255, 255, 0.05);
  border: 1.5px solid rgba(255, 255, 255, 0.1);
  color: var(--do-text);
  border-radius: 0.5rem;
  padding: 0.55rem;
  transition: all 0.3s ease;
}

:deep(.form-field .p-inputtext:focus),
:deep(.form-field .p-inputtextarea:focus) {
  border-color: var(--do-blue);
  box-shadow: 0 0 0 3px var(--vt-c-gray-200);
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.6rem;
  padding-top: 0.65rem;
  border-top: 1px solid rgba(255, 255, 255, 0.07);
}

/* PrimeVue Card Dark Overrides */
:deep(.p-card) {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.07);
  color: var(--do-text);
}

:deep(.p-card-header) {
  border-bottom: 1px solid rgba(255, 255, 255, 0.07);
  background: transparent;
}

:deep(.p-card-content) {
  background: transparent;
}

/* Responsive Design */
@media (max-width: 768px) {
  .dashboard-container {
    padding: 0.85rem;
    padding-top: calc(3.25rem + 0.7rem);
  }

  .dashboard-header {
    flex-direction: column;
    gap: 1rem;
    text-align: center;
    padding: 0.85rem;
  }

  .header-content {
    flex-direction: column;
    gap: 1rem;
  }

  .dashboard-title {
    font-size: 1.2rem;
  }

  .dashboard-subtitle {
    font-size: 0.82rem;
  }

  .profile-section {
    flex-direction: column;
  }

  .stats-grid {
    grid-template-columns: 1fr;
    gap: 1rem;
  }

  .integrations-grid {
    grid-template-columns: 1fr;
    gap: 0.65rem;
  }

  .section-header h2 {
    font-size: 1.1rem;
  }

  .section-header p {
    font-size: 0.82rem;
  }
}

@media (max-width: 480px) {
  .dashboard-container {
    padding: 0.6rem;
    padding-top: calc(3.25rem + 0.6rem);
  }

  .icon-wrapper {
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 2rem;
    color: var(--do-blue);
    flex-shrink: 0;
  }

  .dashboard-title {
    font-size: 1.05rem;
  }

  .dashboard-header {
    padding: 0.75rem;
  }

  :deep(.loading-card .p-card-content),
  :deep(.empty-card .p-card-content),
  :deep(.profile-card .p-card-content),
  :deep(.stats-card .p-card-content) {
    padding: 1.25rem;
  }

  :deep(.profile-card .p-card-header),
  :deep(.stats-card .p-card-header) {
    padding: 1rem 1.25rem;
  }
}

.name-clickable {
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 0.4rem;
}
.name-pencil-icon {
  font-size: 0.75rem;
  opacity: 0;
  transition: opacity 0.15s;
  color: var(--p-primary-color, #6366f1);
}
.name-clickable:hover .name-pencil-icon {
  opacity: 1;
}
.name-edit {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.name-edit-spinner {
  font-size: 0.9rem;
  color: var(--p-primary-color, #6366f1);
}
</style>
