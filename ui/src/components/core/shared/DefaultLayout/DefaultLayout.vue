<script setup lang="ts">
import { RouterView } from 'vue-router'
import NavbarApp from '@/components/core/shared/AppNavbar/NavbarApp.vue'
</script>

<template>
  <NavbarApp />
  <main class="layout-main">
    <RouterView />
  </main>
</template>

<style scoped>
.layout-main {
  width: 100%;
  min-height: 100vh;
  padding-top: 3.5rem;
  background-color: var(--do-bg);
  box-sizing: border-box;
}
</style>
