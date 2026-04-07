<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import gillieIcon from '@/assets/icons/gillie-logo.png'

const router = useRouter()
const { t } = useI18n()

function enter() {
  router.push('/app/dashboard')
}
</script>

<template>
  <div class="welcome">
    <div class="welcome-content">
      <h1 class="welcome-title">Gillie <span class="accent">AI</span></h1>
      <img :src="gillieIcon" alt="Gillie" class="welcome-fish" />
      <p class="welcome-subtitle">{{ t('welcome.subtitle') }}</p>
      <button class="welcome-btn" @click="enter">{{ t('welcome.start') }}</button>
    </div>
  </div>
</template>

<style scoped>
.welcome {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #000;
  padding: 2rem;
}

.welcome-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 1.5rem;
  max-width: 480px;
}

.welcome-fish {
  width: 440px;
  height: 440px;
  object-fit: contain;
  margin: 3rem 0 1.5rem;
  animation: float 4s ease-in-out infinite;
}

.welcome-title {
  font-size: 3rem;
  font-weight: 800;
  color: #fff;
  margin: 0;
  letter-spacing: -0.02em;
}

.accent {
  color: var(--do-blue);
}

.welcome-subtitle {
  font-size: 1.05rem;
  color: var(--do-text-secondary);
  margin: 0;
  line-height: 1.6;
}

.welcome-btn {
  margin-top: 0.5rem;
  padding: 0.85rem 2.5rem;
  background: var(--do-blue);
  color: #fff;
  border: none;
  border-radius: 999px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s, transform 0.2s;
}

.welcome-btn:hover {
  background: var(--do-blue-dark);
  transform: translateY(-2px);
}

@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-12px); }
}
</style>
