<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useAssistant } from '@/composables/useAssistant'
import { useToast } from 'primevue/usetoast'
import { useI18n } from 'vue-i18n'
import type { ToolPromptsConfig } from '@/types/assistant'
import Card from 'primevue/card'
import Button from 'primevue/button'
import Textarea from 'primevue/textarea'
import Toast from 'primevue/toast'
import Accordion from 'primevue/accordion'
import AccordionTab from 'primevue/accordiontab'
import InputSwitch from 'primevue/inputswitch'

const { getAssistantProfile, updateAssistantProfile, assistantProfile } = useAssistant()
const { t } = useI18n()
const toast = useToast()
const isSaving = ref(false)

const TOOL_META: { key: keyof ToolPromptsConfig; icon: string }[] = [
  { key: 'search_documents', icon: 'pi pi-search' },
  { key: 'query_database', icon: 'pi pi-database' },
  { key: 'search_images', icon: 'pi pi-image' },
  { key: 'analyze_pdf', icon: 'pi pi-file-pdf' },
  { key: 'extract_text_from_pdf', icon: 'pi pi-file' },
  { key: 'analyze_excel', icon: 'pi pi-table' },
  { key: 'describe_image', icon: 'pi pi-eye' },
  { key: 'save_memory', icon: 'pi pi-bookmark' },
  { key: 'search_memory', icon: 'pi pi-history' },
  { key: 'system_propose', icon: 'pi pi-server' },
  { key: 'system_confirm', icon: 'pi pi-check-circle' },
  { key: 'cron_create', icon: 'pi pi-clock' },
  { key: 'cron_list', icon: 'pi pi-list' },
  { key: 'cron_delete', icon: 'pi pi-trash' },
  { key: 'cron_run', icon: 'pi pi-play' },
  { key: 'read_file', icon: 'pi pi-file' },
  { key: 'write_file', icon: 'pi pi-file-edit' },
  { key: 'edit_file', icon: 'pi pi-pencil' },
  { key: 'list_directory', icon: 'pi pi-folder-open' },
  { key: 'find_files', icon: 'pi pi-search' },
  { key: 'run_shell', icon: 'pi pi-terminal' },
  { key: 'grep_files', icon: 'pi pi-filter' },
  { key: 'git_status', icon: 'pi pi-code' },
  { key: 'git_diff', icon: 'pi pi-code' },
  { key: 'git_log', icon: 'pi pi-history' },
  { key: 'git_commit', icon: 'pi pi-check-circle' },
]

const prompts = ref<ToolPromptsConfig>({})
// enabled[key] = true means the tool is active (not disabled)
const enabled = ref<Record<string, boolean>>({})

// Initialize all tools as enabled by default
TOOL_META.forEach((t) => { enabled.value[t.key] = true })

const resetToDefault = (key: keyof ToolPromptsConfig) => {
  prompts.value[key] = ''
}

const save = async () => {
  isSaving.value = true
  try {
    const toSave: ToolPromptsConfig = {}
    for (const [k, v] of Object.entries(prompts.value)) {
      if (v && v.trim()) toSave[k as keyof ToolPromptsConfig] = v.trim()
    }

    const disabledTools = TOOL_META
      .filter((t) => !enabled.value[t.key])
      .map((t) => t.key)

    await updateAssistantProfile({
      tool_prompts: JSON.stringify(toSave),
      disabled_tools: disabledTools,
    })
    toast.add({ severity: 'success', summary: t('toolPrompts.saved'), detail: t('toolPrompts.savedDesc'), life: 3000 })
  } catch {
    toast.add({ severity: 'error', summary: t('toolPrompts.error'), detail: t('toolPrompts.errorDesc'), life: 3000 })
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
  if (assistantProfile.value?.disabled_tools) {
    const disabled = assistantProfile.value.disabled_tools
    TOOL_META.forEach((t) => {
      enabled.value[t.key] = !disabled.includes(t.key)
    })
  }
})
</script>

<template>
  <div class="tool-prompts-container">
    <div class="page-header">
      <div class="header-icon"><i class="pi pi-sliders-h"></i></div>
      <div>
        <h1 class="page-title">{{ t('toolPrompts.title') }}</h1>
        <p class="page-subtitle">
          {{ t('toolPrompts.subtitle') }}
        </p>
      </div>
    </div>

    <Accordion class="tools-accordion" :multiple="true">
      <AccordionTab v-for="tool in TOOL_META" :key="tool.key">
        <template #header>
          <div class="tab-header">
            <i :class="tool.icon" class="tab-icon" :style="{ opacity: enabled[tool.key] ? 1 : 0.4 }"></i>
            <span class="tab-label" :style="{ opacity: enabled[tool.key] ? 1 : 0.5 }">{{ t(`toolPrompts.tools.${tool.key}.label`) }}</span>
            <span v-if="!enabled[tool.key]" class="tab-badge tab-badge--disabled">{{ t('toolPrompts.disabled') }}</span>
            <span v-else-if="prompts[tool.key]" class="tab-badge">{{ t('toolPrompts.custom') }}</span>
            <InputSwitch
              v-model="enabled[tool.key]"
              class="tool-toggle"
              @click.stop
            />
          </div>
        </template>

        <div class="tool-field">
          <p class="tool-hint">{{ t(`toolPrompts.tools.${tool.key}.hint`) }}</p>
          <Textarea
            v-model="prompts[tool.key]"
            :placeholder="`${t('toolPrompts.defaultPlaceholder')} '${tool.key}'`"
            :disabled="!enabled[tool.key]"
            rows="4"
            class="w-full"
            auto-resize
          />
          <div class="field-actions">
            <Button
              :label="t('toolPrompts.restoreDefault')"
              icon="pi pi-refresh"
              severity="secondary"
              size="small"
              text
              :disabled="!enabled[tool.key]"
              @click="resetToDefault(tool.key)"
            />
          </div>
        </div>
      </AccordionTab>
    </Accordion>

    <div class="save-bar">
      <Button
        :label="t('toolPrompts.saveChanges')"
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
  background: var(--do-bg);
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
  color: var(--do-text);
}

.page-subtitle {
  font-size: 0.9rem;
  color: var(--do-text-muted);
  margin: 0;
}

.tools-accordion {
  margin-bottom: 1.5rem;
}

.tab-header {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  width: 100%;
}

.tab-icon {
  color: var(--color-primary);
  font-size: 1rem;
  transition: opacity 0.2s;
}

.tab-label {
  font-weight: 600;
  font-size: 0.95rem;
  color: var(--do-text);
  transition: opacity 0.2s;
}

.tab-badge {
  font-size: 0.75rem;
  font-weight: 600;
  background: rgba(59,130,246,0.15);
  color: #93c5fd;
  padding: 0.15rem 0.5rem;
  border-radius: 999px;
}

.tab-badge--disabled {
  background: rgba(255,68,68,0.15);
  color: #fca5a5;
}

.tool-toggle {
  margin-left: auto;
  flex-shrink: 0;
}

.tool-field {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  padding: 0.25rem 0;
}

.tool-hint {
  font-size: 0.85rem;
  color: var(--do-text-muted);
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
  background: rgba(255,255,255,0.04);
  border-radius: 0.75rem;
  border: 1px solid rgba(255,255,255,0.08);
}
</style>
