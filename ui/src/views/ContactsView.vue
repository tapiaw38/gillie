<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import Card from 'primevue/card'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Toast from 'primevue/toast'
import Tag from 'primevue/tag'
import { useAssistant } from '@/composables/useAssistant'
import { useErrorToast } from '@/composables/useErrorToast'
import { useI18n } from 'vue-i18n'

const {
  assistantProfile,
  listContacts,
  addContact,
  updateContact,
  deleteContact,
  ownerMemories,
  ownerMemoriesHasMore,
  ownerMemoriesNextOffset,
  listOwnerMemories,
  isListContactsPending,
  isListContactsError,
  listContactsError,
  isAddContactPending,
  isAddContactError,
  addContactError,
  isUpdateContactPending,
  isUpdateContactError,
  updateContactError,
  isDeleteContactPending,
  isDeleteContactError,
  deleteContactError,
  isListOwnerMemoriesPending,
  isListOwnerMemoriesError,
  listOwnerMemoriesError,
} = useAssistant()

const { t } = useI18n()

const contactForm = reactive({
  name: '',
  channel: '',
  external_id: '',
})

const formError = ref('')
const editingContactId = ref('')
const selectedContactFilter = ref('')
const memoryQuery = ref('')

const { toast } = useErrorToast([
  {
    flag: isListContactsError,
    summary: t('contacts.errorLoad'),
    detail: listContactsError,
  },
  {
    flag: isAddContactError,
    summary: t('contacts.errorCreate'),
    detail: addContactError,
  },
  {
    flag: isUpdateContactError,
    summary: t('contacts.errorUpdate'),
    detail: updateContactError,
  },
  {
    flag: isListOwnerMemoriesError,
    summary: t('contacts.errorMemoryLoad'),
    detail: listOwnerMemoriesError,
  },
  {
    flag: isDeleteContactError,
    summary: t('contacts.errorDelete'),
    detail: deleteContactError,
  },
])

onMounted(async () => {
  await listContacts()
  await listOwnerMemories({ limit: 30, offset: 0 })
})

const createContact = async () => {
  if (!contactForm.name.trim()) {
    formError.value = t('contacts.nameRequired')
    return
  }
  formError.value = ''

  try {
    await addContact({
      name: contactForm.name.trim(),
      channel: contactForm.channel.trim() || undefined,
      external_id: contactForm.external_id.trim() || undefined,
    })
    await listContacts()

    contactForm.name = ''
    contactForm.channel = ''
    contactForm.external_id = ''
    toast.add({ severity: 'success', summary: t('contacts.created'), life: 2500 })
  } catch {
    // handled by error watchers
  }
}

const startEdit = (contact: { id: string; name: string; channel?: string; external_id?: string }) => {
  editingContactId.value = contact.id
  contactForm.name = contact.name
  contactForm.channel = contact.channel || ''
  contactForm.external_id = contact.external_id || ''
}

const cancelEdit = () => {
  editingContactId.value = ''
  contactForm.name = ''
  contactForm.channel = ''
  contactForm.external_id = ''
  formError.value = ''
}

const saveEdit = async () => {
  if (!editingContactId.value) return
  if (!contactForm.name.trim()) {
    formError.value = t('contacts.nameRequired')
    return
  }
  try {
    await updateContact(editingContactId.value, {
      name: contactForm.name.trim(),
      channel: contactForm.channel.trim() || undefined,
      external_id: contactForm.external_id.trim() || undefined,
    })
    await listContacts()
    toast.add({ severity: 'success', summary: t('contacts.updated'), life: 2500 })
    cancelEdit()
  } catch {
    // handled by error watchers
  }
}

const removeContact = async (contactId: string) => {
  try {
    await deleteContact(contactId)
    await listContacts()
    if (editingContactId.value === contactId) {
      cancelEdit()
    }
    toast.add({ severity: 'success', summary: t('contacts.deleted'), life: 2500 })
  } catch {
    // handled by error watchers
  }
}

const refreshMemories = async () => {
  await listOwnerMemories({
    contact_id: selectedContactFilter.value || undefined,
    query: memoryQuery.value.trim() || undefined,
    limit: 30,
    offset: 0,
  })
}

