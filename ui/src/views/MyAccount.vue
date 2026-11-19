<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import Card from 'primevue/card'
import Toast from 'primevue/toast'
import { useAssistant } from '@/composables/useAssistant'
import { useErrorToast } from '@/composables/useErrorToast'
import { useClipboard } from '@/composables/useClipboard'
import LoadingSpinner from '@/components/core/LoadingSpinner/LoadingSpinner.vue'
import Button from 'primevue/button'
import DefaultModal from '@/components/core/shared/DefaultModal/DefaultModal.vue'
import InputText from 'primevue/inputtext'
import Tag from 'primevue/tag'
import { useToogle } from '@/composables/useToogle'
import type { ApiKeyParams } from '@/types/assistant.ts'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
const { copyText } = useClipboard()

const { toogleValue: isVisibleAddApiKey } = useToogle(false)
const { toogleValue: isVisibleRemoveApiKey } = useToogle(false)
const router = useRouter()

const {
  assistantProfile,
  getAssistantProfile,
  addApiKey,
  removeApiKey,
  listContacts,

  isGetAssistantProfilePending,

  isAddApiKeyPending,
  isAddApiKeySuccess,
  isAddApiKeyError,
  addApiKeyError,

  isRemoveApiKeyPending,
  isRemoveApiKeyError,
  isRemoveApiKeySuccess,
  removeApiKeyError,
} = useAssistant()

const errorWatchers = [
  {
    flag: isAddApiKeyError,
    summary: t('myAccount.errorAddKey'),
    detail: addApiKeyError,
  },
  {
    flag: isRemoveApiKeyError,
    summary: t('myAccount.errorDeleteKey'),
    detail: removeApiKeyError,
  },
]

const { toast } = useErrorToast(errorWatchers)

onMounted(async () => {
  await getAssistantProfile()
  await listContacts()
})

watch(isAddApiKeySuccess, (value) => {
  if (value) {
    toast.add({
      severity: 'success',
      summary: t('myAccount.keyAdded'),
      detail: t('myAccount.keyAddedDesc'),
      life: 3000,
    })
  }
})

watch(isRemoveApiKeySuccess, (value) => {
  if (value) {
    toast.add({
      severity: 'success',
      summary: t('myAccount.keyDeleted'),
      detail: t('myAccount.keyDeletedDesc'),
      life: 3000,
    })
  }
})

const addApiKeyParams = reactive<ApiKeyParams>({
  description: '',
  contact_id: '',
})

const modalTitleAddApiKey = computed(() => t('myAccount.addKeyTitle'))
const changeAddApiKeyVisible = (value: boolean) => {
  isVisibleAddApiKey.value = value
}

const addApiKeyHandler = async () => {
  try {
    if (!addApiKeyParams.contact_id) {
      toast.add({
        severity: 'warn',
        summary: t('myAccount.contactRequired'),
        detail: t('myAccount.contactRequiredDesc'),
        life: 3000,
      })
      return
    }
    await addApiKey(addApiKeyParams)
    addApiKeyParams.description = ''
    addApiKeyParams.contact_id = ''
    isVisibleAddApiKey.value = false
  } catch (error) {
    console.error('Error adding api key:', error)
  }
}

const goToContacts = () => router.push('/app/contacts')

const removeApiKeyDeleteData = ref<string | null>(null)

const modalTitleRemoveApiKey = computed(() => t('myAccount.deleteKeyTitle'))
const changeRemoveApiKeyVisible = (value: boolean) => {
  isVisibleRemoveApiKey.value = value
}

const removeApiKeyHandler = async () => {
  if (!removeApiKeyDeleteData.value) return
  try {
    await removeApiKey(removeApiKeyDeleteData.value)
    isVisibleRemoveApiKey.value = false
  } catch (error) {
    console.error('Error removing api key:', error)
  }
}

const copyApiKey = async (apiKey: string) => {
  const copied = await copyText(apiKey)
  if (!copied) {
    toast.add({
      severity: 'error',
      summary: t('common.error'),
      detail: t('common.unknownError'),
      life: 3000,
    })
    return
  }

  toast.add({
    severity: 'success',
    summary: t('myAccount.keyCopied'),
    detail: t('myAccount.keyCopiedDesc'),
    life: 3000,
  })
}

const removeApiKeyOpenModal = (apiKeyID: string) => {
  removeApiKeyDeleteData.value = apiKeyID
  isVisibleRemoveApiKey.value = true
}
</script>

