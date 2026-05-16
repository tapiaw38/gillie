<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useAssistant } from '@/composables/useAssistant'
import { useToast } from 'primevue/usetoast'
import { useI18n } from 'vue-i18n'
import type { ToolPromptsConfig } from '@/types/assistant'
import Button from 'primevue/button'
import Textarea from 'primevue/textarea'
import Toast from 'primevue/toast'
import InputSwitch from 'primevue/inputswitch'
import InputText from 'primevue/inputtext'
import Dialog from 'primevue/dialog'

type ToolKey = keyof ToolPromptsConfig
type FilterMode = 'all' | 'enabled' | 'disabled' | 'customized'

type ToolMeta = {
  key: ToolKey
  icon: string
}

type ToolCategory = {
  id: string
  icon: string
  tools: ToolMeta[]
}

const { getAssistantProfile, updateAssistantProfile, assistantProfile } = useAssistant()
const { t, te } = useI18n()
const toast = useToast()

const ALL_CATEGORIES: ToolCategory[] = [
  {
    id: 'web',
    icon: 'pi pi-globe',
    tools: [
      { key: 'fetch_url', icon: 'pi pi-globe' },
      { key: 'download_file', icon: 'pi pi-download' },
      { key: 'web_search', icon: 'pi pi-search' },
    ],
  },
  {
    id: 'files',
    icon: 'pi pi-folder-open',
    tools: [
      { key: 'read_file', icon: 'pi pi-file' },
      { key: 'write_file', icon: 'pi pi-file-edit' },
      { key: 'edit_file', icon: 'pi pi-pencil' },
      { key: 'list_directory', icon: 'pi pi-folder-open' },
      { key: 'find_files', icon: 'pi pi-search' },
      { key: 'grep_files', icon: 'pi pi-filter' },
    ],
  },
  {
    id: 'code',
    icon: 'pi pi-code',
    tools: [
      { key: 'repo_map', icon: 'pi pi-sitemap' },
      { key: 'check_code', icon: 'pi pi-check-square' },
    ],
  },
  {
    id: 'git',
    icon: 'pi pi-github',
    tools: [
      { key: 'git_status', icon: 'pi pi-code' },
      { key: 'git_diff', icon: 'pi pi-code' },
      { key: 'git_log', icon: 'pi pi-history' },
      { key: 'git_commit', icon: 'pi pi-check-circle' },
    ],
  },
  {
    id: 'documents',
    icon: 'pi pi-file',
    tools: [
      { key: 'search_documents', icon: 'pi pi-search' },
      { key: 'search_images', icon: 'pi pi-image' },
      { key: 'analyze_pdf', icon: 'pi pi-file-pdf' },
      { key: 'extract_text_from_pdf', icon: 'pi pi-file' },
      { key: 'analyze_excel', icon: 'pi pi-table' },
      { key: 'write_excel', icon: 'pi pi-table' },
      { key: 'read_docx', icon: 'pi pi-file-word' },
      { key: 'write_docx', icon: 'pi pi-file-word' },
      { key: 'modify_excel', icon: 'pi pi-table' },
      { key: 'modify_docx', icon: 'pi pi-file-word' },
      { key: 'read_pptx', icon: 'pi pi-desktop' },
      { key: 'write_pptx', icon: 'pi pi-desktop' },
      { key: 'modify_pptx', icon: 'pi pi-desktop' },
      { key: 'insert_image_docx', icon: 'pi pi-image' },
      { key: 'insert_image_excel', icon: 'pi pi-image' },
      { key: 'insert_image_pptx', icon: 'pi pi-image' },
      { key: 'describe_image', icon: 'pi pi-eye' },
    ],
  },
  {
    id: 'media',
    icon: 'pi pi-images',
    tools: [
      { key: 'send_file', icon: 'pi pi-send' },
      { key: 'send_screenshot', icon: 'pi pi-send' },
      { key: 'take_screenshot', icon: 'pi pi-camera' },
    ],
  },
  {
    id: 'browser',
    icon: 'pi pi-window-maximize',
    tools: [
      { key: 'browser_connect', icon: 'pi pi-link' },
      { key: 'browser_navigate', icon: 'pi pi-directions' },
      { key: 'browser_act', icon: 'pi pi-bolt' },
      { key: 'browser_extract', icon: 'pi pi-download' },
      { key: 'browser_click', icon: 'pi pi-mouse' },
      { key: 'browser_type', icon: 'pi pi-pencil' },
      { key: 'browser_get_content', icon: 'pi pi-file' },
      { key: 'browser_screenshot', icon: 'pi pi-camera' },
      { key: 'browser_close', icon: 'pi pi-times' },
      { key: 'browser_switch_tab', icon: 'pi pi-clone' },
      { key: 'browser_enable_remote_debug', icon: 'pi pi-wrench' },
      { key: 'browser_evaluate', icon: 'pi pi-code' },
    ],
  },
  {
    id: 'memory',
    icon: 'pi pi-bookmark',
    tools: [
      { key: 'organize_memory', icon: 'pi pi-sort-alt' },
      { key: 'save_memory', icon: 'pi pi-bookmark' },
      { key: 'search_memory', icon: 'pi pi-history' },
      { key: 'save_solution', icon: 'pi pi-check-circle' },
    ],
  },
  {
    id: 'system',
    icon: 'pi pi-server',
    tools: [
      { key: 'system_propose', icon: 'pi pi-server' },
      { key: 'system_confirm', icon: 'pi pi-check-circle' },
    ],
  },
  {
    id: 'cron',
    icon: 'pi pi-clock',
    tools: [
      { key: 'cron_create', icon: 'pi pi-clock' },
      { key: 'cron_list', icon: 'pi pi-list' },
      { key: 'cron_delete', icon: 'pi pi-trash' },
      { key: 'cron_run', icon: 'pi pi-play' },
    ],
  },
  {
    id: 'database',
    icon: 'pi pi-database',
    tools: [{ key: 'query_database', icon: 'pi pi-database' }],
  },
]

