import { createRouter, createWebHistory, createWebHashHistory } from 'vue-router'
import DefaultLayout from '@/components/core/shared/DefaultLayout/DefaultLayout.vue'

const isElectron = typeof window !== 'undefined' && window.location.protocol === 'file:'

const router = createRouter({
  history: isElectron ? createWebHashHistory() : createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'welcome',
      component: () => import('../views/WelcomeView.vue'),
    },
    {
      path: '/app',
      component: DefaultLayout,
      children: [
        {
          path: '',
          redirect: '/app/dashboard',
        },
        {
          path: '/app/dashboard',
          name: 'dashboard',
          component: () => import('../views/DashboardView.vue'),
        },
        {
          path: '/app/my-account',
          name: 'my-account',
          component: () => import('../views/MyAccount.vue'),
        },
        {
          path: '/app/conversation',
          name: 'conversation',
          component: () => import('../views/ConversationView.vue'),
        },
        {
          path: '/app/store-integration',
          name: 'store-integration',
          component: () => import('../views/StoreIntegrationView.vue'),
        },
        {
          path: '/app/whatsapp-integration',
          name: 'whatsapp-integration',
          component: () => import('../views/WhatsappIntegrationView.vue'),
        },
        {
          path: '/app/whatsapp-devices',
          name: 'whatsapp-devices',
          component: () => import('../views/WhatsappDevicesView.vue'),
        },
        {
          path: '/app/meli-integration',
          name: 'meli-integration',
          component: () => import('../views/MercadolibreIntegrationView.vue'),
        },
        {
          path: '/app/google-calendar-integration',
          name: 'google-calendar-integration',
          component: () => import('../views/GoogleCalendarIntegrationView.vue'),
        },
        {
          path: '/app/google-drive-integration',
          name: 'google-drive-integration',
          component: () => import('../views/GoogleDriveIntegrationView.vue'),
        },
        {
          path: '/app/sqldatabase-integration',
          name: 'sqldatabase-integration',
          component: () => import('../views/SQLDatabaseIntegrationView.vue'),
        },
        {
          path: '/app/system-commands',
          name: 'system-commands',
          component: () => import('../views/SystemCommandsView.vue'),
        },
        {
          path: '/app/slack-integration',
          name: 'slack-integration',
          component: () => import('../views/SlackIntegrationView.vue'),
        },
        {
          path: '/app/telegram-integration',
          name: 'telegram-integration',
          component: () => import('../views/TelegramIntegrationView.vue'),
        },
        {
          path: '/app/tool-prompts',
          name: 'tool-prompts',
          component: () => import('../views/ToolPromptsView.vue'),
        },
        {
          path: '/app/calendar/events',
          name: 'calendar-events',
          component: () => import('../views/CalendarEventsView.vue'),
        },
        {
          path: '/app/functions',
          name: 'functions',
          component: () => import('../views/FunctionsView.vue'),
        },
        {
          path: '/app/sandbox',
          name: 'sandbox',
          component: () => import('../views/SandboxView.vue'),
        },
        {
          path: '/app/cron-jobs',
          name: 'cron-jobs',
          component: () => import('../views/CronJobsView.vue'),
        },
      ],
    },
  ],
})

export default router
