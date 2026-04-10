<script setup lang="ts">
import { ref, watch } from 'vue'
import { usePrimeVue } from 'primevue/config'
import type { FileUploadSelectEvent } from 'primevue/fileupload'
import FileUpload from 'primevue/fileupload'
import Button from 'primevue/button'
import ProgressBar from 'primevue/progressbar'
import Badge from 'primevue/badge'
import Toast from 'primevue/toast'
import type { UploadFile } from './types'
import { useAssistant } from '../../../composables/useAssistant'
import { useErrorToast } from '../../../composables/useErrorToast'

const { addFiles, addFilesError, isAddFilesPending, isAddFilesSuccess, isAddFilesError } =
  useAssistant()

const errorWatchers = [
  {
    flag: isAddFilesError,
    summary: 'Error al subir archivos',
    detail: addFilesError,
  },
]

const { toast } = useErrorToast(errorWatchers)

watch(isAddFilesSuccess, (value) => {
  if (value) {
    toast.add({
      severity: 'success',
      summary: 'Archivos subidos',
      detail: 'Los archivos se subieron correctamente',
      life: 3000,
    })
  }
})

const $primevue = usePrimeVue()

const totalSize = ref(0)
const totalSizePercent = ref(0)
const selectedFiles = ref<File[]>([])

const allowedTypes = [
  'application/pdf',
  'application/vnd.ms-excel',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
]

const onRemoveTemplatingFile = (
  file: UploadFile,
  removeFileCallback: (index: number) => void,
  index: number,
) => {
  if (file.objectURL) {
    URL.revokeObjectURL(file.objectURL)
  }
  removeFileCallback(index)
  totalSize.value -= file.size
  totalSizePercent.value = totalSize.value
}

const onSelectedFiles = (event: FileUploadSelectEvent) => {
  totalSize.value = 0
  const filtered = event.files.filter((file: UploadFile) => allowedTypes.includes(file.type))

  if (filtered.length !== event.files.length) {
    toast.add({
      severity: 'warn',
      summary: 'Tipos de archivo no válidos',
      detail: 'Solo se permiten archivos PDF y Excel (.xls, .xlsx).',
      life: 4000,
    })
  }

  const maxFileSize = 262144000 // 250 MiB (250 * 1024 * 1024)
  const oversizedFiles = filtered.filter((file: UploadFile) => file.size > maxFileSize)

  if (oversizedFiles.length > 0) {
    toast.add({
      severity: 'error',
      summary: 'Archivos demasiado grandes',
      detail: `Los siguientes archivos superan el límite de 250 MiB: ${oversizedFiles
        .map((f: UploadFile) => f.name)
        .join(', ')}`,
      life: 5000,
    })
    return
  }

  if (filtered.length > 0) {
    toast.add({
      severity: 'info',
      summary: 'Archivos seleccionados',
      detail: `${filtered.length} archivo(s) seleccionado(s) correctamente`,
      life: 3000,
    })
  }

  filtered.forEach((file: UploadFile) => {
    file.objectURL = URL.createObjectURL(file)
    totalSize.value += file.size
  })

  totalSizePercent.value = totalSize.value
  selectedFiles.value = filtered
}

const uploadEvent = async (uploadCallback: () => void, clearCallback: () => void) => {
  if (selectedFiles.value.length > 0) {
    try {
      await addFiles(selectedFiles.value)
      clearCallback()
    } catch (error) {
      console.error('Error uploading files:', error + ' - ', addFilesError.value)
    }
  }
  uploadCallback()
}

const onTemplatedUpload = () => {}

const formatSize = (bytes: number) => {
  const k = 1024
  const dm = 2
  const sizes = $primevue.config?.locale?.fileSizeTypes || ['B', 'KB', 'MB', 'GB', 'TB']

  if (bytes === 0) {
    return `0 ${sizes[0]}`
  }

  const i = Math.floor(Math.log(bytes) / Math.log(k))
  const formattedSize = parseFloat((bytes / Math.pow(k, i)).toFixed(dm))

  return `${formattedSize} ${sizes[i]}`
}
</script>

