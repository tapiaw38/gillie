<script setup lang="ts">
import { computed, inject, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from 'primevue/usetoast'
import Card from 'primevue/card'
import Dropdown from 'primevue/dropdown'
import InputSwitch from 'primevue/inputswitch'
import Slider from 'primevue/slider'
import LoadingSpinner from '@/components/core/LoadingSpinner/LoadingSpinner.vue'
import { useAssistant } from '@/composables/useAssistant'
import type { IAssistantService } from '@/services/assistant/assistantService'
import type { VoiceEngineOption } from '@/types/assistant'

const { t } = useI18n()
const toast = useToast()
const services = inject<{ assistantService: IAssistantService }>('services')
const {
  assistantProfile,
  getAssistantProfile,
  updateAssistantProfile,
  isGetAssistantProfilePending: loading,
  isUpdateAssistantProfilePending: saving,
} = useAssistant()

const ttsEnabled = ref(false)
const ttsEngine = ref('')
const ttsVoice = ref('')
const ttsPitch = ref(0)
const responseLang = ref<'en' | 'es'>('en')
const voiceEngines = ref<VoiceEngineOption[]>([])

const selectedEngine = computed(() =>
  voiceEngines.value.find((item) => item.key === ttsEngine.value),
)
const engineOptions = computed(() =>
  voiceEngines.value.map((engine) => ({
    label:
      engine.requires_key && !engine.key_available
        ? `${engine.label} — ${t('voice.engineNoKey')}`
        : engine.label,
    value: engine.key,
    disabled: engine.requires_key && !engine.key_available,
  })),
)
const voiceOptions = computed(() =>
  (selectedEngine.value?.voices ?? []).map((voice) => ({
    label: voice.label,
    value: voice.id,
  })),
)

watch(
  () => assistantProfile.value?.tts_enabled,
  (value) => {
    ttsEnabled.value = value ?? false
  },
  { immediate: true },
)
watch(
  () => assistantProfile.value?.tts_engine,
  (value) => {
    ttsEngine.value = value ?? 'edge'
  },
  { immediate: true },
)
watch(
  () => assistantProfile.value?.tts_voice,
  (value) => {
    ttsVoice.value = value ?? ''
  },
  { immediate: true },
)
watch(
  () => assistantProfile.value?.tts_pitch,
  (value) => {
    ttsPitch.value = value ?? 0
  },
  { immediate: true },
)
watch(
  () => assistantProfile.value?.response_language,
  (value) => {
    if (value === 'en' || value === 'es') responseLang.value = value
  },
  { immediate: true },
)

onMounted(async () => {
  await getAssistantProfile()
  try {
    const options = await services!.assistantService.getOptions()
    voiceEngines.value = options.data.voice_engines ?? []
  } catch {
    voiceEngines.value = []
  }
})

async function save(payload: Record<string, unknown>, detail: string) {
  try {
    await updateAssistantProfile(payload)
    toast.add({ severity: 'success', summary: t('voice.saved'), detail, life: 2500 })
  } catch {
    toast.add({
      severity: 'error',
      summary: t('common.error'),
      detail: t('voice.saveError'),
      life: 3000,
    })
  }
}

async function setEngine(engine: string) {
  const target = voiceEngines.value.find((item) => item.key === engine)
  const voice = target?.voices[0]?.id ?? ''
  ttsEngine.value = engine
  ttsVoice.value = voice
  await save(
    { tts_engine: engine, tts_voice: voice },
    t('voice.engineSet', { engine: target?.label ?? engine }),
  )
}

async function setVoice(voice: string) {
  await save({ tts_voice: voice }, t('voice.voiceSet', { voice }))
}

async function setPitch(event: number | number[] | { value: number | number[] }) {
  const value = typeof event === 'object' && !Array.isArray(event) ? event.value : event
  const next = Number(Array.isArray(value) ? value[0] : value)
  ttsPitch.value = next
  await save({ tts_pitch: next }, t('voice.pitchSet', { value: next > 0 ? `+${next}` : next }))
}

async function setEnabled(value: boolean) {
  await save({ tts_enabled: value }, value ? t('voice.enabled') : t('voice.disabled'))
}

async function setLanguage(lang: 'en' | 'es') {
  responseLang.value = lang
  await save({ response_language: lang }, lang === 'en' ? t('voice.english') : t('voice.spanish'))
}
</script>

<template>
  <main class="voice-page">
    <div class="page-heading">
      <div class="icon-wrapper"><i class="pi pi-microphone" /></div>
      <div>
        <h1>{{ t('voice.title') }}</h1>
        <p>{{ t('voice.subtitle') }}</p>
      </div>
    </div>

    <div v-if="loading" class="loading-state">
      <LoadingSpinner />
      <p>{{ t('voice.loading') }}</p>
    </div>
    <template v-else>
      <Card class="voice-card">
        <template #content
          ><div class="setting-row">
            <div>
              <h3>{{ t('voice.audioResponses') }}</h3>
              <p>{{ t('voice.audioResponsesDesc') }}</p>
            </div>
            <InputSwitch
              v-model="ttsEnabled"
              :disabled="saving"
              @change="setEnabled(ttsEnabled)"
            /></div
        ></template>
      </Card>

      <Card v-if="ttsEnabled" class="voice-card">
        <template #content>
          <div class="setting-row">
            <div>
              <h3>{{ t('voice.engine') }}</h3>
              <p>{{ selectedEngine?.description || t('voice.engineDesc') }}</p>
            </div>
            <Dropdown
              v-model="ttsEngine"
              :options="engineOptions"
              optionLabel="label"
              optionValue="value"
              optionDisabled="disabled"
              :disabled="saving"
              class="voice-dropdown"
              @change="setEngine(ttsEngine)"
            />
          </div>
          <div v-if="voiceOptions.length" class="setting-row nested">
            <div>
              <h3>{{ t('voice.voice') }}</h3>
              <p>{{ t('voice.voiceDesc') }}</p>
            </div>
            <Dropdown
              v-model="ttsVoice"
              :options="voiceOptions"
              optionLabel="label"
              optionValue="value"
              :disabled="saving"
              class="voice-dropdown"
              @change="setVoice(ttsVoice)"
            />
          </div>
          <div class="pitch-setting">
            <div>
              <h3>{{ t('voice.pitch') }}</h3>
              <p>{{ t('voice.pitchDesc') }}</p>
            </div>
            <div class="pitch-control">
              <span>{{ t('voice.lower') }}</span
              ><Slider
                v-model="ttsPitch"
                :min="-6"
                :max="6"
                :step="1"
                :disabled="saving"
                @change="setPitch"
              /><span>{{ t('voice.higher') }}</span
              ><strong>{{ ttsPitch > 0 ? `+${ttsPitch}` : ttsPitch }} st</strong>
            </div>
          </div>
        </template>
      </Card>

      <Card class="voice-card">
        <template #content
          ><div class="setting-row">
            <div>
              <h3>{{ t('voice.language') }}</h3>
              <p>{{ t('voice.languageDesc') }}</p>
            </div>
            <div class="lang-toggle">
              <button
                :class="{ active: responseLang === 'en' }"
                :disabled="saving"
                @click="setLanguage('en')"
              >
                EN</button
              ><button
                :class="{ active: responseLang === 'es' }"
                :disabled="saving"
                @click="setLanguage('es')"
              >
                ES
              </button>
            </div>
          </div></template
        >
      </Card>
    </template>
  </main>
</template>

<style scoped>
.voice-page {
  max-width: 860px;
  margin: 0 auto;
  padding: 2.5rem 1.5rem 4rem;
}
.page-heading {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 2rem;
}
.page-heading h1 {
  margin: 0;
  color: var(--do-text);
  font-size: 1.7rem;
}
.page-heading p,
.setting-row p {
  margin: 0.35rem 0 0;
  color: var(--do-text-secondary);
}
.icon-wrapper {
  display: grid;
  place-items: center;
  width: 3rem;
  height: 3rem;
  border-radius: 0.8rem;
  background: rgba(59, 130, 246, 0.15);
  color: var(--do-blue);
  font-size: 1.4rem;
}
.voice-card {
  margin-bottom: 1rem;
}
.setting-row,
.pitch-setting {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1.5rem;
}
.setting-row h3,
.pitch-setting h3 {
  margin: 0;
  color: var(--do-text);
}
.nested,
.pitch-setting {
  margin-top: 1.5rem;
  padding-top: 1.5rem;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}
.voice-dropdown {
  min-width: 16rem;
}
.pitch-control {
  display: grid;
  grid-template-columns: auto minmax(12rem, 20rem) auto;
  align-items: center;
  gap: 0.7rem;
  color: var(--do-text-secondary);
  font-size: 0.8rem;
}
.pitch-control strong {
  grid-column: 2;
  justify-self: center;
  color: var(--do-text);
}
.lang-toggle {
  display: flex;
  gap: 0.3rem;
}
.lang-toggle button {
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: transparent;
  color: var(--do-text-secondary);
  padding: 0.45rem 0.8rem;
  border-radius: 0.35rem;
  cursor: pointer;
}
.lang-toggle button.active {
  background: rgba(59, 130, 246, 0.2);
  color: var(--do-blue);
}
.loading-state {
  display: grid;
  place-items: center;
  gap: 0.6rem;
  color: var(--do-text-secondary);
}
@media (max-width: 640px) {
  .setting-row,
  .pitch-setting {
    align-items: stretch;
    flex-direction: column;
  }
  .voice-dropdown,
  .pitch-control {
    width: 100%;
  }
}
</style>
