import { onMounted, onUnmounted, watch } from 'vue'
import { authState, isLoggedIn } from '@/stores/authStore'
import { handlePredictSettledPush } from '@/stores/headerNotificationsStore'

function wsBaseUrl(): string {
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${proto}//${window.location.host}`
}

export function useUserPredictWs() {
  let ws: WebSocket | null = null
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null

  function disconnect() {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    if (ws) {
      ws.close()
      ws = null
    }
  }

  function connect() {
    disconnect()
    const token = authState.accessToken
    if (!token) return
    try {
      ws = new WebSocket(`${wsBaseUrl()}/ws/user?token=${encodeURIComponent(token)}`)
      ws.onmessage = (ev) => {
        try {
          const data = JSON.parse(ev.data as string)
          if (data?.type === 'predict_settled' && data.payload) {
            handlePredictSettledPush(data.payload as Record<string, unknown>)
          }
        } catch {
          /* ignore */
        }
      }
      ws.onclose = () => {
        ws = null
        if (isLoggedIn.value) {
          reconnectTimer = setTimeout(connect, 8000)
        }
      }
    } catch {
      /* ignore */
    }
  }

  onMounted(() => {
    if (isLoggedIn.value) connect()
    watch(isLoggedIn, (logged) => {
      if (logged) connect()
      else disconnect()
    })
  })

  onUnmounted(disconnect)
}
