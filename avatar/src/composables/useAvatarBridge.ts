import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type { AnimationType } from '@/avatar/animation-catalog'
import type { AnimationPlayback } from '@/avatar/animation-action'
import {
  finishBodyAnimationOverride,
  resolveBodyAnimation,
  type BodyAnimationOverride,
} from '@/avatar/animation-priority'
import type { VoicePhase, VoiceState } from '@/types/bridge'

const INITIAL_STATE: VoiceState = {
  activity: 'idle',
  microphoneMuted: false,
  outputMuted: false,
  phase: 'inactive',
}

const BODY_IDLE_DELAY_MS = 650

export function useAvatarBridge() {
  const voice = ref<VoiceState>({ ...INITIAL_STATE })
  const audioLevel = ref(0)
  const voiceAnimation = ref<AnimationType>('IDLE')
  const bodyOverride = ref<BodyAnimationOverride | null>(null)
  const talkTurn = ref(0)

  let previousPhase: VoicePhase = 'inactive'
  let previousSpeaking = false
  let unsubscribe: (() => void) | null = null

  const speaking = computed(
    () =>
      voice.value.phase === 'active' &&
      voice.value.activity === 'speaking' &&
      !voice.value.outputMuted,
  )
  const animation = computed(() =>
    resolveBodyAnimation(voiceAnimation.value, bodyOverride.value),
  )
  const animationRequest = computed(
    () => bodyOverride.value?.requestId ?? (animation.value === 'TALK' ? talkTurn.value : 0),
  )
  const playback = computed<AnimationPlayback>(() =>
    bodyOverride.value ? 'once' : 'loop',
  )

  function handleAnimationComplete(): void {
    const requestId = bodyOverride.value?.requestId
    if (requestId == null) return
    bodyOverride.value = finishBodyAnimationOverride(bodyOverride.value, requestId)
  }

  onMounted(() => {
    const bridge = window.avatarBridge
    if (!bridge) return
    void bridge.getSnapshot().then((event) => {
      if (event?.type === 'state') voice.value = event.state
    })
    unsubscribe = bridge.subscribe((event) => {
      if (event.type === 'state') {
        voice.value = event.state
      } else if (event.type === 'audio-level') {
        audioLevel.value = event.level
      } else if (event.type === 'animation') {
        if (event.source === 'mcp' && event.requestId != null) {
          bodyOverride.value = {
            animation: event.animation,
            requestId: event.requestId,
          }
        } else {
          voiceAnimation.value = event.animation
        }
      }
    })
  })

  onBeforeUnmount(() => {
    unsubscribe?.()
    unsubscribe = null
  })

  watch(
    () =>
      [
        speaking.value,
        voice.value.activity,
        voice.value.outputMuted,
        voice.value.phase,
      ] as const,
    ([isSpeaking, activity, outputMuted, phase], _previous, onCleanup) => {
      const startedSpeaking = isSpeaking && !previousSpeaking
      previousSpeaking = isSpeaking
      if (startedSpeaking) talkTurn.value += 1

      if (phase === 'active' && previousPhase !== 'active') {
        voiceAnimation.value = 'GREETING'
        const timer = window.setTimeout(() => {
          voiceAnimation.value = activity === 'speaking' ? 'TALK' : 'IDLE'
        }, 2600)
        previousPhase = phase
        onCleanup(() => window.clearTimeout(timer))
        return
      }
      previousPhase = phase

      if (phase !== 'active' || outputMuted) {
        voiceAnimation.value = 'IDLE'
        audioLevel.value = 0
        return
      }

      if (activity === 'speaking' && !outputMuted) {
        voiceAnimation.value = 'TALK'
        return
      }

      const timer = window.setTimeout(() => {
        voiceAnimation.value = 'IDLE'
      }, BODY_IDLE_DELAY_MS)
      onCleanup(() => window.clearTimeout(timer))
    },
    { immediate: true },
  )

  return {
    animation,
    animationRequest,
    audioLevel,
    handleAnimationComplete,
    playback,
    speaking,
    voice,
  }
}
