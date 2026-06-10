/**
 * Cross-tab guard: only one AI analysis at a time per browser profile.
 * Uses localStorage + heartbeat so stale locks expire after ~2 min without updates.
 */

const LOCK_KEY = 'wc_ai_analyze_lock'
const LOCK_TTL_MS = 120_000
const HEARTBEAT_MS = 5_000

let heartbeatTimer: ReturnType<typeof setInterval> | null = null

function readLock(): { ts: number; tab: string } | null {
  try {
    const raw = localStorage.getItem(LOCK_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as { ts?: number; tab?: string }
    if (!parsed.ts || !parsed.tab) return null
    if (Date.now() - parsed.ts > LOCK_TTL_MS) {
      localStorage.removeItem(LOCK_KEY)
      return null
    }
    return { ts: parsed.ts, tab: parsed.tab }
  } catch {
    return null
  }
}

const tabId = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`

export function isAnalyzeLockedByOtherTab(): boolean {
  const lock = readLock()
  return lock !== null && lock.tab !== tabId
}

export function tryAcquireAnalyzeLock(): boolean {
  const lock = readLock()
  if (lock && lock.tab !== tabId) return false
  localStorage.setItem(LOCK_KEY, JSON.stringify({ ts: Date.now(), tab: tabId }))
  return true
}

function touchLock() {
  localStorage.setItem(LOCK_KEY, JSON.stringify({ ts: Date.now(), tab: tabId }))
}

export function startAnalyzeHeartbeat() {
  stopAnalyzeHeartbeat()
  touchLock()
  heartbeatTimer = setInterval(touchLock, HEARTBEAT_MS)
}

export function stopAnalyzeHeartbeat() {
  if (heartbeatTimer) {
    clearInterval(heartbeatTimer)
    heartbeatTimer = null
  }
}

export function releaseAnalyzeLock() {
  stopAnalyzeHeartbeat()
  const lock = readLock()
  if (lock?.tab === tabId) {
    localStorage.removeItem(LOCK_KEY)
  }
}
