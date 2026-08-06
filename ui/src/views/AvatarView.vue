<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from 'primevue/usetoast'
import { useAssistant } from '@/composables/useAssistant'
import Button from 'primevue/button'
import Slider from 'primevue/slider'
import Toast from 'primevue/toast'
import Message from 'primevue/message'
import InputSwitch from 'primevue/inputswitch'
import { inject } from 'vue'
import type { IAvatarService } from '@/services/avatar/avatarService'

const { t } = useI18n()
const toast = useToast()
const services = inject<{ avatarService: IAvatarService }>('services')
const avatarService = services!.avatarService
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
const avatarAssets = ref<{ model: string | null; animations: string[] }>({
  model: null,
  animations: [],
})
const assetsBusy = ref(false)
const assetsDirty = ref(false)
const assetsLoadError = ref(false)
const storageMode = ref<'local' | 'remote'>(
  (localStorage.getItem('gillie-avatar-storage') as 'local' | 'remote') || 'local',
)
const remoteModelInput = ref<HTMLInputElement | null>(null)
const remoteAnimationsInput = ref<HTMLInputElement | null>(null)
const hasElectron = computed(() => Boolean(window.electronAPI?.avatar))

async function loadAvatarAssets() {
  try {
    if (storageMode.value === 'remote') {
      const response = await avatarService.listAssets()
      avatarAssets.value = {
        model: response.data.model?.name || null,
        animations: response.data.animations.map((asset) => asset.name),
      }
    } else if (window.electronAPI?.avatar) {
      avatarAssets.value = await window.electronAPI.avatar.listAssets()
    }
    assetsLoadError.value = false
  } catch {
    assetsLoadError.value = true
  }
}

function setStorageMode(remote: boolean) {
  storageMode.value = remote ? 'remote' : 'local'
  localStorage.setItem('gillie-avatar-storage', storageMode.value)
  assetsDirty.value = false
  void loadAvatarAssets()
}

async function uploadRemoteFiles(files: File[], type: 'model' | 'animation') {
  assetsBusy.value = true
  try {
    for (const file of files) {
      const response = await avatarService.uploadAsset(file, type)
      avatarAssets.value = {
        model: response.data.model?.name || null,
        animations: response.data.animations.map((asset) => asset.name),
      }
    }
    assetsDirty.value = true
    toast.add({ severity: 'success', summary: t('avatar.assetAdded'), life: 2500 })
  } catch (error) {
    toast.add({ severity: 'error', summary: t('common.error'), detail: String(error), life: 4000 })
  } finally {
    assetsBusy.value = false
  }
}

function onRemoteModelSelected(event: Event) {
  const files = Array.from((event.target as HTMLInputElement).files || [])
  if (files[0]) void uploadRemoteFiles([files[0]], 'model')
}

function onRemoteAnimationsSelected(event: Event) {
  const files = Array.from((event.target as HTMLInputElement).files || [])
  if (files.length) void uploadRemoteFiles(files, 'animation')
}

async function importModel() {
  if (storageMode.value === 'remote') {
    remoteModelInput.value?.click()
    return
  }
  if (!window.electronAPI?.avatar) return
  assetsBusy.value = true
  try {
    avatarAssets.value = await window.electronAPI.avatar.importModel()
    assetsDirty.value = true
    toast.add({ severity: 'success', summary: t('avatar.assetAdded'), life: 2500 })
  } catch (error) {
    toast.add({ severity: 'error', summary: t('common.error'), detail: String(error), life: 4000 })
  } finally {
    assetsBusy.value = false
  }
}

async function importAnimations() {
  if (storageMode.value === 'remote') {
    remoteAnimationsInput.value?.click()
    return
  }
  if (!window.electronAPI?.avatar) return
  assetsBusy.value = true
  try {
    avatarAssets.value = await window.electronAPI.avatar.importAnimations()
    assetsDirty.value = true
    toast.add({ severity: 'success', summary: t('avatar.assetAdded'), life: 2500 })
  } catch (error) {
    toast.add({ severity: 'error', summary: t('common.error'), detail: String(error), life: 4000 })
  } finally {
    assetsBusy.value = false
  }
}

async function removeAnimation(name: string) {
  if (storageMode.value === 'remote') {
    assetsBusy.value = true
    try {
      const response = await avatarService.removeAnimation(name)
      avatarAssets.value = {
        model: response.data.model?.name || null,
        animations: response.data.animations.map((asset) => asset.name),
      }
      assetsDirty.value = true
    } catch (error) {
      toast.add({
        severity: 'error',
        summary: t('common.error'),
        detail: String(error),
        life: 4000,
      })
    } finally {
      assetsBusy.value = false
    }
    return
  }
  if (!window.electronAPI?.avatar) return
  assetsBusy.value = true
  try {
    avatarAssets.value = await window.electronAPI.avatar.removeAnimation(name)
    assetsDirty.value = true
  } catch (error) {
    toast.add({ severity: 'error', summary: t('common.error'), detail: String(error), life: 4000 })
  } finally {
    assetsBusy.value = false
  }
}

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
    if (assetsDirty.value && storageMode.value === 'remote') {
      assetsBusy.value = true
      await avatarService.rebuild()
      assetsDirty.value = false
    } else if (assetsDirty.value && window.electronAPI?.avatar) {
      assetsBusy.value = true
      await window.electronAPI.avatar.save()
      assetsDirty.value = false
    }
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
  } finally {
    assetsBusy.value = false
  }
}

