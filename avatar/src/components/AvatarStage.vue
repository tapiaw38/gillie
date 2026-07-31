<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type { AnimationType } from '@/avatar/animation-catalog'
import type { AnimationPlayback } from '@/avatar/animation-action'
import { createAvatarStage, type AvatarStage } from '@/avatar/stage'

const props = defineProps<{
  animation: AnimationType
  animationRequest: number
  audioLevel: number
  playback: AnimationPlayback
  speaking: boolean
}>()

const emit = defineEmits<{ (event: 'animation-complete'): void }>()

const canvas = ref<HTMLCanvasElement | null>(null)
let stage: AvatarStage | null = null

onMounted(() => {
  if (!canvas.value) return
  stage = createAvatarStage(canvas.value)
  stage.ready.catch((error) => console.error('[avatar] character failed to load', error))

  stage.setAudioLevel(props.audioLevel)
  stage.setSpeaking(props.speaking)

  watch(
    () => [props.animation, props.animationRequest] as const,
    () => {
      stage?.play(props.animation, {
        playback: props.playback,
        onComplete: () => emit('animation-complete'),
      })
    },
    { immediate: true },
  )
  watch(
    () => props.audioLevel,
    (level) => stage?.setAudioLevel(level),
  )
  watch(
    () => props.speaking,
    (value) => stage?.setSpeaking(value),
  )
})

onBeforeUnmount(() => {
  stage?.dispose()
  stage = null
})
</script>

<template>
  <canvas ref="canvas" class="avatar-stage" />
</template>

<style scoped>
.avatar-stage {
  display: block;
  width: 100%;
  height: 100%;
  background: transparent;
}
</style>
