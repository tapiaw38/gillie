<script setup lang="ts">
import { ref, reactive, watch, computed, onMounted } from 'vue'
import Card from 'primevue/card'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import LoadingSpinner from '@/components/core/LoadingSpinner/LoadingSpinner.vue'
import DefaultModal from '@/components/core/shared/DefaultModal/DefaultModal.vue'
import ScrollPanel from 'primevue/scrollpanel'
import Toast from 'primevue/toast'
import type { AssistantProfileParams, AssistantProfileUpdateParams } from '@/types/assistant.ts'
import { useToogle } from '@/composables/useToogle'
import { useAssistant } from '@/composables/useAssistant'
import { useConversation } from '@/composables/useConversation'
import { useErrorToast } from '@/composables/useErrorToast'

const { toogleValue: isVisible } = useToogle(false)
const { toogleValue: isVisibleUpdate } = useToogle(false)

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

const errorWatchers = [
  {
    flag: isAddAssistantProfileError,
    summary: 'Error al agregar asistente',
    detail: addAssistantProfileError,
  },
  {
    flag: isUpdateAssistantProfileError,
    summary: 'Error al actualizar asistente',
    detail: updateAssistantProfileError,
  },
  {
    flag: isGetAssistantProfileError,
    summary: 'Error al obtener perfil de asistente',
    detail: getAssistantProfileError,
  },
  {
    flag: isGetUserConversationError,
    summary: 'Error al obtener conversaciones',
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
  } catch (error) {
    console.error('Error loading dashboard data:', error)
  }
})

const modalTitle = ref('Agregar Asistente')
const changeVisible = (value: boolean) => {
  isVisible.value = value
}

const assistantProfileParams = reactive<AssistantProfileParams>({
  assistant_name: '',
  business_name: '',
  functions: '',
  business_context: '',
})

const addAssistant = async () => {
  await addAssistantProfile(assistantProfileParams)
  if (isAddAssistantProfileSuccess.value) {
    await getAssistantProfile()
    toast.add({
      severity: 'success',
      summary: 'Asistente agregado',
      detail: 'El asistente se creó correctamente',
      life: 3000,
    })
  }
  isVisible.value = false
}

const modalTitleUpdate = ref('Editar Asistente')
const updateAssistantProfileParams = reactive<AssistantProfileUpdateParams>({
  assistant_name: '',
  business_name: '',
  functions: '',
  business_context: '',
})

const changeUpdateVisible = (value: boolean) => {
  isVisibleUpdate.value = value
}

const updateAssistan = async () => {
  await updateAssistantProfile(updateAssistantProfileParams)
  if (isUpdateAssistantProfileSuccess.value) {
    await getAssistantProfile()
    toast.add({
      severity: 'success',
      summary: 'Asistente actualizado',
      detail: 'El asistente se actualizó correctamente',
      life: 3000,
    })
  }
  isVisibleUpdate.value = false
}

watch(
  isVisibleUpdate,
  () => {
    if (assistantProfile && isVisibleUpdate.value) {
      updateAssistantProfileParams.assistant_name = assistantProfile?.value?.assistant_name || ''
      updateAssistantProfileParams.business_name = assistantProfile?.value?.business_name || ''
      updateAssistantProfileParams.functions = assistantProfile?.value?.functions || ''
      updateAssistantProfileParams.business_context =
        assistantProfile?.value?.business_context || ''
    }
  },
  { immediate: true },
)

const totalMessagesInConversation = computed(() => {
  return conversations.value?.reduce((acc, curr) => {
    return acc + (curr?.messages?.length || 0)
  }, 0)
})

