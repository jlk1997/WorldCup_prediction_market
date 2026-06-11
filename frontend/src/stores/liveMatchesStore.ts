import { ref } from 'vue'
import { apiClient } from '@/api/client'
import { isRateLimited } from '@/api/rateLimitGuard'
import type { LiveMatch } from '@/types/api'

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:10086/ws/live'
const POLL_FAST_MS = 45_000
const POLL_SLOW_MS = 120_000
const POLL_BACKOFF_MS = 120_000
const WS_RECONNECT_MIN_MS = 5_000
const WS_RECONNECT_MAX_MS = 60_000

export function mergeLiveMatches(prev: LiveMatch[], incoming: LiveMatch[]): LiveMatch[] {
  if (!incoming.length) return prev
  if (!prev.length) return incoming
  const map = new Map<number, LiveMatch>()
  for (const m of prev) {
    if (m.id != null) map.set(m.id, m)
  }
  for (const m of incoming) {
    if (m.id == null) continue
    const old = map.get(m.id)
    map.set(m.id, old ? { ...old, ...m } : m)
  }
  return [...map.values()]
}

const matches = ref<LiveMatch[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const wsConnected = ref(false)

let subscriberCount = 0
let timer: ReturnType<typeof setInterval> | null = null
let ws: WebSocket | null = null
let reconnectTimer: ReturnType<typeof setTimeout> | null = null
let reconnectDelay = WS_RECONNECT_MIN_MS
let wsFailStreak = 0
let started = false
let pollBackoffUntil = 0
let tabVisible = typeof document !== 'undefined' ? !document.hidden : true

function currentPollMs() {
  if (Date.now() < pollBackoffUntil || isRateLimited()) return POLL_BACKOFF_MS
  return wsConnected.value ? POLL_SLOW_MS : POLL_FAST_MS
}

function onVisibilityChange() {
  tabVisible = !document.hidden
  if (tabVisible && started && subscriberCount > 0) {
    void fetchMatches({ silent: true })
  }
  resetPollTimer()
}

function bindVisibility() {
  if (typeof document === 'undefined') return
  document.addEventListener('visibilitychange', onVisibilityChange)
}

function unbindVisibility() {
  if (typeof document === 'undefined') return
  document.removeEventListener('visibilitychange', onVisibilityChange)
}

function resetPollTimer() {
  if (!started || subscriberCount <= 0) return
  if (timer) clearInterval(timer)
  timer = setInterval(() => {
    void fetchMatches({ silent: wsConnected.value })
  }, currentPollMs())
}

async function fetchMatches(opts?: { silent?: boolean; forceLoading?: boolean }) {
  if (!tabVisible && !opts?.forceLoading) return
  if (isRateLimited()) return
  const silent = opts?.silent ?? wsConnected.value
  if (!silent || opts?.forceLoading) loading.value = true
  error.value = null
  try {
    const res = await apiClient.get<LiveMatch[]>('/api/live/matches')
    matches.value = mergeLiveMatches(matches.value, res.data)
    pollBackoffUntil = 0
    resetPollTimer()
  } catch (e) {
    const msg = e instanceof Error ? e.message : '加载失败'
    error.value = msg
    if (/过于频繁|too many requests|rate limit/i.test(msg)) {
      pollBackoffUntil = Date.now() + POLL_BACKOFF_MS
      resetPollTimer()
    }
  } finally {
    if (!silent || opts?.forceLoading) loading.value = false
  }
}

function closeWebSocket(code = 1000, reason = 'client stop') {
  if (!ws) return
  const socket = ws
  ws = null
  wsConnected.value = false
  try {
    if (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING) {
      socket.close(code, reason)
    }
  } catch {
    /* ignore */
  }
}

function connectWebSocket() {
  closeWebSocket(1000, 'reconnect')
  try {
    ws = new WebSocket(WS_URL)
    const openedAt = Date.now()
    ws.onopen = () => {
      wsConnected.value = true
      wsFailStreak = 0
      reconnectDelay = WS_RECONNECT_MIN_MS
      resetPollTimer()
    }
    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data)
      if (msg.type === 'live_update' && Array.isArray(msg.matches)) {
        matches.value = mergeLiveMatches(matches.value, msg.matches)
      }
    }
    ws.onclose = () => {
      wsConnected.value = false
      ws = null
      resetPollTimer()
      if (!started || subscriberCount <= 0) return
      const livedMs = Date.now() - openedAt
      if (livedMs < 5000) {
        wsFailStreak += 1
        reconnectDelay = Math.min(
          WS_RECONNECT_MAX_MS,
          WS_RECONNECT_MIN_MS * 2 ** Math.min(wsFailStreak, 4),
        )
      } else {
        wsFailStreak = 0
        reconnectDelay = WS_RECONNECT_MIN_MS
      }
      reconnectTimer = setTimeout(connectWebSocket, reconnectDelay)
    }
    ws.onerror = () => ws?.close()
  } catch {
    wsConnected.value = false
  }
}

function startLiveMatches() {
  if (started) return
  started = true
  bindVisibility()
  void fetchMatches({ forceLoading: true })
  connectWebSocket()
  resetPollTimer()
}

function stopLiveMatches() {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
  if (reconnectTimer) {
    clearTimeout(reconnectTimer)
    reconnectTimer = null
  }
  closeWebSocket(1000, 'page leave')
  unbindVisibility()
  started = false
}

export function subscribeLiveMatches() {
  subscriberCount += 1
  if (subscriberCount === 1) startLiveMatches()
  return () => {
    subscriberCount = Math.max(0, subscriberCount - 1)
    if (subscriberCount === 0) stopLiveMatches()
  }
}

export function useLiveMatchesStore() {
  return {
    matches,
    loading,
    error,
    wsConnected,
    refresh: () => fetchMatches({ forceLoading: true }),
    getMatchById: (id: number) => matches.value.find((m) => m.id === id) ?? null,
  }
}
