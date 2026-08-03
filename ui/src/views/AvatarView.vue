<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from 'primevue/usetoast'
import { useAssistant } from '@/composables/useAssistant'
import Button from 'primevue/button'
import Slider from 'primevue/slider'
import Toast from 'primevue/toast'
import Message from 'primevue/message'

const { t } = useI18n()
const toast = useToast()
const {
  assistantProfile,
  getAssistantProfile,
  updateAssistantProfile,
  isGetAssistantProfilePending: loading,
  isUpdateAssistantProfilePending: saving,
} = useAssistant()

const DEFAULTS = { width: 430, height: 680, zoom: 1.5 }
const LIMITS = {
  width: { min: 200, max: 3840 },
  height: { min: 200, max: 2160 },
  zoom: { min: 0.5, max: 4 },
}

const width = ref(DEFAULTS.width)
const height = ref(DEFAULTS.height)
const zoom = ref(DEFAULTS.zoom)

watch(
  assistantProfile,
  (profile) => {
    if (!profile) return
    width.value = profile.avatar_width ?? DEFAULTS.width
    height.value = profile.avatar_height ?? DEFAULTS.height
    zoom.value = profile.avatar_zoom ?? DEFAULTS.zoom
  },
  { immediate: true },
)

const isDefault = computed(
  () =>
    width.value === DEFAULTS.width &&
    height.value === DEFAULTS.height &&
    zoom.value === DEFAULTS.zoom,
)

const previewStyle = computed(() => {
  const cap = 260
  const scale = Math.min(cap / width.value, (cap * 1.4) / height.value, 1)
  return {
    width: `${Math.round(width.value * scale)}px`,
    height: `${Math.round(height.value * scale)}px`,
  }
})

// The zoom moves the camera, so a larger number crops tighter. Showing the
// silhouette scaled by it makes that direction obvious before saving.
const subjectStyle = computed(() => ({
  height: `${Math.min(96, 58 * zoom.value)}%`,
}))

const clamp = (value: number, { min, max }: { min: number; max: number }) =>
  Math.min(max, Math.max(min, value))

const fields = computed(() => [
  {
    key: 'width' as const,
    model: width,
    label: t('avatar.width'),
    hint: t('avatar.widthHint'),
    limits: LIMITS.width,
    step: 10,
    display: `${width.value} px`,
    low: `${LIMITS.width.min} px`,
    high: `${LIMITS.width.max} px`,
    decimals: 0,
  },
  {
    key: 'height' as const,
    model: height,
    label: t('avatar.height'),
    hint: t('avatar.heightHint'),
    limits: LIMITS.height,
    step: 10,
    display: `${height.value} px`,
    low: `${LIMITS.height.min} px`,
    high: `${LIMITS.height.max} px`,
    decimals: 0,
  },
  {
    key: 'zoom' as const,
    model: zoom,
    label: t('avatar.zoom'),
    hint: t('avatar.zoomHint'),
    limits: LIMITS.zoom,
    step: 0.05,
    display: `${zoom.value.toFixed(2)}×`,
    low: t('avatar.zoomFar'),
    high: t('avatar.zoomNear'),
    decimals: 2,
  },
])

function nudge(field: (typeof fields.value)[number], direction: 1 | -1) {
  const next = field.model.value + field.step * direction
  const rounded = Number(next.toFixed(field.decimals))
  field.model.value = clamp(rounded, field.limits)
}

async function save() {
  const payload = {
    avatar_width: clamp(Math.round(width.value), LIMITS.width),
    avatar_height: clamp(Math.round(height.value), LIMITS.height),
    avatar_zoom: Number(clamp(zoom.value, LIMITS.zoom).toFixed(2)),
  }
  width.value = payload.avatar_width
  height.value = payload.avatar_height
  zoom.value = payload.avatar_zoom
  try {
    await updateAssistantProfile(payload)
    toast.add({
      severity: 'success',
      summary: t('avatar.saved'),
      detail: t('avatar.savedDetail'),
      life: 3000,
    })
  } catch {
    toast.add({
      severity: 'error',
      summary: t('common.error'),
      detail: t('avatar.saveError'),
      life: 3000,
    })
  }
}

function restoreDefaults() {
  width.value = DEFAULTS.width
  height.value = DEFAULTS.height
  zoom.value = DEFAULTS.zoom
}

onMounted(getAssistantProfile)
</script>

