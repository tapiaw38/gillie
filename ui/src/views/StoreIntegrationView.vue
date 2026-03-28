<script setup lang="ts">
import Card from 'primevue/card'
import FileUpload from '@/components/core/FileUpload/FileUpload.vue'
import LoadingSpinner from '@/components/core/LoadingSpinner/LoadingSpinner.vue'
import Toast from 'primevue/toast'
import { useAssistant } from '@/composables/useAssistant'
import { useErrorToast } from '@/composables/useErrorToast'
import { onMounted, watch } from 'vue'

const {
  assistantProfile,
  getAssistantProfile,
  removeFileById,

  isGetAssistantProfilePending,
  isGetAssistantProfileError,
  getAssistantProfileError,

  isRemoveFileByIdPending,
  isRemoveFileByIdSuccess,
  isRemoveFileByIdError,
  removeFileByIdError,
} = useAssistant()

const errorWatchers = [
  {
    flag: isRemoveFileByIdError,
    summary: 'Error al eliminar archivo',
    detail: removeFileByIdError,
  },
  {
    flag: isGetAssistantProfileError,
    summary: 'Error al cargar archivos',
    detail: getAssistantProfileError,
  },
]

const { toast } = useErrorToast(errorWatchers)

onMounted(() => {
  getAssistantProfile()
})

watch(isRemoveFileByIdSuccess, (value) => {
  if (value) {
    toast.add({
      severity: 'success',
      summary: 'Archivo eliminado',
      detail: 'El archivo se eliminó correctamente',
      life: 3000,
    })
  }
})

const removeFile = async (fileId: string) => {
  try {
    await removeFileById(fileId)
    if (isRemoveFileByIdSuccess.value) {
      await getAssistantProfile()
    }
  } catch (error) {
    console.error('Error al eliminar el archivo:', error)
  }
}
</script>

<template>
  <div class="integration-container">
    <!-- Header Section -->
    <div class="header-section">
      <div class="integration-header">
        <div class="icon-wrapper storage-icon">
          <i class="pi pi-cloud"></i>
        </div>
        <div class="header-content">
          <h1 class="integration-title">Integración de Almacenamiento</h1>
          <p class="integration-subtitle">
            Gestiona archivos para que tu asistente pueda acceder a ellos
          </p>
        </div>
      </div>
    </div>

    <!-- Info Card -->
    <Card class="info-card">
      <template #content>
        <div class="info-content">
          <div class="info-icon">
            <i class="pi pi-info-circle"></i>
          </div>
          <div class="info-text">
            <h3>¿Cómo funciona?</h3>
            <p>
              Sube archivos que tu asistente podrá consultar y utilizar para responder preguntas más
              precisas. Los archivos se almacenan de forma segura y están disponibles solo para tu
              asistente.
            </p>
          </div>
        </div>
      </template>
    </Card>

    <!-- Main Content Grid -->
    <div class="content-grid">
      <!-- Upload Section -->
      <Card class="upload-card">
        <template #header>
          <div class="card-header">
            <div class="header-icon upload-header-icon">
              <i class="pi pi-cloud-upload"></i>
            </div>
            <div class="header-text">
              <h3>Subir Archivos</h3>
              <p>Arrastra archivos o haz clic para seleccionar</p>
            </div>
          </div>
        </template>
        <template #content>
          <div class="upload-content">
            <FileUpload />
          </div>
        </template>
      </Card>

      <!-- Files List Section -->
      <Card class="files-card">
        <template #header>
          <div class="card-header">
            <div class="header-icon files-header-icon">
              <i class="pi pi-file"></i>
            </div>
            <div class="header-text">
              <h3>Archivos Almacenados</h3>
              <p>{{ assistantProfile?.files?.length || 0 }} archivo(s) disponible(s)</p>
            </div>
          </div>
        </template>
        <template #content>
          <div class="files-content">
            <!-- Loading State -->
            <div v-if="isGetAssistantProfilePending" class="loading-state">
              <LoadingSpinner />
              <p>Cargando archivos...</p>
            </div>

            <!-- Error State -->
            <div v-else-if="isGetAssistantProfileError" class="error-state">
              <i class="pi pi-exclamation-triangle"></i>
              <p>Error al cargar los archivos</p>
              <small>{{ getAssistantProfileError }}</small>
            </div>

            <!-- Files List -->
            <div v-else-if="assistantProfile?.files?.length" class="files-list">
              <div v-for="(file, index) in assistantProfile.files" :key="index" class="file-item">
                <div class="file-info">
                  <div class="file-icon">
                    <i class="pi pi-file-o"></i>
                  </div>
                  <div class="file-details">
                    <a :href="file.url" target="_blank" rel="noopener noreferrer" class="file-name">
                      {{ file.name }}
                    </a>
                    <span class="file-meta">Archivo disponible para el asistente</span>
                  </div>
                </div>
                <button
                  class="delete-button"
                  @click="removeFile(file.id)"
                  :disabled="isRemoveFileByIdPending"
                  title="Eliminar archivo"
                >
                  <i class="pi pi-trash"></i>
                </button>
              </div>

              <!-- Remove File Loading -->
              <div v-if="isRemoveFileByIdPending" class="action-loading">
                <LoadingSpinner />
                <p>Eliminando archivo...</p>
              </div>

              <!-- Remove File Error -->
              <div v-if="isRemoveFileByIdError" class="action-error">
                <i class="pi pi-exclamation-triangle"></i>
                <p>Error al eliminar el archivo</p>
                <small>{{ removeFileByIdError }}</small>
              </div>
            </div>

            <!-- Empty State -->
            <div v-else class="empty-state">
              <i class="pi pi-folder-open"></i>
              <h4>No hay archivos almacenados</h4>
              <p>Sube tu primer archivo para comenzar</p>
            </div>
          </div>
        </template>
      </Card>
    </div>

    <!-- Toast for Notifications -->
    <Toast position="top-right" />
  </div>
