import { useStorage } from '@/composables/useStorage'

const API_KEY_STORAGE_KEY = 'gillie_api_key'

export const useApiKey = () => {
  const { getItem, setItem } = useStorage()

  const getApiKey = (): string => getItem(API_KEY_STORAGE_KEY) ?? ''

  const setApiKey = (key: string): void => {
    setItem(API_KEY_STORAGE_KEY, key)
  }

  return { getApiKey, setApiKey }
}