const prompts = ref<ToolPromptsConfig>({})
const enabled = ref<Record<string, boolean>>({})
const isSaving = ref(false)
const searchQuery = ref('')
const filterMode = ref<FilterMode>('all')
const activeCategoryId = ref<string | null>(null)
const editorToolKey = ref<ToolKey | null>(null)

for (const category of ALL_CATEGORIES) {
  for (const tool of category.tools) {
    enabled.value[tool.key] = true
  }
}

const filterOptions: { key: FilterMode; icon: string }[] = [
  { key: 'all', icon: 'pi pi-th-large' },
  { key: 'enabled', icon: 'pi pi-check-circle' },
  { key: 'disabled', icon: 'pi pi-ban' },
  { key: 'customized', icon: 'pi pi-star' },
]

const humanizeKey = (key: string) =>
  key
    .split('_')
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(' ')

const toolLabel = (key: ToolKey) =>
  te(`toolPrompts.tools.${key}.label`) ? t(`toolPrompts.tools.${key}.label`) : humanizeKey(key)

const toolHint = (key: ToolKey) =>
  te(`toolPrompts.tools.${key}.hint`)
    ? t(`toolPrompts.tools.${key}.hint`)
    : t('toolPrompts.genericHint', { tool: humanizeKey(key) })

const categoryLabel = (id: string) =>
  te(`toolPrompts.categories.${id}`) ? t(`toolPrompts.categories.${id}`) : humanizeKey(id)

const isCustomized = (key: ToolKey) => Boolean(prompts.value[key]?.trim())

const matchesSearch = (tool: ToolMeta) => {
  const query = searchQuery.value.trim().toLowerCase()
  if (!query) return true
  return [tool.key, toolLabel(tool.key), toolHint(tool.key)].some((value) =>
    value.toLowerCase().includes(query),
  )
}

const matchesFilter = (tool: ToolMeta) => {
  if (filterMode.value === 'enabled') return enabled.value[tool.key]
  if (filterMode.value === 'disabled') return !enabled.value[tool.key]
  if (filterMode.value === 'customized') return isCustomized(tool.key)
  return true
}

const categories = computed(() =>
  ALL_CATEGORIES.map((category) => {
    const visibleTools = category.tools.filter((tool) => matchesSearch(tool) && matchesFilter(tool))
    const customizedCount = category.tools.filter((tool) => isCustomized(tool.key)).length
    const disabledCount = category.tools.filter((tool) => !enabled.value[tool.key]).length
    return {
      ...category,
      visibleTools,
      visibleCount: visibleTools.length,
      customizedCount,
      disabledCount,
    }
  }),
)

const visibleCategories = computed(() => categories.value.filter((category) => category.visibleCount > 0))

const activeCategory = computed(() => {
  const matched = visibleCategories.value.find((category) => category.id === activeCategoryId.value)
  return matched ?? null
})

