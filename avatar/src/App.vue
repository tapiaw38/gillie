<script setup lang="ts">
import AvatarStage from '@/components/AvatarStage.vue'
import { useAvatarBridge } from '@/composables/useAvatarBridge'

const {
  animation,
  animationRequest,
  audioLevel,
  handleAnimationComplete,
  playback,
  speaking,
} = useAvatarBridge()
</script>

<template>
  <main class="app">
    <AvatarStage
      :animation="animation"
      :animation-request="animationRequest"
      :audio-level="audioLevel"
      :playback="playback"
      :speaking="speaking"
      @animation-complete="handleAnimationComplete"
    />
  </main>
</template>
