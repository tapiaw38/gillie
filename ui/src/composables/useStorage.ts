const isStorageAvailable = () => typeof window !== 'undefined' && typeof window.localStorage !== 'undefined'

export const useStorage = () => {
  const getItem = (key: string): string | null => {
    if (!isStorageAvailable()) {
      return null
    }

    try {
      return window.localStorage.getItem(key)
    } catch {
      return null
    }
  }

  const setItem = (key: string, value: string): boolean => {
    if (!isStorageAvailable()) {
      return false
    }

    try {
      window.localStorage.setItem(key, value)
      return true
    } catch {
      return false
    }
  }

  const removeItem = (key: string): boolean => {
    if (!isStorageAvailable()) {
      return false
    }

    try {
      window.localStorage.removeItem(key)
      return true
    } catch {
      return false
    }
  }

  return {
    getItem,
    setItem,
    removeItem,
  }
}