const integrations = [
  {
    name: 'Storage',
    description: 'Integración con almacenamiento de archivos en la nube',
    icon: 'pi pi-file',
    color: 'text-primary',
    to: 'store-integration',
    enabled: true,
  },
  {
    name: 'WhatsApp (Meta API)',
    description: 'Integración WhatsApp con Meta Business API oficial',
    icon: 'pi pi-whatsapp',
    color: 'text-green-500',
    to: 'whatsapp-integration',
    enabled: true,
  },
  {
    name: 'WhatsApp Devices',
    description: 'Gestión de dispositivos WhatsApp con respuestas automáticas de IA',
    icon: 'pi pi-whatsapp',
    color: 'text-green-500',
    to: 'whatsapp-devices',
    enabled: true,
  },
  {
    name: 'Mercado Libre',
    description: 'Integración Mercado Libre, Contestar preguntas sin responder',
    icon: 'pi pi-chat',
    color: 'text-green-500',
    to: 'meli-integration',
    enabled: false,
  },
  {
    name: 'Google Calendar',
    description: 'Integración Google Calendar, gestiona eventos y sincronización',
    icon: 'pi pi-calendar',
    color: 'text-yellow-500',
    to: 'google-calendar-integration',
    enabled: true,
  },
  {
    name: 'Google Drive',
    description: 'Integración Google Drive, accede a documentos y archivos desde el asistente',
    icon: 'pi pi-folder-open',
    color: 'text-blue-500',
    to: 'google-drive-integration',
    enabled: true,
  },
  {
    name: 'Funciones',
    description: 'Editor de funciones personalizadas para el asistente',
    icon: 'pi pi-code',
    color: 'text-primary',
    to: 'functions',
    enabled: true,
  },
]
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
          <h1 class="dashboard-title">Dashboard</h1>
          <p class="dashboard-subtitle">Gestiona tu asistente y revisa el rendimiento</p>
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
                <p>Cargando perfil del asistente...</p>
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
                <h3>No hay asistente configurado</h3>
                <p>Crea tu primer asistente para comenzar</p>
                <Button
                  label="Crear Asistente"
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
                  <h3>{{ assistantProfile?.assistant_name }}</h3>
                  <p>Asistente Virtual</p>
                </div>
              </div>
              <Button
                icon="pi pi-pencil"
                class="edit-button"
                size="small"
                @click="isVisibleUpdate = true"
                title="Editar asistente"
              />
            </div>
          </template>
          <template #content>
            <div class="profile-content">
              <div class="info-item">
                <label>Empresa</label>
                <span>{{ assistantProfile?.business_name }}</span>
              </div>
              <div class="info-item">
                <label>Contexto de Negocio</label>
                <ScrollPanel class="context-scroll">
                  <p>{{ assistantProfile?.business_context }}</p>
                </ScrollPanel>
              </div>
              <div class="profile-actions">
                <RouterLink class="sandbox-button" :to="{ name: 'sandbox' }">
                  <i class="pi pi-shield"></i>
                  Sandbox Testing
                </RouterLink>
              </div>
            </div>
          </template>
        </Card>

        <!-- Stats Card -->
        <Card v-if="isGetUserConversationSuccess" class="stats-card p-2">
          <template #header>
            <div class="stats-header">
              <div class="stats-icon">
                <i class="pi pi-chart-bar"></i>
              </div>
              <div class="stats-info">
                <h3>Estadísticas</h3>
                <p>Resumen de actividad</p>
              </div>
            </div>
          </template>
          <template #content>
            <div class="stats-grid">
              <div class="stat-item">
                <div class="stat-value">{{ conversations?.length || 0 }}</div>
                <div class="stat-label">Conversaciones</div>
                <div class="stat-icon">
                  <i class="pi pi-comments"></i>
                </div>
              </div>
              <div class="stat-item">
                <div class="stat-value">{{ totalMessagesInConversation || 0 }}</div>
                <div class="stat-label">Mensajes</div>
                <div class="stat-icon">
                  <i class="pi pi-envelope"></i>
                </div>
              </div>
              <div class="stat-item">
                <div class="stat-value">{{ assistantProfile?.iteration_limit || 0 }}</div>
                <div class="stat-label">Iteraciones Restantes</div>
                <div class="stat-icon">
                  <i class="pi pi-clock"></i>
                </div>
              </div>
            </div>
            <div class="stats-actions">
              <RouterLink class="view-conversations-button" :to="{ name: 'conversation' }">
                <i class="pi pi-eye"></i>
                Ver Conversaciones
              </RouterLink>
            </div>
          </template>
        </Card>
      </div>

      <!-- Integrations Section -->
      <div class="integrations-section">
        <div class="section-header">
          <h2>Integraciones Disponibles</h2>
          <p>Conecta tu asistente con diferentes plataformas</p>
        </div>

        <div class="integrations-grid">
          <Card
            v-for="integration in integrations"
            :key="integration.name"
            class="integration-card"
            :class="{
              'integration-enabled': integration.enabled,
              'integration-disabled': !integration.enabled,
            }"
          >
            <template #content>
              <div class="integration-content">
                <div class="integration-header">
                  <div
                    class="integration-icon"
                    :class="integration.enabled ? integration.color : 'disabled'"
                  >
                    <i :class="integration.icon"></i>
                  </div>
                  <div class="integration-status">
                    <span v-if="integration.enabled" class="status-badge enabled">Disponible</span>
                    <span v-else class="status-badge disabled">Próximamente</span>
                  </div>
                </div>

                <div class="integration-info">
                  <h3>{{ integration.name }}</h3>
                  <p>{{ integration.description }}</p>
                </div>

                <div class="integration-actions">
                  <Button
                    v-if="integration.enabled"
                    label="Configurar"
                    severity="primary"
                    :link="true"
                    @click="$router.push({ name: integration.to })"
                  />
                  <Button v-else label="Próximamente" disabled />
                </div>
              </div>
            </template>
          </Card>
        </div>
      </div>
    </div>

    <!-- Modals -->
    <DefaultModal :isVisible="isVisible" :title="modalTitle" @update:visible="changeVisible">
      <form @submit.prevent="addAssistant" class="modal-form">
        <div class="form-field">
          <label for="assistant_name">Nombre del Asistente</label>
          <InputText
            id="assistant_name"
            v-model="assistantProfileParams.assistant_name"
            placeholder="Ingresa el nombre del asistente"
            required
          />
        </div>

        <div class="form-field">
          <label for="business_name">Nombre de la Empresa</label>
          <InputText
            id="business_name"
            v-model="assistantProfileParams.business_name"
            placeholder="Ingresa el nombre de la empresa"
            required
          />
        </div>

        <div class="form-field">
          <label for="business_context">Contexto del Negocio</label>
          <Textarea
            id="business_context"
            v-model="assistantProfileParams.business_context"
            placeholder="Describe el contexto de tu negocio"
            rows="4"
            required
          />
        </div>

        <div class="modal-actions">
          <Button
            type="button"
            label="Cancelar"
            severity="secondary"
            @click="() => changeVisible(false)"
          />
          <Button type="submit" label="Crear Asistente" :loading="isAddAssistantProfilePending" />
        </div>
      </form>
    </DefaultModal>

    <DefaultModal
      :isVisible="isVisibleUpdate"
      :title="modalTitleUpdate"
      @update:visible="changeUpdateVisible"
    >
      <form @submit.prevent="updateAssistan" class="modal-form">
        <div class="form-field">
          <label for="update_assistant_name">Nombre del Asistente</label>
          <InputText
            id="update_assistant_name"
            v-model="updateAssistantProfileParams.assistant_name"
            placeholder="Ingresa el nombre del asistente"
            required
          />
        </div>

        <div class="form-field">
          <label for="update_business_name">Nombre de la Empresa</label>
          <InputText
            id="update_business_name"
            v-model="updateAssistantProfileParams.business_name"
            placeholder="Ingresa el nombre de la empresa"
            required
          />
        </div>

        <div class="form-field">
          <label for="update_business_context">Contexto del Negocio</label>
          <Textarea
            id="update_business_context"
            v-model="updateAssistantProfileParams.business_context"
            placeholder="Describe el contexto de tu negocio"
            rows="4"
            required
          />
        </div>

        <div class="modal-actions">
          <Button
            type="button"
            label="Cancelar"
            severity="secondary"
            @click="() => changeUpdateVisible(false)"
          />
          <Button
            type="submit"
            label="Actualizar Asistente"
            :loading="isUpdateAssistantProfilePending"
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
  padding: 2rem;
  padding-top: calc(3.5rem + 1.5rem);
  min-height: 100vh;
  background: var(--do-bg);
}

