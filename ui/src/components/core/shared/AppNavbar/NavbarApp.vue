<script setup lang="ts">
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import gillieIcon from '@/assets/icons/gillie-logo.png'
import { useBackendStatus } from '@/composables/useBackendStatus'
import { useStorage } from '@/composables/useStorage'

const route = useRoute()
const router = useRouter()
const { isActive, cause } = useBackendStatus()
const { t, locale } = useI18n()
const { setItem } = useStorage()

const isActiveLink = (path: string) => route.path === path
const canGoBack = () => route.path !== '/app/dashboard'

const setLocale = (lang: string) => {
  locale.value = lang
  setItem('gillie-lang', lang)
}

const routerLinks: { icon: string; label: string; url: string }[] = []
</script>

<template>
  <nav class="navbar">
    <!-- Brand -->
    <div class="navbar-brand">
      <button v-if="canGoBack()" class="back-btn" @click="router.back()" :title="t('nav.back')">
        <i class="pi pi-arrow-left" />
      </button>
      <img :src="gillieIcon" alt="Gillie" class="brand-logo" />
    </div>

    <!-- Navigation links -->
    <div class="navbar-center">
      <RouterLink
        v-for="link in routerLinks"
        :key="link.url"
        :to="link.url"
        class="nav-item"
        :class="{ 'nav-item--active': isActiveLink(link.url) }"
      >
        <i :class="link.icon" />
        <span class="nav-label">{{ link.label }}</span>
      </RouterLink>
    </div>

    <!-- Right side: language switcher + status -->
    <div class="navbar-end">
      <!-- Language Switcher -->
      <div class="lang-switcher">
        <button
          class="lang-btn"
          :class="{ 'lang-btn--active': locale === 'en' }"
          @click="setLocale('en')"
        >EN</button>
        <button
          class="lang-btn"
          :class="{ 'lang-btn--active': locale === 'es' }"
          @click="setLocale('es')"
        >ES</button>
      </div>

      <!-- Status indicator -->
      <div class="status-indicator" :class="isActive ? 'status--active' : 'status--inactive'">
        <span class="status-dot" />
        <div class="status-text">
          <span class="status-label">{{ isActive ? t('nav.active') : t('nav.inactive') }}</span>
          <span v-if="!isActive && cause" class="status-cause">{{ cause }}</span>
        </div>
      </div>
    </div>
  </nav>
</template>

<style scoped>
.navbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 1.25rem;
  height: 3.25rem;
  background: rgba(6,13,26,0.9);
  backdrop-filter: blur(20px);
  border-bottom: 1px solid rgba(255,255,255,0.08);
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
}

/* Brand */
.navbar-brand {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-shrink: 0;
}

.back-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.9rem;
  height: 1.9rem;
  border: none;
  background: rgba(255,255,255,0.06);
  color: var(--do-text-secondary);
  border-radius: 0.4rem;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
  flex-shrink: 0;
}

.back-btn:hover {
  background: rgba(255,255,255,0.1);
  color: var(--do-text);
}

.brand-logo {
  width: 2.2rem;
  height: 2.2rem;
  object-fit: contain;
  filter: drop-shadow(0 0 8px rgba(59,130,246,0.4));
}

/* Nav links */
.navbar-center {
  display: flex;
  align-items: center;
  gap: 0.2rem;
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  color: var(--do-text-secondary);
  text-decoration: none;
  font-weight: 500;
  font-size: 0.8125rem;
  padding: 0.35rem 0.65rem;
  border-radius: 0.375rem;
  transition: background 0.15s ease, color 0.15s ease;
  white-space: nowrap;
}

.nav-item:hover {
  background: rgba(255,255,255,0.06);
  color: var(--do-text);
}

.nav-item--active {
  background: rgba(59,130,246,0.15);
  color: var(--do-blue);
}

/* Right side */
.navbar-end {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-shrink: 0;
}

/* Language Switcher */
.lang-switcher {
  display: flex;
  align-items: center;
  gap: 0.1rem;
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 0.4rem;
  padding: 0.15rem;
}

.lang-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0.2rem 0.45rem;
  border: none;
  background: transparent;
  color: var(--do-text-secondary);
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  border-radius: 0.25rem;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
  line-height: 1;
}

.lang-btn:hover {
  background: rgba(255,255,255,0.08);
  color: var(--do-text);
}

.lang-btn--active {
  background: rgba(59,130,246,0.25);
  color: var(--do-blue);
}

/* Status */
.status-indicator {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.25rem 0.6rem;
  border-radius: 1rem;
  transition: background 0.3s, border-color 0.3s;
}

.status--active {
  background: rgba(10,207,131,0.08);
  border: 1px solid rgba(10,207,131,0.2);
}

.status--inactive {
  background: rgba(255,68,68,0.08);
  border: 1px solid rgba(255,68,68,0.2);
}

.status-dot {
  width: 0.45rem;
  height: 0.45rem;
  border-radius: 50%;
  flex-shrink: 0;
  transition: background 0.3s;
}

.status--active .status-dot {
  background: var(--color-success);
  box-shadow: 0 0 6px rgba(10,207,131,0.6);
}

.status--inactive .status-dot {
  background: var(--color-danger);
  box-shadow: 0 0 6px rgba(255,68,68,0.6);
}

.status-text {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
}

.status-label {
  font-size: 0.75rem;
  font-weight: 600;
  transition: color 0.3s;
}

.status--active .status-label { color: var(--color-success); }
.status--inactive .status-label { color: var(--color-danger); }

.status-cause {
  font-size: 0.65rem;
  font-weight: 400;
  color: var(--do-text-muted);
  white-space: nowrap;
}

/* Mobile */
@media (max-width: 640px) {
  .navbar {
    padding: 0 0.75rem;
  }

  .navbar-center {
    position: static;
    transform: none;
    gap: 0.1rem;
  }

  .nav-label {
    display: none;
  }

  .nav-item {
    padding: 0.4rem;
    font-size: 1rem;
  }

  .brand-logo {
    width: 1.9rem;
    height: 1.9rem;
  }

  .status-cause {
    display: none;
  }
}

@media (prefers-reduced-motion: reduce) {
  .nav-item, .status-indicator { transition: none; }
}
</style>