<template>
  <div class="avatar-container">
    <div class="header-section">
      <div class="integration-header">
        <div class="icon-wrapper avatar-icon">
          <i class="pi pi-user"></i>
        </div>
        <div class="header-content">
          <h1 class="integration-title">{{ t('avatar.title') }}</h1>
          <p class="integration-subtitle">{{ t('avatar.subtitle') }}</p>
        </div>
        <Button
          :label="t('avatar.save')"
          icon="pi pi-check"
          severity="primary"
          class="save-btn"
          :loading="saving"
          @click="save"
        />
      </div>
    </div>

    <div v-if="loading" class="panel state-panel">
      <div class="centered-state">
        <i class="pi pi-spin pi-spinner state-icon"></i>
        <p>{{ t('avatar.loading') }}</p>
      </div>
    </div>

    <div v-else class="layout-grid">
      <div class="panel controls-panel">
        <div class="panel-body">
          <div v-for="field in fields" :key="field.key" class="field">
            <label class="field-label">
              {{ field.label }}
              <span class="field-value">{{ field.display }}</span>
            </label>
            <div class="field-row">
              <Button
                icon="pi pi-minus"
                severity="secondary"
                outlined
                class="step-btn"
                :aria-label="`${field.label} -`"
                :disabled="field.model.value <= field.limits.min"
                @click="nudge(field, -1)"
              />
              <Slider
                v-model="field.model.value"
                :min="field.limits.min"
                :max="field.limits.max"
                :step="field.step"
                class="field-slider"
              />
              <Button
                icon="pi pi-plus"
                severity="secondary"
                outlined
                class="step-btn"
                :aria-label="`${field.label} +`"
                :disabled="field.model.value >= field.limits.max"
                @click="nudge(field, 1)"
              />
            </div>
            <div class="field-scale">
              <span>{{ field.low }}</span>
              <span>{{ field.high }}</span>
            </div>
            <small class="field-hint">{{ field.hint }}</small>
          </div>

          <div class="actions">
            <Button
              :label="t('avatar.restore')"
              icon="pi pi-replay"
              severity="secondary"
              text
              :disabled="isDefault"
              @click="restoreDefaults"
            />
          </div>
        </div>
      </div>

      <div class="panel preview-panel">
        <div class="panel-body preview-body">
          <h3 class="preview-title">{{ t('avatar.preview') }}</h3>
          <div class="preview-frame" :style="previewStyle">
            <div class="preview-subject" :style="subjectStyle">
              <i class="pi pi-user"></i>
            </div>
          </div>
          <p class="preview-caption">{{ width }} × {{ height }} px</p>
        </div>
      </div>
    </div>

    <Message severity="info" :closable="false" class="restart-note">
      {{ t('avatar.restartNote') }}
    </Message>

    <Toast position="top-right" />
  </div>
</template>

<style scoped>
.avatar-container {
  max-width: 1100px;
  margin: 0 auto;
  padding: 1rem 1.25rem;
  min-height: 100vh;
  background: var(--do-bg);
  box-sizing: border-box;
}

.header-section {
  margin-bottom: 1.5rem;
}

.integration-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
}

.icon-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 2rem;
  color: var(--do-blue);
  flex-shrink: 0;
}

.avatar-icon {
  background: linear-gradient(135deg, #8b5cf6 0%, #5b21b6 100%);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}

.header-content {
  flex: 1;
  min-width: 0;
}

.integration-title {
  font-size: 1.6rem;
  font-weight: 700;
  margin: 0 0 0.25rem 0;
  color: var(--do-text);
}

.integration-subtitle {
  font-size: 0.95rem;
  color: var(--do-text-muted);
  margin: 0;
}

.save-btn {
  margin-left: auto;
  flex-shrink: 0;
}

.panel {
  border: 1px solid var(--do-border-light);
  border-radius: 0.75rem;
  overflow: hidden;
  background: var(--do-bg);
}

.state-panel {
  margin-bottom: 1rem;
}

.centered-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  padding: 2rem 1rem;
  text-align: center;
}

.state-icon {
  font-size: 1.75rem;
  color: var(--do-text-muted);
}

.layout-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr);
  gap: 1rem;
  align-items: start;
}

.panel-body {
  padding: 1.25rem;
}

.field {
  margin-bottom: 1.5rem;
}

.field:last-of-type {
  margin-bottom: 1rem;
}

.field-label {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.5rem;
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--do-text);
  margin-bottom: 0.5rem;
}

.field-input {
  width: 100%;
}

.field-hint {
  display: block;
  margin-top: 0.4rem;
  font-size: 0.8rem;
  color: var(--do-text-muted);
}

.field-value {
  font-variant-numeric: tabular-nums;
  color: var(--do-text-muted);
  font-weight: 500;
}

.field-row {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.field-slider {
  flex: 1;
  min-width: 0;
}

.step-btn {
  flex-shrink: 0;
  width: 2.5rem;
  height: 2.5rem;
}

.field-scale {
  display: flex;
  justify-content: space-between;
  font-size: 0.75rem;
  color: var(--do-text-muted);
  margin-top: 0.5rem;
}

@media (max-width: 560px) {
  .field-row {
    gap: 0.5rem;
  }

  .step-btn {
    width: 2.25rem;
    height: 2.25rem;
  }
}

.actions {
  display: flex;
  justify-content: flex-end;
  border-top: 1px solid var(--do-border-light);
  padding-top: 0.75rem;
}

.preview-body {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
}

.preview-title {
  align-self: flex-start;
  font-size: 0.9rem;
  font-weight: 600;
  margin: 0;
  color: var(--do-text);
}

.preview-frame {
  position: relative;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  border: 1px dashed var(--do-border-light);
  border-radius: 0.5rem;
  background:
    linear-gradient(45deg, rgba(139, 92, 246, 0.06) 25%, transparent 25%) 0 0 / 16px 16px,
    linear-gradient(-45deg, rgba(139, 92, 246, 0.06) 25%, transparent 25%) 0 0 / 16px 16px;
  transition: width 0.15s ease, height 0.15s ease;
  overflow: hidden;
}

.preview-subject {
  display: flex;
  align-items: center;
  justify-content: center;
  aspect-ratio: 1 / 2.6;
  background: linear-gradient(180deg, #8b5cf6 0%, #5b21b6 100%);
  border-radius: 999px 999px 0 0;
  color: #fff;
  opacity: 0.75;
  transition: height 0.15s ease;
}

.preview-subject i {
  font-size: 1.25rem;
  margin-bottom: 20%;
}

.preview-caption {
  margin: 0;
  font-size: 0.8rem;
  color: var(--do-text-muted);
  font-variant-numeric: tabular-nums;
}

.restart-note {
  margin-top: 1rem;
}

@media (max-width: 820px) {
  .layout-grid {
    grid-template-columns: 1fr;
  }
}
</style>