<template>
  <div class="account-container">
    <!-- Header -->
    <div class="account-header">
      <div class="header-content">
        <div class="icon-wrapper">
          <i class="pi pi-key"></i>
        </div>
        <div class="title-section">
          <h1 class="page-title">{{ t('myAccount.title') }}</h1>
          <p class="page-subtitle">{{ t('myAccount.subtitle') }}</p>
        </div>
      </div>
    </div>

    <div v-if="isGetAssistantProfilePending" class="loading-state">
      <LoadingSpinner />
      <p>{{ t('myAccount.loadingAccount') }}</p>
    </div>

    <div v-else-if="assistantProfile" class="api-keys-section">
      <Card class="api-keys-card">
        <template #header>
          <div class="api-header">
            <div class="api-info">
              <div class="api-icon">
                <i class="pi pi-key"></i>
              </div>
              <div class="api-details">
                <h3>{{ t('myAccount.apiKeys') }}</h3>
                <p>
                  {{ assistantProfile?.api_keys?.filter((key) => key.is_active).length || 0 }}
                  {{ t('myAccount.activeKeys') }}
                </p>
              </div>
            </div>
            <Button
              icon="pi pi-users"
              :label="t('myAccount.manageContacts')"
              severity="secondary"
              text
              @click="goToContacts"
            />
            <Button
              icon="pi pi-plus"
              :label="t('myAccount.newKey')"
              severity="primary"
              @click="isVisibleAddApiKey = true"
            />
          </div>
        </template>
        <template #content>
          <div class="api-keys-content">
            <!-- Keys List -->
            <div v-if="assistantProfile?.api_keys?.some((key) => key.is_active)" class="keys-list">
              <div
                v-for="apiKey in assistantProfile.api_keys"
                :key="apiKey.id"
                class="key-item"
                v-show="apiKey.is_active"
              >
                <div class="key-info">
                  <div class="key-header">
                    <Tag :value="apiKey.description" severity="info" class="key-tag" />
                    <Tag
                      :value="apiKey.contact_name || 'No contact'"
                      severity="success"
                      class="key-tag"
                    />
                    <span class="key-date">{{ t('myAccount.recentlyCreated') }}</span>
                  </div>
                  <div class="key-value-container">
                    <div class="key-value">
                      <code>{{ apiKey.value }}</code>
                    </div>
                    <div class="key-actions">
                      <Button
                        icon="pi pi-copy"
                        severity="warning"
                        size="small"
                        @click="copyApiKey(apiKey.value)"
                        :title="t('myAccount.copyKey')"
                      />
                      <Button
                        icon="pi pi-trash"
                        severity="danger"
                        size="small"
                        @click="removeApiKeyOpenModal(apiKey.id)"
                        :title="t('myAccount.deleteKey')"
                      />
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Empty State -->
            <div v-else class="empty-keys">
              <i class="pi pi-key"></i>
              <h4>{{ t('myAccount.noApiKeys') }}</h4>
              <p>{{ t('myAccount.noApiKeysDesc') }}</p>
              <Button
                :label="t('myAccount.createFirstKey')"
                icon="pi pi-plus"
                severity="primary"
                @click="isVisibleAddApiKey = true"
              />
            </div>

            <div v-if="isAddApiKeyError" class="error-message">
              <i class="pi pi-exclamation-triangle"></i>
              <span>{{ t('myAccount.errorAddKeyMsg') }}: {{ addApiKeyError }}</span>
            </div>
          </div>
        </template>
      </Card>
    </div>

    <!-- Add API Key Modal -->
    <DefaultModal
      @update:visible="changeAddApiKeyVisible"
      :isVisible="isVisibleAddApiKey"
      :title="modalTitleAddApiKey"
    >
      <div class="modal-form">
        <div class="form-field">
          <label for="api_key_description">{{ t('myAccount.keyDescription') }}</label>
          <InputText
            id="api_key_description"
            v-model="addApiKeyParams.description"
            :placeholder="t('myAccount.keyDescriptionPlaceholder')"
          />
          <small>{{ t('myAccount.keyDescriptionHelp') }}</small>
        </div>
        <div class="form-field">
          <label for="api_key_contact">{{ t('myAccount.contactLabel') }}</label>
          <Dropdown
            id="api_key_contact"
            v-model="addApiKeyParams.contact_id"
            :options="assistantProfile?.contacts || []"
            optionLabel="name"
            optionValue="id"
            :placeholder="t('myAccount.contactPlaceholder')"
          />
          <small>{{ t('myAccount.contactHelp') }}</small>
        </div>
      </div>
      <div class="modal-actions">
        <Button
          :label="t('common.cancel')"
          severity="secondary"
          @click="isVisibleAddApiKey = false"
        />
        <Button
          :label="t('myAccount.createKey')"
          icon="pi pi-key"
          :loading="isAddApiKeyPending"
          @click="addApiKeyHandler"
        />
      </div>
    </DefaultModal>

    <!-- Remove API Key Modal -->
    <DefaultModal
      @update:visible="changeRemoveApiKeyVisible"
      :isVisible="isVisibleRemoveApiKey"
      :title="modalTitleRemoveApiKey"
    >
      <div class="modal-content">
        <div class="warning-content">
          <i class="pi pi-exclamation-triangle warning-icon"></i>
          <div class="warning-text">
            <h4>{{ t('myAccount.deleteKeyConfirm') }}</h4>
            <p>{{ t('myAccount.deleteKeyWarning') }}</p>
          </div>
        </div>
      </div>
      <div class="modal-actions">
        <Button
          :label="t('common.cancel')"
          severity="secondary"
          @click="isVisibleRemoveApiKey = false"
        />
        <Button
          :label="t('common.delete')"
          icon="pi pi-trash"
          severity="danger"
          :loading="isRemoveApiKeyPending"
          @click="removeApiKeyHandler"
        />
      </div>
      <div v-if="isRemoveApiKeyError" class="modal-error">
        <i class="pi pi-exclamation-triangle"></i>
        <span>{{ t('myAccount.errorDeleteKeyMsg') }}: {{ removeApiKeyError }}</span>
      </div>
    </DefaultModal>

    <Toast position="top-right" />
  </div>