</template>

<style scoped>
.integration-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
  min-height: 100vh;
  background: var(--do-bg);
}

/* Header Section */
.header-section {
  margin-bottom: 2rem;
}

.integration-header {
  display: flex;
  align-items: center;
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.icon-wrapper {
  width: 4rem;
  height: 4rem;
  border-radius: 1rem;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 2rem;
  color: white;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
}

.storage-icon {
  background: var(--gradient-primary);
}

.header-content {
  flex: 1;
}

.integration-title {
  font-size: 1.6rem;
  font-weight: 700;
  margin: 0 0 0.5rem 0;
  color: var(--do-text);
}

.integration-subtitle {
  font-size: 1.125rem;
  color: var(--do-text-muted);
  margin: 0;
  font-weight: 400;
}

/* Info Card */
.info-card {
  margin-bottom: 2rem;
  border-radius: 1rem;
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
  border: 1px solid var(--vt-c-gray-200);
  background: rgba(59,130,246,0.08);
}

:deep(.info-card .p-card-content) {
  padding: 1.5rem 2rem;
}

.info-content {
  display: flex;
  align-items: flex-start;
  gap: 1rem;
}

.info-icon {
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 0.75rem;
  background: var(--color-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 1.25rem;
  flex-shrink: 0;
}

.info-text h3 {
  margin: 0 0 0.5rem 0;
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--color-primary-dark);
}

.info-text p {
  margin: 0;
  color: var(--color-primary-dark);
  line-height: 1.6;
}

/* Content Grid */
.content-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2rem;
}

/* Card Headers */
.card-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1.5rem 2rem;
}

.header-icon {
  width: 3rem;
  height: 3rem;
  border-radius: 0.75rem;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.25rem;
  color: white;
}

.upload-header-icon {
  background: var(--gradient-success);
}

.files-header-icon {
  background: var(--gradient-primary);
}

.header-text h3 {
  margin: 0 0 0.25rem 0;
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--do-text);
}

.header-text p {
  margin: 0;
  font-size: 0.875rem;
  color: var(--do-text-muted);
}

/* Upload Card */
.upload-card {
  border-radius: 1rem;
  overflow: hidden;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
  border: 1px solid var(--vt-c-gray-200);
  transition: all 0.3s ease;
}

.upload-card:hover {
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
  transform: translateY(-2px);
}

:deep(.upload-card .p-card-header) {
  background: rgba(16,185,129,0.08);
  border-bottom: 1px solid var(--vt-c-gray-200);
}

:deep(.upload-card .p-card-content) {
  padding: 2rem;
}