/* Header Section */
.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
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
  width: 4rem;
  height: 4rem;
  border-radius: 0.75rem;
  background: var(--gradient-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 1.5rem;
  box-shadow: 0 4px 14px rgba(0, 105, 255, 0.3);
}

.title-section {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.dashboard-title {
  font-size: 2.25rem;
  font-weight: 800;
  color: var(--do-text);
  margin: 0;
  line-height: 1.2;
}

.dashboard-subtitle {
  font-size: 1.125rem;
  color: var(--do-text-muted);
  margin: 0;
  line-height: 1.5;
}

/* Content Grid */
.content-grid {
  display: flex;
  flex-direction: column;
  gap: 2rem;
  margin-bottom: 2rem;
}

/* Profile Section */
.profile-section {
  display: flex;
  flex-direction: row;
  gap: 1.5rem;
  align-items: flex-start;
}

.profile-section > * {
  flex: 1;
  min-width: 0;
}

.section-header {
  text-align: center;
  margin-bottom: 2rem;
}

.section-header h2 {
  font-size: 2rem;
  font-weight: 700;
  color: var(--do-text);
  margin-bottom: 0.75rem;
}

.section-header p {
  font-size: 1.125rem;
  color: var(--do-text-muted);
  line-height: 1.6;
}

.integrations-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 1.5rem;
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
  gap: 1rem;
}