const activeTools = computed(() => activeCategory.value?.visibleTools ?? [])

const summary = computed(() => {
  const tools = ALL_CATEGORIES.flatMap((category) => category.tools)
  return {
    total: tools.length,
    enabled: tools.filter((tool) => enabled.value[tool.key]).length,
    disabled: tools.filter((tool) => !enabled.value[tool.key]).length,
    customized: tools.filter((tool) => isCustomized(tool.key)).length,
  }
})

const editorTool = computed(() => {
  if (!editorToolKey.value) return null
  return ALL_CATEGORIES.flatMap((category) => category.tools).find((tool) => tool.key === editorToolKey.value) ?? null
})

const resetToDefault = (key: ToolKey) => {
  prompts.value[key] = ''
}

const openEditor = (key: ToolKey) => {
  editorToolKey.value = key
}

const closeEditor = () => {
  editorToolKey.value = null
}

const save = async () => {
  isSaving.value = true
  try {
    const toSave: ToolPromptsConfig = {}
    for (const [k, v] of Object.entries(prompts.value)) {
      if (v && v.trim()) toSave[k as ToolKey] = v.trim()
    }

    const disabledTools = ALL_CATEGORIES.flatMap((category) => category.tools)
      .filter((tool) => !enabled.value[tool.key])
      .map((tool) => tool.key)

    await updateAssistantProfile({
      tool_prompts: JSON.stringify(toSave),
      disabled_tools: disabledTools,
    })

    toast.add({
      severity: 'success',
      summary: t('toolPrompts.saved'),
      detail: t('toolPrompts.savedDesc'),
      life: 3000,
    })
  } catch {
    toast.add({
      severity: 'error',
      summary: t('toolPrompts.error'),
      detail: t('toolPrompts.errorDesc'),
      life: 3000,
    })
  } finally {
    isSaving.value = false
  }
}

onMounted(async () => {
  await getAssistantProfile()
  if (assistantProfile.value?.tool_prompts) {
    try {
      prompts.value = JSON.parse(assistantProfile.value.tool_prompts)
    } catch {
      prompts.value = {}
    }
  }

  if (assistantProfile.value?.disabled_tools) {
    const disabled = assistantProfile.value.disabled_tools
    for (const category of ALL_CATEGORIES) {
      for (const tool of category.tools) {
        enabled.value[tool.key] = !disabled.includes(tool.key)
      }
    }
  }
})
</script>

