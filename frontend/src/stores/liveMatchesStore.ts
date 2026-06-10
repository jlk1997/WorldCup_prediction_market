import { ref } from 'vue'
import { apiClient } from '@/api/client'
import type { LiveMatch } from '@/types/api'

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:10086/ws/live'
const POLL_FAST_MS = 30_000
const POLL_SLOW_MS = 90_000

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
let reconnectDelay = 3000
let started = false

function currentPollMs() {
  return wsConnected.value ? POLL_SLOW_MS : POLL_FAST_MS
}

function resetPollTimer() {
  if (!started || subscriberCount <= 0) return
  if (timer) clearInterval(timer)
  timer = setInterval(() => {
    void fetchMatches({ silent: wsConnected.value })
  }, currentPollMs())
}

async function fetchMatches(opts?: { silent?: boolean; forceLoading?: boolean }) {
  const silent = opts?.silent ?? wsConnected.value
  if (!silent || opts?.forceLoading) loading.value = true
  error.value = null
  try {
    const res = await apiClient.get<LiveMatch[]>('/api/live/matches')
    matches.value = mergeLiveMatches(matches.value, res.data)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
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
    ws.onopen = () => {
      wsConnected.value = true
      reconnectDelay = 3000
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
      reconnectTimer = setTimeout(connectWebSocket, reconnectDelay)
      reconnectDelay = Math.min(reconnectDelay * 1.5, 30_000)
    }
    ws.onerror = () => ws?.close()
  } catch {
    wsConnected.value = false
  }
}

function startLiveMatches() {
  if (started) return
  started = true
  void fetchMatches({ forceLoading: true })
  connectWebSocket()
  timer = setInterval(() => {
    void fetchMatches({ silent: wsConnected.value })
  }, currentPollMs())
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
