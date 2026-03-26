import { ref, onMounted, onUnmounted } from 'vue'
import axios from 'axios'

const BASE_URL = import.meta.env.VITE_ASSISTANT_BASE_URL || 'http://localhost:8000'
const INTERVAL_MS = 10000

export function useBackendStatus() {
  const isActive = ref(false)
  const cause = ref('')
  let timer: ReturnType<typeof setInterval>

  const check = async () => {
    try {
      await axios.get(`${BASE_URL}/`, { timeout: 3000 })
      isActive.value = true
      cause.value = ''
    } catch (err: any) {
      isActive.value = false
      if (err.code === 'ERR_NETWORK' || err.code === 'ECONNREFUSED') {
        cause.value = 'Backend no disponible'
      } else if (err.code === 'ECONNABORTED') {
        cause.value = 'Tiempo de espera agotado'
      } else if (err.response?.status >= 500) {
        cause.value = `Error del servidor (${err.response.status})`
      } else {
        cause.value = 'Sin conexión'
      }
    }
  }

  onMounted(() => {
    check()
    timer = setInterval(check, INTERVAL_MS)
  })

  onUnmounted(() => clearInterval(timer))

  return { isActive, cause }
}