.upload-content {
  min-height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Files Card */
.files-card {
  border-radius: 1rem;
  overflow: hidden;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
  border: 1px solid var(--vt-c-gray-200);
  transition: all 0.3s ease;
}

.files-card:hover {
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
  transform: translateY(-2px);
}

:deep(.files-card .p-card-header) {
  background: rgba(139,92,246,0.08);
  border-bottom: 1px solid var(--vt-c-gray-200);
}

:deep(.files-card .p-card-content) {
  padding: 2rem;
}

.files-content {
  min-height: 200px;
}

/* States */
.loading-state,
.error-state,
.empty-state,
.action-loading,
.action-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 2rem;
  gap: 1rem;
}

.loading-state i,
.error-state i,
.empty-state i {
  font-size: 3rem;
  color: var(--do-text-secondary);
}

.error-state i,
.action-error i {
  color: var(--color-danger);
}

.loading-state p,
.error-state p,
.empty-state p,
.action-loading p,
.action-error p {
  margin: 0;
  color: var(--do-text-muted);
  font-weight: 500;
}

.empty-state h4 {
  margin: 0;
  color: var(--do-text);
  font-weight: 600;
}

.error-state small,
.action-error small {
  color: var(--color-danger);
  font-size: 0.75rem;
}

/* Files List */
.files-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.file-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem;
  background: rgba(255,255,255,0.04);
  border-radius: 0.75rem;
  border: 1px solid var(--vt-c-gray-200);
  transition: all 0.3s ease;
}

.file-item:hover {
  background: rgba(255,255,255,0.07);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
  transform: translateY(-1px);
}

.file-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex: 1;
  min-width: 0;
}

.file-icon {
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 0.5rem;
  background: var(--gradient-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 1rem;
  flex-shrink: 0;
}

.file-details {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  min-width: 0;
}

.file-name {
  font-weight: 600;
  color: var(--do-text);
  text-decoration: none;
  font-size: 0.875rem;
  word-break: break-all;
  transition: color 0.3s ease;
}

.file-name:hover {
  color: var(--color-primary);
}

.file-meta {
  font-size: 0.75rem;
  color: var(--do-text-muted);
}

.delete-button {
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 0.5rem;
  border: none;
  background: rgba(255,68,68,0.15);
  color: #fca5a5;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.3s ease;
  flex-shrink: 0;
}

.delete-button:hover:not(:disabled) {
  background: rgba(255,68,68,0.25);
  transform: scale(1.05);
}

.delete-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.action-loading,
.action-error {
  margin-top: 1rem;
  padding: 1rem;
  background: rgba(255,255,255,0.04);
  border-radius: 0.75rem;
  border: 1px solid var(--vt-c-gray-200);
}

/* Responsive Design */
@media (max-width: 768px) {
  .integration-container {
    padding: 1rem;
  }

  .integration-header {
    flex-direction: column;
    text-align: center;
    gap: 1rem;
  }

  .integration-title {
    font-size: 2rem;
  }

  .integration-subtitle {
    font-size: 1rem;
  }

  .content-grid {
    grid-template-columns: 1fr;
    gap: 1.5rem;
  }

  .card-header {
    padding: 1rem 1.5rem;
  }

  :deep(.upload-card .p-card-content),
  :deep(.files-card .p-card-content) {
    padding: 1.5rem;
  }

  :deep(.info-card .p-card-content) {
    padding: 1rem 1.5rem;
  }

  .info-content {
    flex-direction: column;
    text-align: center;
  }

  .file-item {
    flex-direction: column;
    gap: 1rem;
    align-items: stretch;
  }

  .file-info {
    justify-content: center;
  }

  .delete-button {
    align-self: center;
  }
}

@media (max-width: 480px) {
  .integration-container {
    padding: 0.5rem;
  }

  .icon-wrapper {
    width: 3rem;
    height: 3rem;
    font-size: 1.5rem;
  }

  .integration-title {
    font-size: 1.75rem;
  }

  .card-header {
    padding: 1rem;
  }

  .header-icon {
    width: 2.5rem;
    height: 2.5rem;
    font-size: 1rem;
  }

  :deep(.upload-card .p-card-content),
  :deep(.files-card .p-card-content),
  :deep(.info-card .p-card-content) {
    padding: 1rem;
  }
}
</style>