.profile-icon {
  width: 3rem;
  height: 3rem;
  border-radius: 0.75rem;
  background: var(--gradient-success);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--vt-c-white);
  font-size: 1.25rem;
}

.profile-details h3 {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--do-text);
  margin: 0 0 0.25rem 0;
}

.profile-details p {
  color: var(--do-text-muted);
  margin: 0;
}

.profile-content {
  display: flex;
  flex-direction: column;
  gap: 1rem;
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
  max-height: 150px;
}

.context-scroll p {
  margin: 0;
  color: var(--do-text-muted);
  line-height: 1.6;
}

.profile-actions {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid var(--do-border-light);
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.sandbox-button {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  color: white;
  text-decoration: none;
  border-radius: 0.75rem;
  font-weight: 600;
  font-size: 0.95rem;
  transition: all 0.3s ease;
  flex: 1;
  justify-content: center;
  min-width: fit-content;
}

.sandbox-button {
  background: linear-gradient(135deg, #F5A623 0%, #D4891A 100%);
  box-shadow: 0 4px 15px rgba(245, 166, 35, 0.3);
}

.sandbox-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 30px rgba(245, 166, 35, 0.4);
  color: white;
}

.sandbox-button i {
  font-size: 1.1rem;
}

/* Stats Card */
.stats-header {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.stats-icon {
  width: 3rem;
  height: 3rem;
  border-radius: 0.75rem;
  background: var(--gradient-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 1.25rem;
}

.stats-info h3 {
  font-size: 1.5rem;
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
  gap: 1.5rem;
  margin-bottom: 1.5rem;
}

.stat-item {
  text-align: center;
  padding: 1rem;
  background: var(--do-bg);
  border-radius: 0.75rem;
  border: 1px solid var(--do-border-light);
  position: relative;
}

.stat-value {
  font-size: 2rem;
  font-weight: 800;
  color: var(--do-text);
  margin-bottom: 0.5rem;
}

.stat-label {
  font-size: 0.875rem;
  color: var(--do-text-muted);
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
  padding: 0.75rem 1.5rem;
  background: var(--gradient-primary);
  color: white;
  text-decoration: none;
  border-radius: 0.75rem;
  font-weight: 600;
  font-size: 1rem;
  transition: all 0.3s ease;
  box-shadow: 0 4px 14px rgba(0, 105, 255, 0.3);
}

.view-conversations-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 30px rgba(0, 105, 255, 0.4);
  color: white;
}

/* Integration Cards */
.integration-content {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.integration-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.integration-icon {
  width: 3rem;
  height: 3rem;
  border-radius: 0.75rem;
  background: var(--do-bg);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.25rem;
  border: 1px solid var(--do-border-light);
}

.integration-icon.text-primary {
  color: var(--do-blue);
}

.integration-icon.text-green-500 {
  color: var(--do-success);
}

.integration-icon.text-yellow-500 {
  color: var(--do-warning);
}

.integration-icon.disabled {
  color: var(--do-text-muted);
  background: var(--do-border-light);
}

.integration-status {
  display: flex;
  gap: 0.5rem;
}

.status-badge {
  padding: 0.25rem 0.75rem;
  border-radius: 1rem;
  font-size: 0.75rem;
  font-weight: 600;
}

.status-badge.enabled {
  background: rgba(10, 207, 131, 0.1);
  color: var(--do-success);
  border: 1px solid rgba(10, 207, 131, 0.2);
}

.status-badge.disabled {
  background: rgba(140, 144, 152, 0.1);
  color: var(--do-text-muted);
  border: 1px solid rgba(140, 144, 152, 0.2);
}

.integration-info h3 {
  margin: 0 0 0.5rem 0;
  font-size: 1.125rem;
  font-weight: 700;
  color: var(--do-text);
}

.integration-info p {
  margin: 0;
  color: var(--do-text-muted);
  line-height: 1.5;
  font-size: 0.875rem;
}

.integration-actions {
  margin-top: auto;
}

/* Loading and Empty States */
.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  text-align: center;
  padding: 2rem;
}

.loading-state p,
.empty-state p {
  color: var(--do-text-muted);
  margin: 0;
}

.empty-state i {
  font-size: 3rem;
  color: var(--do-blue);
}

.empty-state h3 {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--do-text);
  margin: 0;
}

.create-button {
  background: var(--gradient-success);
  border: none;
  color: var(--vt-c-white);
  padding: 0.75rem 1.5rem;
  border-radius: 0.75rem;
  font-weight: 600;
  font-size: 1rem;
  transition: all 0.3s ease;
  box-shadow: 0 4px 14px rgba(10, 207, 131, 0.3);
}

.create-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 30px rgba(10, 207, 131, 0.4);
}