function restoreDefaults() {
  width.value = DEFAULTS.width
  height.value = DEFAULTS.height
  zoom.value = DEFAULTS.zoom
}

onMounted(async () => {
  await Promise.all([getAssistantProfile(), loadAvatarAssets()])
})
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

    <div class="panel assets-panel">
      <div class="panel-body">
        <div class="assets-header">
          <div>
            <h3 class="preview-title">{{ t('avatar.assetsTitle') }}</h3>
            <small class="field-hint">{{ t('avatar.assetsHint') }}</small>
          </div>
        </div>
        <div class="storage-mode-row">
          <div class="storage-mode-copy">
            <i :class="storageMode === 'remote' ? 'pi pi-cloud' : 'pi pi-desktop'" />
            <div>
              <strong>{{
                storageMode === 'remote' ? t('avatar.remoteStorage') : t('avatar.localStorage')
              }}</strong>
              <small>{{
                storageMode === 'remote'
                  ? t('avatar.remoteStorageHint')
                  : t('avatar.localStorageHint')
              }}</small>
            </div>
          </div>
          <InputSwitch
            :model-value="storageMode === 'remote'"
            @update:model-value="setStorageMode"
          />
        </div>
        <div class="asset-actions">
          <Button
            :label="t('avatar.replaceModel')"
            icon="pi pi-upload"
            severity="secondary"
            outlined
            :loading="assetsBusy"
            :disabled="storageMode === 'local' && !hasElectron"
            @click="importModel"
          />
          <Button
            :label="t('avatar.addAnimations')"
            icon="pi pi-plus"
            :loading="assetsBusy"
            :disabled="storageMode === 'local' && !hasElectron"
            @click="importAnimations"
          />
          <input
            ref="remoteModelInput"
            type="file"
            accept=".vrm"
            hidden
            @change="onRemoteModelSelected"
          />
          <input
            ref="remoteAnimationsInput"
            type="file"
            accept=".vrma"
            multiple
            hidden
            @change="onRemoteAnimationsSelected"
          />
        </div>
        <div class="asset-list">
          <div class="asset-row">
            <span
              ><i class="pi pi-user" /> {{ avatarAssets.model || t('avatar.modelMissing') }}</span
            >
            <small>{{ t('avatar.modelRequired') }}</small>
          </div>
          <div v-for="animation in avatarAssets.animations" :key="animation" class="asset-row">
            <span><i class="pi pi-play" /> {{ animation }}</span>
            <Button
              icon="pi pi-trash"
              severity="danger"
              text
              rounded
              :aria-label="`${t('avatar.removeAnimation')} ${animation}`"
              :disabled="assetsBusy"
              @click="removeAnimation(animation)"
            />
          </div>
          <small v-if="avatarAssets.animations.length === 0" class="field-hint">{{
            t('avatar.noAnimations')
          }}</small>
        </div>
        <small v-if="storageMode === 'local' && !hasElectron" class="dirty-note">{{
          t('avatar.desktopOnly')
        }}</small>
        <small v-if="assetsLoadError" class="dirty-note">{{ t('avatar.assetsLoadError') }}</small>
        <small v-if="assetsDirty" class="dirty-note">{{ t('avatar.unsavedAssets') }}</small>
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
  transition:
    width 0.15s ease,
    height 0.15s ease;
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

.assets-panel {
  margin-top: 1rem;
}

.assets-header,
.asset-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.storage-mode-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin-top: 1rem;
  padding: 0.75rem 0.9rem;
  border: 1px solid var(--do-border-light);
  border-radius: 0.55rem;
  background: color-mix(in srgb, var(--do-blue) 5%, transparent);
}

.storage-mode-copy {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  min-width: 0;
}

.storage-mode-copy > i {
  color: var(--do-blue);
  font-size: 1.1rem;
}

.storage-mode-copy div {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}

.storage-mode-copy small {
  color: var(--do-text-muted);
  line-height: 1.3;
}

.asset-actions {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  justify-content: flex-end;
  margin-top: 0.75rem;
}

.asset-list {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  margin-top: 1rem;
}

.asset-row {
  min-height: 2.5rem;
  padding: 0.35rem 0.65rem;
  border: 1px solid var(--do-border-light);
  border-radius: 0.4rem;
}

.asset-row i {
  color: var(--do-blue);
  margin-right: 0.4rem;
}

.dirty-note {
  display: block;
  margin-top: 0.75rem;
  color: var(--do-warning, #b45309);
}

@media (max-width: 820px) {
  .layout-grid {
    grid-template-columns: 1fr;
  }

  .assets-header,
  .storage-mode-row {
    align-items: flex-start;
  }

  .storage-mode-row {
    flex-direction: column;
  }

  .asset-actions {
    justify-content: flex-start;
  }
}
</style>
