<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useToast } from 'primevue/usetoast'
import { useI18n } from 'vue-i18n'
import DataView from 'primevue/dataview'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import Calendar from 'primevue/calendar'
import Dropdown from 'primevue/dropdown'
import ProgressSpinner from 'primevue/progressspinner'
import Message from 'primevue/message'
import Toast from 'primevue/toast'
import { useCalendar } from '@/composables/useCalendar'
import { useAssistant } from '@/composables/useAssistant'
import type { CalendarEvent } from '@/types/calendar'

const toast = useToast()
const { t } = useI18n()
const { assistantProfile, getAssistantProfile } = useAssistant()
const {
  events,
  isListEventsPending: isLoading,
  listEvents,
  updateEvent,
  deleteEvent: deleteCalendarEvent,
  isListEventsError,
  listEventsError,
  updateEventError,
  deleteEventError,
} = useCalendar()

const filteredEvents = ref<CalendarEvent[]>([])

const selectedStatus = ref<string | null>(null)
const searchQuery = ref('')

const statusOptions = computed(() => [
  { label: t('calendarEvents.status.all'), value: null },
  { label: t('calendarEvents.status.scheduled'), value: 'scheduled' },
  { label: t('calendarEvents.status.completed'), value: 'completed' },
  { label: t('calendarEvents.status.cancelled'), value: 'cancelled' },
])

const editDialogVisible = ref(false)
const selectedEvent = ref<CalendarEvent | null>(null)
const saving = ref(false)
const editForm = ref({
  title: '',
  description: '',
  location: '',
  start_time: new Date(),
  end_time: new Date(),
  status: 'scheduled',
})

const deleteDialogVisible = ref(false)
const eventToDelete = ref<CalendarEvent | null>(null)
const deleting = ref(false)

async function fetchEvents() {
  try {
    if (!assistantProfile.value) {
      await getAssistantProfile()
    }

    await listEvents(assistantProfile.value?.id)
    filteredEvents.value = events.value
  } catch (err: unknown) {
    console.error('Error fetching events:', err)
    toast.add({
      severity: 'error',
      summary: t('calendarEvents.errorLoad'),
      detail: listEventsError.value || t('calendarEvents.errorLoadDesc'),
      life: 5000,
    })
  }
}

function filterEvents() {
  let filtered = [...events.value]

  if (selectedStatus.value) {
    filtered = filtered.filter((event) => event.status === selectedStatus.value)
  }

  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    filtered = filtered.filter(
      (event) =>
        event.title.toLowerCase().includes(query) ||
        event.description?.toLowerCase().includes(query),
    )
  }

  filteredEvents.value = filtered
}

function openEditDialog(event: CalendarEvent) {
  selectedEvent.value = event
  editForm.value = {
    title: event.title,
    description: event.description || '',
    location: event.location || '',
    start_time: new Date(event.start_time),
    end_time: new Date(event.end_time),
    status: event.status,
  }
  editDialogVisible.value = true
}

async function saveEvent() {
  if (!selectedEvent.value) return

  saving.value = true

  try {
    await updateEvent(
      selectedEvent.value.id,
      {
        title: editForm.value.title,
        description: editForm.value.description || undefined,
        location: editForm.value.location || undefined,
        start_time: editForm.value.start_time.toISOString(),
        end_time: editForm.value.end_time.toISOString(),
      },
      assistantProfile.value?.id,
    )

    toast.add({
      severity: 'success',
      summary: t('calendarEvents.eventUpdated'),
      detail: t('calendarEvents.eventUpdatedDesc'),
      life: 3000,
    })

    editDialogVisible.value = false
    filteredEvents.value = events.value
  } catch (err: unknown) {
    console.error('Error updating event:', err)
    toast.add({
      severity: 'error',
      summary: t('calendarEvents.errorUpdate'),
      detail: updateEventError.value || t('calendarEvents.errorUpdateDesc'),
      life: 5000,
    })
  } finally {
    saving.value = false
  }
}

function confirmDelete(event: CalendarEvent) {
  eventToDelete.value = event
  deleteDialogVisible.value = true
}

async function performDelete() {
  if (!eventToDelete.value) return

  deleting.value = true

  try {
    await deleteCalendarEvent(eventToDelete.value.id, assistantProfile.value?.id)

    toast.add({
      severity: 'success',
      summary: t('calendarEvents.eventDeleted'),
      detail: t('calendarEvents.eventDeletedDesc'),
      life: 3000,
    })

    deleteDialogVisible.value = false
    filteredEvents.value = events.value
  } catch (err: unknown) {
    console.error('Error deleting event:', err)
    toast.add({
      severity: 'error',
      summary: t('calendarEvents.errorDelete'),
      detail: deleteEventError.value || t('calendarEvents.errorDeleteDesc'),
      life: 5000,
    })
  } finally {
    deleting.value = false
  }
}

function getStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    scheduled: t('calendarEvents.status.scheduled'),
    completed: t('calendarEvents.status.completed'),
    cancelled: t('calendarEvents.status.cancelled'),
  }
  return labels[status] || status
}

function getStatusSeverity(status: string): 'success' | 'info' | 'warning' | 'danger' {
  const severities: Record<string, 'success' | 'info' | 'warning' | 'danger'> = {
    scheduled: 'info',
    completed: 'success',
    cancelled: 'danger',
  }
  return severities[status] || 'info'
}

function formatDateTime(dateString: string): string {
  const date = new Date(dateString)
  return date.toLocaleString('es-ES', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

onMounted(() => {
  fetchEvents()
})
</script>

<template>
  <div class="calendar-events-view">
    <div class="header">
      <div class="header-content">
        <div>
          <h1 class="title">{{ t('calendarEvents.title') }}</h1>
          <p class="subtitle">
            {{ t('calendarEvents.subtitle') }}
          </p>
        </div>
      </div>
    </div>

    <div v-if="isLoading" class="loading-state">
      <ProgressSpinner />
      <p>{{ t('calendarEvents.loading') }}</p>
    </div>

    <div v-else-if="isListEventsError" class="error-state">
      <Message severity="error" :closable="false">
        {{ listEventsError }}
      </Message>
    </div>

    <div v-else-if="filteredEvents && filteredEvents.length > 0" class="events-container">
      <div class="filters">
        <div class="filter-group">
          <label>{{ t('calendarEvents.filter.status') }}:</label>
          <Dropdown
            v-model="selectedStatus"
            :options="statusOptions"
            optionLabel="label"
            optionValue="value"
            :placeholder="t('calendarEvents.filter.allStatuses')"
            @change="filterEvents"
          />
        </div>
        <div class="filter-group">
          <label>{{ t('calendarEvents.filter.search') }}:</label>
          <InputText
            v-model="searchQuery"
            :placeholder="t('calendarEvents.filter.searchPlaceholder')"
            @input="filterEvents"
          />
        </div>
      </div>

      <DataView :value="filteredEvents" dataKey="id" layout="list">
        <template #list="{ items }">
          <div v-for="event in items" :key="event.id" class="event-card">
            <div class="event-header">
              <div class="event-title-group">
                <h3>{{ event.title }}</h3>
                <Tag
                  :value="getStatusLabel(event.status)"
                  :severity="getStatusSeverity(event.status)"
                />
              </div>
              <div class="event-actions">
                <Button
                  icon="pi pi-pencil"
                  class="p-button-text p-button-rounded"
                  @click="openEditDialog(event)"
                  v-tooltip.top="t('calendarEvents.editEvent')"
                />
                <Button
                  icon="pi pi-trash"
                  class="p-button-text p-button-rounded p-button-danger"
                  @click="confirmDelete(event)"
                  v-tooltip.top="t('common.delete')"
                />
              </div>
            </div>

            <div class="event-details">
              <div class="detail-row">
                <i class="pi pi-clock"></i>
                <span>
                  {{ formatDateTime(event.start_time) }} -
                  {{ formatDateTime(event.end_time) }}
                </span>
              </div>

              <div v-if="event.location" class="detail-row">
                <i class="pi pi-map-marker"></i>
                <span>{{ event.location }}</span>
              </div>

              <div v-if="event.description" class="detail-row">
                <i class="pi pi-info-circle"></i>
                <span>{{ event.description }}</span>
              </div>

              <div v-if="event.attendees?.length > 0" class="detail-row">
                <i class="pi pi-users"></i>
                <span>{{ event.attendees.length }} {{ t('calendarEvents.attendees') }}</span>
              </div>

              <div v-if="event.google_id" class="detail-row">
                <i class="pi pi-google"></i>
                <span class="google-sync">{{ t('calendarEvents.syncedGoogle') }}</span>
              </div>
            </div>
          </div>
        </template>
      </DataView>
    </div>

    <div
      v-else-if="!isLoading && (!filteredEvents || filteredEvents.length === 0)"
      class="empty-state"
    >
      <i class="pi pi-calendar"></i>
      <h2>{{ t('calendarEvents.noEvents') }}</h2>
      <p>
        {{ t('calendarEvents.noEventsDesc') }}
      </p>
    </div>

    <Dialog
      v-model:visible="editDialogVisible"
      :header="t('calendarEvents.editEvent')"
      :modal="true"
      :closable="true"
      :style="{ width: '50vw' }"
    >
      <div v-if="selectedEvent" class="edit-form">
        <div class="field">
          <label for="title">{{ t('calendarEvents.fields.title') }} *</label>
          <InputText id="title" v-model="editForm.title" class="w-full" />
        </div>

        <div class="field">
          <label for="description">{{ t('calendarEvents.fields.description') }}</label>
          <Textarea id="description" v-model="editForm.description" rows="3" class="w-full" />
        </div>

        <div class="field">
          <label for="location">{{ t('calendarEvents.fields.location') }}</label>
          <InputText id="location" v-model="editForm.location" class="w-full" />
        </div>

        <div class="field-group">
          <div class="field">
            <label for="startTime">{{ t('calendarEvents.fields.startTime') }} *</label>
            <Calendar
              id="startTime"
              v-model="editForm.start_time"
              showTime
              hourFormat="24"
              dateFormat="dd/mm/yy"
              class="w-full"
            />
          </div>

          <div class="field">
            <label for="endTime">{{ t('calendarEvents.fields.endTime') }} *</label>
            <Calendar
              id="endTime"
              v-model="editForm.end_time"
              showTime
              hourFormat="24"
              dateFormat="dd/mm/yy"
              class="w-full"
            />
          </div>
        </div>
      </div>

      <template #footer>
        <Button
          :label="t('common.cancel')"
          icon="pi pi-times"
          class="p-button-text"
          @click="editDialogVisible = false"
        />
        <Button :label="t('common.save')" icon="pi pi-check" :loading="saving" @click="saveEvent" />
      </template>
    </Dialog>

    <Dialog
      v-model:visible="deleteDialogVisible"
      :header="t('calendarEvents.confirmDelete')"
      :modal="true"
      :closable="true"
      :style="{ width: '30vw' }"
    >
      <div class="delete-confirmation">
        <i class="pi pi-exclamation-triangle" style="font-size: 3rem; color: var(--red-500)"></i>
        <p>
          {{ t('calendarEvents.confirmDeleteMsg') }}
          <strong>{{ eventToDelete?.title }}</strong>?
        </p>
        <p class="warning-text">
          {{ t('calendarEvents.deleteWarning') }}
        </p>
      </div>

      <template #footer>
        <Button
          :label="t('common.cancel')"
          icon="pi pi-times"
          class="p-button-text"
          @click="deleteDialogVisible = false"
        />
        <Button
          :label="t('common.delete')"
          icon="pi pi-trash"
          class="p-button-danger"
          :loading="deleting"
          @click="performDelete"
        />
      </template>
    </Dialog>

    <Toast />
  </div>
</template>

<style scoped>
.calendar-events-view {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}

.header {
  margin-bottom: 2rem;
}

.title {
  font-size: 2rem;
  font-weight: 600;
  color: var(--vt-c-gray-900);
  margin-bottom: 0.5rem;
}

.subtitle {
  color: var(--vt-c-gray-500);
  font-size: 1rem;
  margin: 0;
  line-height: 1.5;
}

.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem 2rem;
  text-align: center;
}

.loading-state p {
  margin-top: 1rem;
  color: var(--vt-c-gray-600);
}

.empty-state i {
  font-size: 4rem;
  color: var(--vt-c-gray-400);
}

.empty-state h2 {
  margin-top: 1rem;
  color: var(--vt-c-gray-900);
  font-weight: 600;
}

.empty-state p {
  color: var(--vt-c-gray-600);
  max-width: 500px;
  margin-top: 0.5rem;
}

.error-state {
  margin: 2rem 0;
}

.events-container {
  margin-top: 2rem;
}

.filters {
  display: flex;
  gap: 1rem;
  margin-bottom: 2rem;
  flex-wrap: wrap;
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  flex: 1;
  min-width: 200px;
}

.filter-group label {
  font-weight: 500;
  color: var(--vt-c-gray-700);
  font-size: 0.9rem;
}

.event-card {
  background: var(--surface-card);
  border: 1px solid var(--surface-border);
  border-radius: 8px;
  padding: 1.5rem;
  margin-bottom: 1rem;
  transition: all 0.3s;
}

.event-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
}