const loadMoreMemories = async () => {
  if (!ownerMemoriesHasMore.value || ownerMemoriesNextOffset.value == null) return
  await listOwnerMemories({
    contact_id: selectedContactFilter.value || undefined,
    query: memoryQuery.value.trim() || undefined,
    limit: 30,
    offset: ownerMemoriesNextOffset.value,
    append: true,
  })
}

const resolveScopeLabel = (scope: string | undefined) => {
  if (!scope) return t('contacts.unknownScope')
  const contactMatch = scope.match(/__contact__(.+)$/)
  if (contactMatch && contactMatch[1]) {
    const contact = (assistantProfile.value?.contacts || []).find((item) => item.id === contactMatch[1])
    return contact ? contact.name : contactMatch[1]
  }
  if (scope.endsWith('__owner')) return t('contacts.ownerScope')
  return scope
}
</script>

<template>
  <div class="contacts-container">
    <div class="page-header">
      <div class="header-left">
        <div class="icon-wrapper">
          <i class="pi pi-users"></i>
        </div>
        <div class="header-text">
          <h1 class="page-title">{{ t('contacts.title') }}</h1>
          <p class="page-subtitle">{{ t('contacts.subtitle') }}</p>
        </div>
      </div>
    </div>

    <div class="grid">
      <Card class="panel contacts-panel">
        <template #title>{{ t('contacts.createTitle') }}</template>
        <template #content>
          <div class="form-grid">
            <div class="field">
              <label>{{ t('contacts.fields.name') }}</label>
              <InputText v-model="contactForm.name" :placeholder="t('contacts.placeholders.name')" />
            </div>
            <div class="field">
              <label>{{ t('contacts.fields.channel') }}</label>
              <InputText v-model="contactForm.channel" :placeholder="t('contacts.placeholders.channel')" />
            </div>
            <div class="field">
              <label>{{ t('contacts.fields.externalId') }}</label>
              <InputText v-model="contactForm.external_id" :placeholder="t('contacts.placeholders.externalId')" />
            </div>
          </div>
          <small v-if="formError" class="error">{{ formError }}</small>
          <div class="actions">
            <Button
              v-if="!editingContactId"
              :label="t('contacts.actions.create')"
              icon="pi pi-plus"
              :loading="isAddContactPending"
              @click="createContact"
            />
            <Button
              v-else
              :label="t('contacts.actions.save')"
              icon="pi pi-check"
              :loading="isUpdateContactPending"
              @click="saveEdit"
            />
            <Button
              v-if="editingContactId"
              :label="t('common.cancel')"
              severity="secondary"
              text
              @click="cancelEdit"
            />
          </div>
        </template>
      </Card>

      <Card class="panel">
        <template #title>{{ t('contacts.listTitle') }}</template>
        <template #content>
          <div v-if="isListContactsPending">{{ t('contacts.loading') }}</div>
          <DataTable
            v-else-if="assistantProfile?.contacts?.length"
            :value="assistantProfile.contacts"
            paginator
            :rows="5"
            :rowsPerPageOptions="[5, 10, 15]"
            class="contacts-table"
          >
            <Column field="name" :header="t('contacts.fields.name')" />
            <Column field="channel" :header="t('contacts.fields.channel')">
              <template #body="slotProps">
                <Tag :value="slotProps.data.channel || t('contacts.generalChannel')" severity="info" />
              </template>
            </Column>
            <Column field="external_id" :header="t('contacts.fields.externalId')">
              <template #body="slotProps">
                <span class="muted">{{ slotProps.data.external_id || '-' }}</span>
              </template>
            </Column>
            <Column :header="t('common.actions')">
              <template #body="slotProps">
                <div class="item-right">
                  <Button icon="pi pi-pencil" text size="small" @click="startEdit(slotProps.data)" />
                  <Button
                    icon="pi pi-trash"
                    text
                    size="small"
                    severity="danger"
                    :loading="isDeleteContactPending"
                    @click="removeContact(slotProps.data.id)"
                  />
                </div>
              </template>
            </Column>
          </DataTable>
          <div v-else class="muted">{{ t('contacts.empty') }}</div>
        </template>
      </Card>

      <Card class="panel panel-span-2">
        <template #title>{{ t('contacts.memoryTitle') }}</template>
        <template #content>
          <div class="memory-filters">
            <div class="field">
              <label>{{ t('contacts.memoryContactFilter') }}</label>
              <select v-model="selectedContactFilter" class="native-select">
                <option value="">{{ t('contacts.allContacts') }}</option>
                <option v-for="contact in assistantProfile?.contacts || []" :key="contact.id" :value="contact.id">
                  {{ contact.name }}
                </option>
              </select>
            </div>
            <div class="field">
              <label>{{ t('contacts.memorySearch') }}</label>
              <InputText v-model="memoryQuery" :placeholder="t('contacts.memorySearchPlaceholder')" />
            </div>
            <div class="actions">
              <Button :label="t('common.refresh')" icon="pi pi-refresh" :loading="isListOwnerMemoriesPending" @click="refreshMemories" />
            </div>
          </div>

          <div v-if="isListOwnerMemoriesPending">{{ t('contacts.memoryLoading') }}</div>
          <div v-else-if="ownerMemories?.length" class="list">
            <div v-for="memory in ownerMemories" :key="memory.id" class="item item-memory">
              <div class="item-main">
                <strong>{{ resolveScopeLabel(memory.memory_scope_id) }}</strong>
                <span class="muted">{{ memory.content }}</span>
                <span class="muted">{{ new Date(memory.created_at).toLocaleString() }}</span>
              </div>
              <Tag :value="`${t('contacts.importance')}: ${memory.importance}`" severity="contrast" />
            </div>
            <div class="actions" v-if="ownerMemoriesHasMore">
              <Button :label="t('contacts.loadMoreMemories')" icon="pi pi-angle-down" @click="loadMoreMemories" />
            </div>
          </div>
          <div v-else class="muted">{{ t('contacts.memoryEmpty') }}</div>
        </template>
      </Card>
    </div>

    <Toast position="top-right" />
  </div>
