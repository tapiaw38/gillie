export const useOAuthPopup = () => {
  const openOAuthPopup = (url: string, onSuccess: () => void) => {
    const width = 600
    const height = 700
    const left = Math.round(window.screen.width / 2 - width / 2)
    const top = Math.round(window.screen.height / 2 - height / 2)

    const popup = window.open(
      url,
      'oauth-popup',
      `width=${width},height=${height},left=${left},top=${top},scrollbars=yes,resizable=yes`,
    )

    if (!popup) {
      // Popup blocked by browser — fallback to redirect
      window.location.href = url
      return
    }

    const onMessage = (event: MessageEvent) => {
      if (event.data?.type === 'oauth_success') {
        window.removeEventListener('message', onMessage)
        clearInterval(poll)
        onSuccess()
      }
    }

    window.addEventListener('message', onMessage)

    // Fallback: if popup closes without sending postMessage
    const poll = setInterval(() => {
      if (popup.closed) {
        clearInterval(poll)
        window.removeEventListener('message', onMessage)
        onSuccess()
      }
    }, 500)
  }

  return { openOAuthPopup }
}
