<script setup lang="ts">
import { RouterLink, useRoute } from 'vue-router'
import { computed } from 'vue'
import { useAssistant } from '@/composables/useAssistant'
import gillieIcon from '@/assets/icons/gillie.png'

const { assistantProfile } = useAssistant()
const route = useRoute()

const isActive = (path: string) => route.path === path

const routerLinks = [
  {
    icon: 'pi pi-th-large',
    label: 'Panel',
    url: '/dashboard',
  },
  {
    icon: 'pi pi-comments',
    label: 'Conversaciones',
    url: '/conversation',
  },
  {
    icon: 'pi pi-cog',
    label: 'Mi Cuenta',
    url: '/my-account',
  },
]

const assistantName = computed(() => assistantProfile.value?.assistant_name || 'Gillie')
</script>

<template>
  <nav class="navbar">
    <!-- Brand -->
    <div class="navbar-brand d-flex">
      <img :src="gillieIcon" alt="Gillie" class="brand-logo" />
      <span class="brand-name">{{ assistantName }}</span>
    </div>

    <!-- Navigation links -->
    <div class="navbar-center">
      <RouterLink
        v-for="link in routerLinks"
        :key="link.url"
        :to="link.url"
        class="nav-item"
        :class="{ 'nav-item--active': isActive(link.url) }"
      >
        <i :class="link.icon" class="mr-2" />
        <span>{{ link.label }}</span>
      </RouterLink>
    </div>

    <!-- Right side status indicator -->
    <div class="navbar-end">
      <div class="status-indicator">
        <span class="status-dot"></span>
        <span class="status-label">Activo</span>
      </div>
    </div>
  </nav>
</template>

<style scoped>
.navbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 1.5rem;
  height: 3.25rem;
  background: var(--do-bg-white);
  border-bottom: 1px solid var(--do-border-light);
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}

/* Brand */
.navbar-brand {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  text-decoration: none;
  flex-shrink: 0;
}

.brand-logo {
  width: 6rem;
  height: 6rem;
  object-fit: contain;
}

.brand-name {
  font-size: 0.9rem;
  font-weight: 700;
  color: var(--do-text);
  letter-spacing: -0.01em;
}

.navbar-center {
  display: flex;
  align-items: center;
  gap: 0.25rem;
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
  transition:
    background 0.15s ease,
    color 0.15s ease;
}

.nav-item:hover {
  background: var(--do-bg);
  color: var(--do-text);
}

.nav-item--active {
  background: rgba(0, 105, 255, 0.08);
  color: var(--do-blue);
}

.nav-item--active i {
  color: var(--do-blue);
}

.navbar-end {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.25rem 0.6rem;
  background: rgba(10, 207, 131, 0.08);
  border: 1px solid rgba(10, 207, 131, 0.2);
  border-radius: 1rem;
}

.status-dot {
  width: 0.45rem;
  height: 0.45rem;
  border-radius: 50%;
  background: var(--do-success);
  flex-shrink: 0;
}

.status-label {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--do-success);
}

/* Responsive */
@media (max-width: 768px) {
  .navbar {
    padding: 0 1rem;
  }

  .navbar-center {
    position: static;
    transform: none;
    gap: 0.1rem;
  }

  .nav-item span {
    display: none;
  }

  .brand-name {
    display: none;
  }

  .status-label {
    display: none;
  }
}

@media (prefers-reduced-motion: reduce) {
  .nav-item {
    transition: none;
  }
}
</style>