</template>

<style scoped>
.contacts-container { max-width: 1200px; margin: 0 auto; padding: 2rem; }
.page-header { margin-bottom: 1.5rem; }
.header-left { display: flex; align-items: center; gap: 0.75rem; }
.icon-wrapper { width: 2.2rem; height: 2.2rem; border-radius: 0.6rem; display: flex; align-items: center; justify-content: center; background: rgba(59,130,246,0.12); }
.page-title { margin: 0; }
.page-subtitle { margin: 0; color: var(--do-text-secondary); }
.grid { display: grid; gap: 1rem; grid-template-columns: 1fr 1fr; }
.panel { border: 1px solid var(--do-border-light); }
.panel-span-2 { grid-column: 1 / -1; }
.form-grid { display: grid; gap: 0.75rem; }
.field { display: grid; gap: 0.35rem; }
.actions { margin-top: 0.75rem; display: flex; justify-content: flex-end; }
.memory-filters { display: grid; grid-template-columns: 1fr 1fr auto; gap: 0.75rem; align-items: end; margin-bottom: 0.75rem; }
.native-select { border: 1px solid var(--do-border-light); border-radius: 0.45rem; background: var(--do-bg-card); color: var(--do-text); min-height: 2.4rem; padding: 0 0.6rem; }
.error { color: #ef4444; }
.list { display: grid; gap: 0.6rem; }
.contacts-table :deep(.p-datatable-tbody > tr > td) { vertical-align: middle; }
.item { display: flex; justify-content: space-between; align-items: center; border: 1px solid var(--do-border-light); border-radius: 0.6rem; padding: 0.6rem; }
.item-memory { align-items: flex-start; }
.item-main { display: grid; }
.item-right { display: flex; align-items: center; gap: 0.35rem; }
.muted { color: var(--do-text-secondary); font-size: 0.9rem; }
@media (max-width: 900px) {
  .grid { grid-template-columns: 1fr; }
  .memory-filters { grid-template-columns: 1fr; }
}
</style>