</template>

<style scoped>
.account-container {
  max-width: 900px;
  margin: 0 auto;
  padding: 2rem;
  padding-top: calc(3.5rem + 2rem);
  min-height: 100vh;
  background: var(--do-bg);
}

/* Header */
.account-header {
  background: var(--do-bg-white);
  padding: 1.5rem 2rem;
  border-radius: 0.75rem;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
  border: 1px solid var(--do-border-light);
  margin-bottom: 2rem;
}

.header-content {
  display: flex;
  align-items: center;
  gap: 1.5rem;
}

.icon-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 2rem;
  color: var(--do-blue);
  flex-shrink: 0;
}

.page-title {
  font-size: 2rem;
  font-weight: 800;
  color: var(--do-text);
  margin: 0 0 0.25rem 0;
}

.page-subtitle {
  font-size: 1rem;
  color: var(--do-text-muted);
  margin: 0;
}

/* Loading */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 4rem 2rem;
  gap: 1rem;
  background: var(--do-bg-white);
  border-radius: 0.75rem;
  border: 1px solid var(--do-border-light);
}

.loading-state p {
  margin: 0;
  color: var(--do-text-muted);
}

/* TTS Card */
.tts-card {
  border-radius: 0.75rem;
  overflow: hidden;
  border: 1px solid var(--do-border-light);
}

:deep(.tts-card .p-card-content) {
  padding: 1.25rem 1.5rem;
}

