const isClipboardAvailable = () =>
  typeof window !== 'undefined' && typeof window.navigator?.clipboard?.writeText === 'function'

export const useClipboard = () => {
  const copyText = async (text: string): Promise<boolean> => {
    if (!isClipboardAvailable()) {
      return false
    }

    try {
      await window.navigator.clipboard.writeText(text)
      return true
    } catch {
      return false
    }
  }

  return {
    copyText,
  }
}
