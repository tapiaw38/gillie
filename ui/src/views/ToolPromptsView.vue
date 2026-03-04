<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useAssistant } from '@/composables/useAssistant'
import { useToast } from 'primevue/usetoast'
import type { ToolPromptsConfig } from '@/types/assistant'
import Card from 'primevue/card'
import Button from 'primevue/button'
import Textarea from 'primevue/textarea'
import Toast from 'primevue/toast'
import Accordion from 'primevue/accordion'
import AccordionTab from 'primevue/accordiontab'

const { getAssistantProfile, updateAssistantProfile, assistantProfile } = useAssistant()
const toast = useToast()
const isSaving = ref(false)

const TOOL_META: { key: keyof ToolPromptsConfig; label: string; icon: string; hint: string }[] = [
  {
    key: 'search_documents',
    label: 'Buscar en documentos',
    icon: 'pi pi-search',
    hint: 'Cuándo el LLM debe buscar en PDFs/Excel subidos al asistente.',
  },
  {
    key: 'query_database',
    label: 'Consultar base de datos',
    icon: 'pi pi-database',
    hint: 'Cuándo el LLM debe consultar la tabla PostgreSQL configurada. Solo aplica si la integración SQL está activa.',
  },
  {
    key: 'search_images',
    label: 'Buscar imágenes',
    icon: 'pi pi-image',
    hint: 'Cuándo buscar imágenes dentro de archivos subidos.',
  },
  {
    key: 'analyze_pdf',
    label: 'Analizar PDF',
    icon: 'pi pi-file-pdf',
    hint: 'Cuándo analizar la estructura de un PDF.',
  },
  {
    key: 'extract_text_from_pdf',
    label: 'Extraer texto de PDF',
    icon: 'pi pi-file',
    hint: 'Cuándo extraer texto e imágenes de un PDF.',
  },
  {
    key: 'analyze_excel',
    label: 'Analizar Excel',
    icon: 'pi pi-table',
    hint: 'Cuándo analizar datos de un archivo Excel.',
  },
  {
    key: 'describe_image',
    label: 'Describir imagen',
    icon: 'pi pi-eye',
    hint: 'Cuándo describir el contenido de una imagen en base64.',
  },
  {
    key: 'save_memory',
    label: 'Guardar memoria',
    icon: 'pi pi-bookmark',
    hint: 'Cuándo guardar un dato relevante del usuario en la memoria del asistente.',
  },
  {
    key: 'search_memory',
    label: 'Buscar en memoria',
    icon: 'pi pi-history',
    hint: 'Cuándo buscar datos previos guardados en memoria.',
  },
]

const prompts = ref<ToolPromptsConfig>({})

const resetToDefault = (key: keyof ToolPromptsConfig) => {
  prompts.value[key] = ''
}

const save = async () => {
  isSaving.value = true
  try {
    // Only save non-empty prompts
    const toSave: ToolPromptsConfig = {}
    for (const [k, v] of Object.entries(prompts.value)) {
      if (v && v.trim()) toSave[k as keyof ToolPromptsConfig] = v.trim()
    }
    await updateAssistantProfile({ tool_prompts: JSON.stringify(toSave) })
    toast.add({ severity: 'success', summary: 'Guardado', detail: 'Prompts actualizados', life: 3000 })
  } catch {
    toast.add({ severity: 'error', summary: 'Error', detail: 'No se pudo guardar', life: 3000 })
  } finally {
    isSaving.value = false
  }
}

onMounted(async () => {
  await getAssistantProfile()
  if (assistantProfile.value?.tool_prompts) {
    try {
      const saved = JSON.parse(assistantProfile.value.tool_prompts)
      prompts.value = saved
    } catch {
      prompts.value = {}
    }
  }
})
</script>

<template>
  <div class="tool-prompts-container">
    <div class="page-header">
      <div class="header-icon"><i class="pi pi-sliders-h"></i></div>
      <div>
        <h1 class="page-title">Prompts de Tools</h1>
        <p class="page-subtitle">
          Personalizá las instrucciones que le indican al LLM cuándo usar cada herramienta.
          Dejá vacío para usar el valor por defecto.
        </p>
      </div>
    </div>

    <Accordion class="tools-accordion" :multiple="true">
      <AccordionTab v-for="tool in TOOL_META" :key="tool.key">
        <template #header>
          <div class="tab-header">
            <i :class="tool.icon" class="tab-icon"></i>
            <span class="tab-label">{{ tool.label }}</span>
            <span v-if="prompts[tool.key]" class="tab-badge">Personalizado</span>
          </div>
        </template>

        <div class="tool-field">
          <p class="tool-hint">{{ tool.hint }}</p>
          <Textarea
            v-model="prompts[tool.key]"
            :placeholder="`Dejar vacío para usar el prompt por defecto de '${tool.key}'`"
            rows="4"
            class="w-full"
            auto-resize
          />
          <div class="field-actions">
            <Button
              label="Restaurar por defecto"
              icon="pi pi-refresh"
              severity="secondary"
              size="small"
              text
              @click="resetToDefault(tool.key)"
            />
          </div>
        </div>
      </AccordionTab>
    </Accordion>

    <div class="save-bar">
      <Button
        label="Guardar cambios"
        icon="pi pi-save"
        severity="primary"
        :loading="isSaving"
        @click="save"
      />
    </div>

    <Toast position="top-right" />
  </div>
</template>

<style scoped>
.tool-prompts-container {
  max-width: 860px;
  margin: 0 auto;
  padding: 1rem 1.25rem;
  min-height: 100vh;
  background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
  box-sizing: border-box;
}

.page-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.header-icon {
  width: 3.2rem;
  height: 3.2rem;
  border-radius: 0.75rem;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.6rem;
  color: white;
  background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.08);
  flex-shrink: 0;
}

.page-title {
  font-size: 1.6rem;
  font-weight: 700;
  margin: 0 0 0.25rem;
  background: linear-gradient(135deg, #1e293b 0%, #475569 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.page-subtitle {
  font-size: 0.9rem;
  color: #64748b;
  margin: 0;
}

.tools-accordion {
  margin-bottom: 1.5rem;
}

.tab-header {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}

.tab-icon {
  color: var(--color-primary);
  font-size: 1rem;
}

.tab-label {
  font-weight: 600;
  font-size: 0.95rem;
  color: #374151;
}

.tab-badge {
  margin-left: auto;
  font-size: 0.75rem;
  font-weight: 600;
  background: #dbeafe;
  color: #1d4ed8;
  padding: 0.15rem 0.5rem;
  border-radius: 999px;
}

.tool-field {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  padding: 0.25rem 0;
}

.tool-hint {
  font-size: 0.85rem;
  color: #64748b;
  font-style: italic;
  margin: 0;
}

.w-full {
  width: 100%;
}

.field-actions {
  display: flex;
  justify-content: flex-end;
}

.save-bar {
  display: flex;
  justify-content: flex-end;
  padding: 1rem;
  background: white;
  border-radius: 0.75rem;
  box-shadow: 0 3px 14px rgba(0, 0, 0, 0.06);
  border: 1px solid #e2e8f0;
}
</style>