.tts-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.tts-info {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.tts-icon {
  width: 2.75rem;
  height: 2.75rem;
  border-radius: 0.625rem;
  background: var(--gradient-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.125rem;
  color: white;
  flex-shrink: 0;
}

.tts-details h3 {
  margin: 0 0 0.2rem 0;
  font-size: 1.125rem;
  font-weight: 700;
  color: var(--do-text);
}

.tts-details p {
  margin: 0;
  font-size: 0.875rem;
  color: var(--do-text-muted);
}

/* Language toggle */
.voice-dropdown {
  min-width: 10rem;
  flex-shrink: 0;
}

.lang-toggle {
  display: flex;
  border: 1px solid var(--do-border-light);
  border-radius: 0.5rem;
  overflow: hidden;
  flex-shrink: 0;
}

.lang-opt {
  padding: 0.35rem 0.85rem;
  font-size: 0.8rem;
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

/* API Keys Section */
.api-keys-section {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.api-keys-card {
  border-radius: 0.75rem;
  overflow: hidden;
  border: 1px solid var(--do-border-light);
}

:deep(.api-keys-card .p-card-header) {
  background: var(--do-bg-white);
  padding: 1.25rem 1.5rem;
  border-bottom: 1px solid var(--do-border-light);
}

.api-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.api-info {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.api-icon {
  width: 2.75rem;
  height: 2.75rem;
  border-radius: 0.625rem;
  background: var(--gradient-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.125rem;
  color: white;
}

.api-details h3 {
  margin: 0 0 0.2rem 0;
  font-size: 1.125rem;
  font-weight: 700;
  color: var(--do-text);
}

.api-details p {
  margin: 0;
  font-size: 0.875rem;
  color: var(--do-text-muted);
}

:deep(.api-keys-card .p-card-content) {
  padding: 1.5rem;
}

.api-keys-content {
  min-height: 150px;
}

/* Keys List */
.keys-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.key-item {
  padding: 1.25rem;
  background: var(--do-bg);
  border-radius: 0.625rem;
  border: 1px solid var(--do-border-light);
  transition: box-shadow 0.15s ease;
}

.key-item:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.key-info {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.key-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

:deep(.key-tag) {
  background: rgba(0, 105, 255, 0.1);
  color: var(--do-blue);
  border: 1px solid rgba(0, 105, 255, 0.2);
}

.key-date {
  font-size: 0.75rem;
  color: var(--do-text-muted);
}

.key-value-container {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.key-value {
  flex: 1;
  background: var(--do-bg-white);
  padding: 0.625rem 0.875rem;
  border-radius: 0.5rem;
  border: 1px solid var(--do-border-light);
  overflow: hidden;
}

.key-value code {
  font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
  font-size: 0.8rem;
  color: var(--do-text);
  word-break: break-all;
}

.key-actions {
  display: flex;
  gap: 0.5rem;
  flex-shrink: 0;
}

/* Empty State */
.empty-keys {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 3rem 2rem;
  gap: 1rem;
}

.empty-keys i {
  font-size: 2.5rem;
  color: var(--do-text-muted);
}

.empty-keys h4 {
  margin: 0;
  color: var(--do-text);
  font-weight: 600;
  font-size: 1.125rem;
}

.empty-keys p {
  margin: 0;
  color: var(--do-text-muted);
  line-height: 1.5;
}

/* Error */
.error-message {
  margin-top: 1rem;
  padding: 0.875rem 1rem;
  background: rgba(239, 68, 68, 0.08);
  border: 1px solid rgba(239, 68, 68, 0.2);
  border-radius: 0.5rem;
  color: #b91c1c;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
}

/* Modal */
.modal-form {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  margin-bottom: 2rem;
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

:deep(.form-field .p-inputtext) {
  border: 2px solid var(--do-border-light);
  border-radius: 0.5rem;
  padding: 0.75rem;
}

:deep(.form-field .p-inputtext:focus) {
  border-color: var(--do-blue);
  box-shadow: 0 0 0 3px rgba(0, 105, 255, 0.1);
}

.form-field small {
  color: var(--do-text-muted);
  font-size: 0.75rem;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  padding-top: 1rem;
  border-top: 1px solid var(--do-border-light);
}

.modal-content {
  margin-bottom: 2rem;
}

.warning-content {
  display: flex;
  align-items: flex-start;
  gap: 1rem;
  padding: 1.25rem;
  background: rgba(239, 68, 68, 0.05);
  border: 1px solid rgba(239, 68, 68, 0.2);
  border-radius: 0.75rem;
}

.warning-icon {
  font-size: 1.75rem;
  color: #ef4444;
  flex-shrink: 0;
}

.warning-text h4 {
  margin: 0 0 0.5rem 0;
  color: #b91c1c;
  font-weight: 600;
}

.warning-text p {
  margin: 0;
  color: #7f1d1d;
  line-height: 1.5;
  font-size: 0.9rem;
}

.modal-error {
  margin-top: 1rem;
  padding: 0.875rem 1rem;
  background: rgba(239, 68, 68, 0.08);
  border: 1px solid rgba(239, 68, 68, 0.2);
  border-radius: 0.5rem;
  color: #b91c1c;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
}

/* Responsive */
@media (max-width: 768px) {
  .account-container {
    padding: 1rem;
    padding-top: calc(3.5rem + 1rem);
  }

  .account-header {
    padding: 1.25rem;
  }

  .header-content {
    gap: 1rem;
  }

  .page-title {
    font-size: 1.5rem;
  }

  .api-header {
    flex-direction: column;
    gap: 1rem;
    align-items: stretch;
  }

  .key-value-container {
    flex-direction: column;
    align-items: stretch;
  }

  .key-actions {
    justify-content: flex-end;
  }
}
</style>