<template>
  <div class="integration-container">
    <div class="page-header">
      <div class="header-left">
        <div class="icon-wrapper tools-icon">
          <i class="pi pi-sliders-h"></i>
        </div>
        <div class="header-text">
          <h1 class="page-title">{{ t('toolPrompts.title') }}</h1>
          <p class="page-subtitle">{{ t('toolPrompts.subtitle') }}</p>
        </div>
      </div>
    </div>

    <section class="panel">
      <div class="panel-header">
        <div>
          <p class="panel-title">{{ t('toolPrompts.overviewTitle') }}</p>
          <p class="panel-subtitle">{{ t('toolPrompts.panelSubtitle') }}</p>
        </div>
      </div>
      <div class="panel-body">
        <div class="summary-grid">
          <div class="status-row">
            <div class="status-row-label">{{ t('toolPrompts.summary.total') }}</div>
            <div class="status-row-value">
              <strong class="summary-value">{{ summary.total }}</strong>
            </div>
          </div>
          <div class="status-row">
            <div class="status-row-label">{{ t('toolPrompts.summary.enabled') }}</div>
            <div class="status-row-value">
              <strong class="summary-value">{{ summary.enabled }}</strong>
            </div>
          </div>
          <div class="status-row">
            <div class="status-row-label">{{ t('toolPrompts.summary.disabled') }}</div>
            <div class="status-row-value">
              <strong class="summary-value">{{ summary.disabled }}</strong>
            </div>
          </div>
          <div class="status-row">
            <div class="status-row-label">{{ t('toolPrompts.summary.customized') }}</div>
            <div class="status-row-value">
              <strong class="summary-value">{{ summary.customized }}</strong>
            </div>
          </div>
        </div>

        <div class="search-box">
          <i class="pi pi-search search-icon"></i>
          <InputText
            v-model="searchQuery"
            :placeholder="t('toolPrompts.searchPlaceholder')"
            class="search-input"
          />
        </div>

        <div class="filter-row">
          <button
            v-for="option in filterOptions"
            :key="option.key"
            type="button"
            class="filter-chip"
            :class="{ 'filter-chip--active': filterMode === option.key }"
            @click="filterMode = option.key"
          >
            <i :class="option.icon"></i>
            <span>{{ t(`toolPrompts.filters.${option.key}`) }}</span>
          </button>
        </div>
      </div>
    </section>

    <section class="panel">
      <div class="panel-header">
        <div>
          <p class="panel-title">{{ t('toolPrompts.categoriesTitle') }}</p>
          <p class="panel-subtitle">{{ t('toolPrompts.categoriesSubtitle') }}</p>
        </div>
      </div>
      <div class="panel-body">
        <div class="categories-grid">
          <button
            v-for="category in visibleCategories"
            :key="category.id"
            type="button"
            class="category-card"
            :class="{ 'category-card--active': activeCategory?.id === category.id }"
            @click="activeCategoryId = activeCategory?.id === category.id ? null : category.id"
          >
            <div class="category-head">
              <div class="category-icon">
                <i :class="category.icon"></i>
              </div>
              <div>
                <h2 class="category-title">{{ categoryLabel(category.id) }}</h2>
                <p class="category-meta">{{ category.visibleCount }} {{ t('toolPrompts.toolsCount') }}</p>
              </div>
            </div>

            <div class="category-badges">
              <span v-if="category.customizedCount > 0" class="category-badge">
                {{ category.customizedCount }} {{ t('toolPrompts.summary.customized') }}
              </span>
              <span v-if="category.disabledCount > 0" class="category-badge category-badge--muted">
                {{ category.disabledCount }} {{ t('toolPrompts.summary.disabled') }}
              </span>
              <span
                v-if="category.customizedCount === 0 && category.disabledCount === 0"
                class="category-badge category-badge--quiet"
              >
                {{ t('toolPrompts.readyLabel') }}
              </span>
            </div>
          </button>
        </div>
      </div>
    </section>

    <section v-if="activeCategory" class="panel">
      <div class="panel-header">
        <div>
          <p class="panel-title">{{ categoryLabel(activeCategory.id) }}</p>
          <p class="panel-subtitle">{{ t('toolPrompts.toolsSubtitle') }}</p>
        </div>
      </div>
      <div class="panel-body">
        <div class="tool-list">
          <article
            v-for="tool in activeTools"
            :key="tool.key"
            class="tool-row"
            :class="{ 'tool-row--disabled': !enabled[tool.key] }"
          >
            <div class="tool-main">
              <div class="tool-icon">
                <i :class="tool.icon"></i>
              </div>
              <div class="tool-copy">
              <div class="tool-title-row">
                  <h3 class="tool-title">{{ toolLabel(tool.key) }}</h3>
                  <span v-if="isCustomized(tool.key)" class="tool-pill">{{ t('toolPrompts.custom') }}</span>
                  <span v-if="!enabled[tool.key]" class="tool-pill tool-pill--disabled">{{ t('toolPrompts.disabled') }}</span>
                </div>
                <p class="tool-hint">{{ toolHint(tool.key) }}</p>
              </div>
            </div>

            <div class="tool-actions">
              <InputSwitch v-model="enabled[tool.key]" />
              <Button
                :label="t('toolPrompts.editPrompt')"
                icon="pi pi-pencil"
                severity="secondary"
                size="small"
                outlined
                @click="openEditor(tool.key)"
              />
            </div>
          </article>
        </div>
      </div>
    </section>

    <section v-else-if="visibleCategories.length > 0" class="panel">
      <div class="panel-body empty-body">
        <i class="pi pi-th-large empty-icon"></i>
        <h2>{{ t('toolPrompts.selectCategoryTitle') }}</h2>
        <p>{{ t('toolPrompts.selectCategoryDesc') }}</p>
      </div>
    </section>

    <section v-else class="panel">
      <div class="panel-body empty-body">
        <i class="pi pi-search empty-icon"></i>
        <h2>{{ t('toolPrompts.noResultsTitle') }}</h2>
        <p>{{ t('toolPrompts.noResultsDesc') }}</p>
      </div>
    </section>

    <div class="panel">
      <div class="panel-body save-bar">
        <Button
          :label="t('toolPrompts.saveChanges')"
          icon="pi pi-save"
          severity="primary"
          :loading="isSaving"
          @click="save"
        />
      </div>
    </div>

    <Dialog
      :visible="Boolean(editorTool)"
      modal
      :style="{ width: 'min(760px, 92vw)' }"
      :header="editorTool ? toolLabel(editorTool.key) : ''"
      @update:visible="(visible) => !visible && closeEditor()"
    >
      <div v-if="editorTool" class="editor-modal">
        <code class="editor-key">{{ editorTool.key }}</code>
        <p class="editor-hint">{{ toolHint(editorTool.key) }}</p>
        <Textarea
          v-model="prompts[editorTool.key]"
          :placeholder="`${t('toolPrompts.defaultPlaceholder')} '${editorTool.key}'`"
          :disabled="!enabled[editorTool.key]"
          rows="10"
          class="w-full"
          auto-resize
        />

        <div class="editor-actions">
          <Button
            :label="t('toolPrompts.restoreDefault')"
            icon="pi pi-refresh"
            severity="secondary"
            text
            :disabled="!enabled[editorTool.key]"
            @click="resetToDefault(editorTool.key)"
          />
          <Button
            :label="t('toolPrompts.closeEditor')"
            icon="pi pi-check"
            severity="primary"
            @click="closeEditor()"
          />
        </div>
      </div>
    </Dialog>

    <Toast position="top-right" />
  </div>