.event-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
}

.event-title-group {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex: 1;
}

.event-title-group h3 {
  margin: 0;
  color: var(--vt-c-gray-900);
  font-size: 1.25rem;
  font-weight: 600;
}

.event-actions {
  display: flex;
  gap: 0.5rem;
}

.event-details {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.detail-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  color: var(--vt-c-gray-600);
}

.detail-row i {
  color: var(--vt-c-blue-primary);
  font-size: 1rem;
}

.google-sync {
  color: var(--vt-c-success);
  font-weight: 500;
}

.edit-form {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  padding: 1rem 0;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.field label {
  font-weight: 500;
  color: var(--vt-c-gray-700);
}

.field-group {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.delete-confirmation {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
  text-align: center;
}

.delete-confirmation p {
  margin: 0;
  color: var(--vt-c-gray-900);
}

.warning-text {
  color: var(--vt-c-gray-600);
  font-size: 0.9rem;
}

.w-full {
  width: 100%;
}

@media (max-width: 768px) {
  .calendar-events-view {
    padding: 1rem;
  }

  .filters {
    flex-direction: column;
  }

  .event-header {
    flex-direction: column;
    gap: 1rem;
  }

  .event-actions {
    width: 100%;
    justify-content: flex-end;
  }

  .field-group {
    grid-template-columns: 1fr;
  }
}
</style>