/* Modal Styles */
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

:deep(.form-field .p-inputtext),
:deep(.form-field .p-inputtextarea) {
  border: 2px solid var(--do-border-light);
  border-radius: 0.5rem;
  padding: 0.75rem;
  transition: all 0.3s ease;
}

:deep(.form-field .p-inputtext:focus),
:deep(.form-field .p-inputtextarea:focus) {
  border-color: var(--do-blue);
  box-shadow: 0 0 0 3px rgba(0, 105, 255, 0.1);
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  padding-top: 1rem;
  border-top: 1px solid var(--do-border-light);
}

/* Responsive Design */
@media (max-width: 768px) {
  .dashboard-container {
    padding: 1rem;
    padding-top: calc(3.5rem + 1rem);
  }

  .dashboard-header {
    flex-direction: column;
    gap: 1rem;
    text-align: center;
    padding: 1.25rem;
  }

  .header-content {
    flex-direction: column;
    gap: 1rem;
  }

  .dashboard-title {
    font-size: 2rem;
  }

  .dashboard-subtitle {
    font-size: 1rem;
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
    gap: 1rem;
  }

  .section-header h2 {
    font-size: 1.75rem;
  }

  .section-header p {
    font-size: 1rem;
  }
}

@media (max-width: 480px) {
  .dashboard-container {
    padding: 0.5rem;
    padding-top: calc(3.5rem + 0.75rem);
  }

  .icon-wrapper {
    width: 3rem;
    height: 3rem;
    font-size: 1.25rem;
  }

  .dashboard-title {
    font-size: 1.75rem;
  }

  .dashboard-header {
    padding: 1rem;
  }

  :deep(.loading-card .p-card-content),
  :deep(.empty-card .p-card-content),
  :deep(.profile-card .p-card-content),
  :deep(.stats-card .p-card-content),
  :deep(.integration-card .p-card-content) {
    padding: 1.25rem;
  }

  :deep(.profile-card .p-card-header),
  :deep(.stats-card .p-card-header) {
    padding: 1rem 1.25rem;
  }
}
</style>