</template>

<style scoped>
.integration-container { max-width: 860px; margin: 0 auto; padding: 1.25rem; display: flex; flex-direction: column; gap: 1rem; background: var(--do-bg); box-sizing: border-box; }
.page-header { display: flex; align-items: center; justify-content: space-between; gap: 1rem; padding: 1rem 1.25rem; border: 1px solid var(--do-border-light); border-radius: 0.6rem; background: rgba(255, 255, 255, 0.02); }
.header-left { display: flex; align-items: center; gap: 1rem; min-width: 0; }
.icon-wrapper { display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.tools-icon { color: var(--color-primary); font-size: 1.7rem; }
.header-text { min-width: 0; }
.page-title { font-size: 1.35rem; font-weight: 700; color: var(--do-text); margin: 0 0 0.2rem; line-height: 1.2; }
.page-subtitle { font-size: 0.875rem; color: var(--do-text-muted); margin: 0; }
.panel { border: 1px solid var(--do-border-light); border-radius: 0.6rem; overflow: hidden; background: var(--do-bg); }
.panel-header { display: flex; align-items: center; gap: 0.875rem; padding: 0.875rem 1.25rem; border-bottom: 1px solid var(--do-border-light); background: rgba(255, 255, 255, 0.015); }
.panel-title { font-size: 0.95rem; font-weight: 600; color: var(--do-text); margin: 0 0 0.15rem; }
.panel-subtitle { font-size: 0.8rem; color: var(--do-text-muted); margin: 0; }
.panel-body { padding: 1rem; display: flex; flex-direction: column; gap: 0.85rem; }
.summary-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 0.45rem; }
.status-row { display: flex; align-items: baseline; justify-content: space-between; gap: 0.5rem; padding: 0.42rem 0.55rem; background: rgba(255, 255, 255, 0.015); border: 1px solid var(--do-border-light); border-radius: 0.4rem; }
.status-row-label { display: flex; align-items: center; gap: 0.3rem; font-size: 0.64rem; font-weight: 600; color: var(--do-text-muted); text-transform: uppercase; letter-spacing: 0.03em; }
.status-row-value { display: flex; align-items: center; justify-content: flex-end; min-width: 0; }
.summary-value { font-family: 'SF Mono', 'Monaco', 'Consolas', monospace; font-size: 0.88rem; color: var(--do-text); }
.search-box { position: relative; }
.search-icon { position: absolute; left: 0.9rem; top: 50%; transform: translateY(-50%); color: var(--do-text-muted); }
.search-input { width: 100%; }
:deep(.search-input .p-inputtext) { width: 100%; padding-left: 2.4rem; }
.filter-row { display: flex; flex-wrap: wrap; gap: 0.6rem; }
.filter-chip { display: inline-flex; align-items: center; gap: 0.45rem; border-radius: 999px; border: 1px solid var(--do-border-light); background: rgba(255, 255, 255, 0.015); color: var(--do-text); padding: 0.55rem 0.85rem; font-size: 0.84rem; cursor: pointer; transition: border-color 0.18s ease, background 0.18s ease; }
.filter-chip--active { background: rgba(255, 255, 255, 0.04); border-color: var(--color-primary); }
.categories-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 0.6rem; }
.category-card { text-align: left; padding: 0.7rem 0.75rem; border-radius: 0.45rem; border: 1px solid var(--do-border-light); background: rgba(255, 255, 255, 0.015); color: inherit; cursor: pointer; transition: border-color 0.18s ease, background 0.18s ease; }
.category-card--active { border-color: var(--color-primary); background: rgba(255, 255, 255, 0.03); }
.category-head { display: flex; gap: 0.55rem; align-items: center; margin-bottom: 0.55rem; }
.category-icon, .tool-icon { width: 1.8rem; height: 1.8rem; border-radius: 0.35rem; display: inline-flex; align-items: center; justify-content: center; background: rgba(255, 255, 255, 0.03); color: var(--color-primary); flex-shrink: 0; }
.category-title, .tool-title { margin: 0; color: var(--do-text); }
.category-title { font-size: 0.86rem; font-weight: 700; }
.category-meta, .tool-hint, .editor-hint, .empty-body p { margin: 0; color: var(--do-text-muted); }
.category-meta { font-size: 0.72rem; margin-top: 0.1rem; }
.category-badges { display: flex; flex-wrap: wrap; gap: 0.35rem; }
.category-badge, .tool-pill { display: inline-flex; align-items: center; border-radius: 999px; padding: 0.14rem 0.42rem; font-size: 0.65rem; font-weight: 600; background: rgba(255, 255, 255, 0.04); color: var(--do-text-muted); }
.category-badge--muted, .tool-pill--disabled { color: var(--color-danger); }
.category-badge--quiet { opacity: 0.8; }
.tool-list { display: flex; flex-direction: column; gap: 0.55rem; }
.tool-row { display: flex; align-items: center; justify-content: space-between; gap: 0.85rem; padding: 0.68rem 0.75rem; border-radius: 0.45rem; background: rgba(255, 255, 255, 0.015); border: 1px solid var(--do-border-light); }
.tool-row--disabled { opacity: 0.7; }
.tool-main { display: flex; align-items: flex-start; gap: 0.7rem; min-width: 0; }
.tool-copy { min-width: 0; }
.tool-title-row { display: flex; flex-wrap: wrap; align-items: center; gap: 0.35rem; margin-bottom: 0.15rem; }
.tool-title { font-size: 0.88rem; font-weight: 700; }
.tool-hint { font-size: 0.8rem; line-height: 1.35; }
.tool-actions { display: flex; align-items: center; gap: 0.55rem; flex-shrink: 0; }
.empty-body { align-items: center; text-align: center; padding: 2rem 1.25rem; }
.empty-icon { font-size: 2rem; color: var(--do-text-muted); margin-bottom: 0.3rem; }
.save-bar { display: flex; justify-content: flex-end; }
.editor-modal { display: flex; flex-direction: column; gap: 0.9rem; }
.editor-key { display: inline-block; align-self: flex-start; font-size: 0.76rem; color: var(--do-text-muted); background: rgba(255, 255, 255, 0.025); padding: 0.18rem 0.42rem; border-radius: 0.3rem; }
.editor-hint { font-size: 0.88rem; line-height: 1.45; }
.editor-actions { display: flex; align-items: center; justify-content: space-between; gap: 0.75rem; }
.w-full { width: 100%; }
:deep(.p-dialog) { border-radius: 0.6rem; overflow: hidden; border: 1px solid var(--do-border-light); }
:deep(.p-dialog-header) { background: var(--do-bg); color: var(--do-text); border-bottom: 1px solid var(--do-border-light); padding: 1rem 1.25rem; }
:deep(.p-dialog-content) { background: var(--do-bg); color: var(--do-text); padding: 1.25rem; }
:deep(.p-inputtext),
:deep(.p-inputtextarea) { background: rgba(255, 255, 255, 0.02); border-color: var(--do-border-light); color: var(--do-text); }
:deep(.p-inputtext::placeholder),
:deep(.p-inputtextarea::placeholder) { color: var(--do-text-muted); opacity: 0.85; }
@media (max-width: 600px) {
  .integration-container { padding: 0.75rem; }
  .page-header { flex-direction: column; align-items: flex-start; gap: 0.875rem; }
  .summary-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .status-row { flex-direction: column; align-items: flex-start; }
  .tool-row { flex-direction: column; align-items: stretch; }
  .tool-actions { justify-content: space-between; }
  .editor-actions { flex-direction: column; align-items: stretch; }
}
</style>
