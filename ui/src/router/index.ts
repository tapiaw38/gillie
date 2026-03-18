import { createRouter, createWebHistory } from 'vue-router'
import DefaultLayout from '@/components/core/shared/DefaultLayout/DefaultLayout.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      component: DefaultLayout,
      children: [
        {
          path: '',
          redirect: '/dashboard',
        },
        {
          path: '/dashboard',
          name: 'dashboard',
          component: () => import('../views/DashboardView.vue'),
        },
        {
          path: '/my-account',
          name: 'my-account',
          component: () => import('../views/MyAccount.vue'),
        },
        {
          path: '/conversation',
          name: 'conversation',
          component: () => import('../views/ConversationView.vue'),
        },
        {
          path: '/store-integration',
          name: 'store-integration',
          component: () => import('../views/StoreIntegrationView.vue'),
        },
        {
          path: '/whatsapp-integration',
          name: 'whatsapp-integration',
          component: () => import('../views/WhatsappIntegrationView.vue'),
        },
        {
          path: '/whatsapp-devices',
          name: 'whatsapp-devices',
          component: () => import('../views/WhatsappDevicesView.vue'),
        },
        {
          path: '/meli-integration',
          name: 'meli-integration',
          component: () => import('../views/MercadolibreIntegrationView.vue'),
        },
        {
          path: '/google-calendar-integration',
          name: 'google-calendar-integration',
          component: () => import('../views/GoogleCalendarIntegrationView.vue'),
        },
        {
          path: '/google-drive-integration',
          name: 'google-drive-integration',
          component: () => import('../views/GoogleDriveIntegrationView.vue'),
        },
        {
          path: '/sqldatabase-integration',
          name: 'sqldatabase-integration',
          component: () => import('../views/SQLDatabaseIntegrationView.vue'),
        },
        {
          path: '/system-commands',
          name: 'system-commands',
          component: () => import('../views/SystemCommandsView.vue'),
        },
        {
          path: '/slack-integration',
          name: 'slack-integration',
          component: () => import('../views/SlackIntegrationView.vue'),
        },
        {
          path: '/telegram-integration',
          name: 'telegram-integration',
          component: () => import('../views/TelegramIntegrationView.vue'),
        },
        {
          path: '/tool-prompts',
          name: 'tool-prompts',
          component: () => import('../views/ToolPromptsView.vue'),
        },
        {
          path: '/calendar/events',
          name: 'calendar-events',
          component: () => import('../views/CalendarEventsView.vue'),
        },
        {
          path: '/functions',
          name: 'functions',
          component: () => import('../views/FunctionsView.vue'),
        },
        {
          path: '/sandbox',
          name: 'sandbox',
          component: () => import('../views/SandboxView.vue'),
        },
        {
          path: '/cron-jobs',
          name: 'cron-jobs',
          component: () => import('../views/CronJobsView.vue'),
        },
      ],
    },
  ],
})

export default router
