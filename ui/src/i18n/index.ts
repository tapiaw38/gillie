import { createI18n } from 'vue-i18n'
import { useStorage } from '@/composables/useStorage'
import en from './locales/en.json'
import es from './locales/es.json'

const { getItem } = useStorage()
const savedLang = getItem('gillie-lang') || 'en'

export const i18n = createI18n({
  legacy: false,
  locale: savedLang,
  fallbackLocale: 'en',
  messages: { en, es },
})
