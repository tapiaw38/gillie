const API_KEY_STORAGE_KEY = 'gillie_api_key'

export const useApiKey = () => {
  const getApiKey = (): string => localStorage.getItem(API_KEY_STORAGE_KEY) ?? ''

  const setApiKey = (key: string): void => {
    localStorage.setItem(API_KEY_STORAGE_KEY, key)
  }

  return { getApiKey, setApiKey }
}