<template>
  <div class="card">
    <FileUpload
      name="demo[]"
      @upload="onTemplatedUpload"
      :multiple="true"
      accept=".pdf,application/pdf,application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
      :maxFileSize="262144000"
      @select="onSelectedFiles"
    >
      <template #header="{ chooseCallback, uploadCallback, clearCallback, files }">
        <div class="flex flex-wrap justify-between items-center flex-1 gap-4">
          <div class="flex gap-2">
            <Button
              @click="chooseCallback()"
              icon="pi pi-file"
              rounded
              outlined
              severity="secondary"
            />
            <Button
              @click="uploadEvent(uploadCallback, clearCallback)"
              icon="pi pi-cloud-upload"
              rounded
              outlined
              severity="success"
              :disabled="!files || files.length === 0 || isAddFilesPending"
              :loading="isAddFilesPending"
            />
            <Button
              @click="clearCallback()"
              icon="pi pi-times"
              rounded
              outlined
              severity="danger"
              :disabled="!files || files.length === 0"
            />
          </div>
          <ProgressBar
            :value="totalSizePercent"
            :showValue="false"
            class="md:w-20rem h-1 w-full md:ml-auto"
          >
            <span class="whitespace-nowrap">{{ formatSize(totalSize) }}</span>
          </ProgressBar>
        </div>
      </template>

      <template #content="{ files, uploadedFiles, removeUploadedFileCallback, removeFileCallback }">
        <div class="flex flex-col gap-8 pt-4">
          <div v-if="files.length > 0">
            <h5>Pending</h5>
            <div class="flex flex-wrap gap-4">
              <div
                v-for="(file, index) of files"
                :key="file.name + file.type + file.size"
                class="file-card p-3 rounded-border flex flex-col border border-surface items-center gap-2"
              >
                <div>
                  <img
                    role="presentation"
                    :alt="file.name"
                    :src="(file as any).objectURL"
                    width="100"
                    height="50"
                  />
                </div>
                <span
                  class="font-semibold text-ellipsis max-w-60 whitespace-nowrap overflow-hidden"
                  >{{ file.name }}</span
                >
                <div>{{ formatSize(file.size) }}</div>
                <Badge value="Pending" severity="warn" />
                <Button
                  icon="pi pi-times"
                  @click="onRemoveTemplatingFile(file as any, removeFileCallback, index)"
                  outlined
                  rounded
                  severity="danger"
                />
              </div>
            </div>
          </div>

          <div v-if="uploadedFiles.length > 0">
            <h5>Completed</h5>
            <div class="flex flex-wrap gap-4">
              <div
                v-for="(file, index) of uploadedFiles"
                :key="file.name + file.type + file.size"
                class="file-card p-3 rounded-border flex flex-col border border-surface items-center gap-2"
              >
                <div>
                  <img
                    role="presentation"
                    :alt="file.name"
                    :src="(file as any).objectURL"
                    width="100"
                    height="50"
                  />
                </div>
                <span
                  class="font-semibold text-ellipsis max-w-60 whitespace-nowrap overflow-hidden"
                  >{{ file.name }}</span
                >
                <div>{{ formatSize(file.size) }}</div>
                <Badge value="Completed" class="mt-4" severity="success" />
                <Button
                  icon="pi pi-times"
                  @click="removeUploadedFileCallback(index)"
                  outlined
                  rounded
                  severity="danger"
                />
              </div>
            </div>
          </div>
        </div>
      </template>

      <template #empty>
        <div class="flex items-center justify-center flex-col">
          <i
            class="pi pi-cloud-upload !border-2 !rounded-full !p-8 !text-4xl !text-muted-color"
          ></i>
          <p class="mt-2 mb-0">
            Arrastra y suelta archivos PDF o Excel aquí para subirlos (máximo 250 MiB por archivo).
          </p>
        </div>
      </template>
    </FileUpload>

    <!-- Toast for Notifications -->
    <Toast position="top-right" />
  </div>
</template>

<style scoped>
/* File Card - using PrimeVue classes */
.file-card {
  max-width: 200px;
  min-width: 160px;
  max-height: 280px;
  transition: transform 0.2s ease;
}

.file-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.file-card img {
  object-fit: cover;
  border-radius: 4px;
  background-color: var(--p-surface-ground, #13131a);
  padding: 8px;
}

/* Ensure consistent spacing */
.file-card .font-semibold {
  font-size: 0.875rem;
  line-height: 1.2;
  text-align: center;
}

.file-card div {
  font-size: 0.75rem;
  color: var(--p-text-muted-color, #94a3b8);
}

:deep(.p-fileupload) {
  background: var(--p-surface-card, #1e1e2e);
  border-color: var(--p-surface-border, rgba(255, 255, 255, 0.1));
  color: var(--p-text-color, #e2e8f0);
}

:deep(.p-fileupload-header) {
  background: var(--p-surface-card, #1e1e2e);
  border-color: var(--p-surface-border, rgba(255, 255, 255, 0.1));
  color: var(--p-text-color, #e2e8f0);
}

:deep(.p-fileupload-content) {
  max-height: 400px;
  overflow-y: auto;
  background: var(--p-surface-card, #1e1e2e);
  border-color: var(--p-surface-border, rgba(255, 255, 255, 0.1));
  color: var(--p-text-color, #e2e8f0);
}

:deep(.p-fileupload-empty) {
  background: var(--p-surface-card, #1e1e2e);
  color: var(--p-text-muted-color, #94a3b8);
}

@media (max-width: 768px) {
  .file-card {
    max-width: 140px;
    min-width: 120px;
    max-height: 240px;
  }

  .file-card img {
    width: 80px !important;
    height: 40px !important;
  }

  .file-card .font-semibold {
    font-size: 0.75rem;
    max-width: 120px;
  }

  .flex.flex-wrap.gap-4 {
    gap: 0.75rem !important;
  }
}

@media (max-width: 480px) {
  .file-card {
    max-width: 120px;
    min-width: 100px;
    max-height: 220px;
    padding: 0.5rem !important;
  }

  .file-card img {
    width: 60px !important;
    height: 30px !important;
  }

  .flex.flex-wrap.gap-4 {
    gap: 0.5rem !important;
  }
}
</style>
