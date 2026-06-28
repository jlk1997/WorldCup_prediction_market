import { reactive } from 'vue'
import {
  getNotifications,
  getNotificationBadge,
  markNotificationsRead,
  getPendingPredictionsCount,
  type UserNotification,
} from '@/api/notifications'
import { enrichNotificationPayload } from '@/utils/predictRevealPayload'
import { isLoggedIn } from '@/stores/authStore'
import { registerLogoutCleanup } from '@/stores/logoutRegistry'
import { predictRevealConfig } from '@/stores/predictRevealConfigStore'
import { notifyIfHidden } from '@/composables/useBrowserNotify'

const POLL_FAST_MS = 30_000
const POLL_SLOW_MS = 120_000

export const referralNotify = reactive({ unread: 0, latest: null as UserNotification | null })
export const predictNotify = reactive({ unread: 0, latest: null as UserNotification | null })
export const collectibleNotify = reactive({ unread: 0, latest: null as UserNotification | null })
export const growthNotify = reactive({ unread: 0, latest: null as UserNotification | null })

const GROWTH_CATEGORIES = ['matchday_repurchase', 'matchday_ai', 'fantasy_weekly'] as const

export const predictReveal = reactive({
  visible: false,
  queue: [] as UserNotification[],
  index: 0,
})

const shownPredictIds = new Set<number>()

let pollTimer: ReturnType<typeof setInterval> | null = null
let pollIntervalMs = POLL_SLOW_MS
let started = false

function normalizePredictNote(note: UserNotification): UserNotification {
  return {
    ...note,
    payload: enrichNotificationPayload(note),
  }
}

function mergePredictQueue(notes: UserNotification[]) {
  const maxItems = predictRevealConfig.carousel?.max_items ?? 10
  for (const raw of notes) {
    const note = normalizePredictNote(raw)
    if (shownPredictIds.has(note.id)) continue
    if (predictReveal.queue.some((q) => q.id === note.id)) continue
    shownPredictIds.add(note.id)
    predictReveal.queue.push(note)
  }
  if (predictReveal.queue.length > maxItems) {
    predictReveal.queue = predictReveal.queue.slice(-maxItems)
  }
  if (predictReveal.queue.length > 0) {
    predictReveal.visible = true
  }
}

async function pollAll() {
  if (!isLoggedIn.value) {
    referralNotify.unread = 0
    referralNotify.latest = null
    predictNotify.unread = 0
    predictNotify.latest = null
    collectibleNotify.unread = 0
    collectibleNotify.latest = null
    growthNotify.unread = 0
    growthNotify.latest = null
    return
  }
  try {
    const badge = await getNotificationBadge()
    const counts = badge.counts
    const refCount = counts.referral_reward ?? 0
    const predCount = counts.predict_settled ?? 0
    const dropC = counts.collectible_drop ?? 0
    const setC = counts.collectible_set ?? 0
    const chainC = counts.collectible_chain ?? 0
    referralNotify.unread = refCount
    predictNotify.unread = predCount
    collectibleNotify.unread = dropC + setC + chainC
    growthNotify.unread = GROWTH_CATEGORIES.reduce((n, c) => n + (counts[c] ?? 0), 0)

    const fetches: Promise<void>[] = []
    if (refCount > 0) {
      fetches.push(
        getNotifications({ unread_only: true, category: 'referral_reward', limit: 1 }).then((rows) => {
          referralNotify.latest = rows[0] ?? null
        }),
      )
    } else {
      referralNotify.latest = null
    }
    if (predCount > 0) {
      const limit = Math.min(predCount, predictRevealConfig.carousel?.max_items ?? 10)
      fetches.push(
        getNotifications({ unread_only: true, category: 'predict_settled', limit }).then((rows) => {
          const notes = rows.map(normalizePredictNote)
          predictNotify.latest = notes[0] ?? null
          if (notes.length) {
            mergePredictQueue(notes)
            const latest = notes[0]
            const payload = latest?.payload as Record<string, unknown> | undefined
            const won = payload?.status === 'won'
            notifyIfHidden(
              won ? '猜中了！' : '竞猜已开奖',
              won ? '点击查看结算详情' : '来看看本场结果',
              '/me?focus=predictions',
            )
          }
        }),
      )
    } else if (!predictReveal.visible) {
      predictNotify.latest = null
    }
    if (collectibleNotify.unread > 0) {
      fetches.push(
        Promise.all([
          getNotifications({ unread_only: true, category: 'collectible_drop', limit: 1 }),
          getNotifications({ unread_only: true, category: 'collectible_set', limit: 1 }),
          getNotifications({ unread_only: true, category: 'collectible_chain', limit: 1 }),
        ]).then((groups) => {
          const latest = groups.flat().sort((a, b) => b.id - a.id)[0] ?? null
          collectibleNotify.latest = latest
          if (latest) {
            notifyIfHidden(latest.title, latest.body, '/collection')
          }
        }),
      )
    } else {
      collectibleNotify.latest = null
    }
    if (growthNotify.unread > 0) {
      fetches.push(
        Promise.all(
          GROWTH_CATEGORIES.map((cat) =>
            getNotifications({ unread_only: true, category: cat, limit: 1 }),
          ),
        ).then((groups) => {
          const latest = groups.flat().sort((a, b) => b.id - a.id)[0] ?? null
          growthNotify.latest = latest
          if (latest) {
            const payload = latest.payload as Record<string, unknown> | undefined
            notifyIfHidden(latest.title, latest.body, String(payload?.path || '/'))
          }
        }),
      )
    } else {
      growthNotify.latest = null
    }
    await Promise.all(fetches)

    const nextInterval = await resolvePollInterval()
    if (nextInterval !== pollIntervalMs) {
      pollIntervalMs = nextInterval
      if (pollTimer) {
        clearInterval(pollTimer)
        pollTimer = setInterval(() => void pollAll(), pollIntervalMs)
      }
    }
  } catch {
    referralNotify.unread = 0
    predictNotify.unread = 0
    collectibleNotify.unread = 0
    growthNotify.unread = 0
  }
}

async function resolvePollInterval(): Promise<number> {
  try {
    const pending = await getPendingPredictionsCount()
    return pending > 0 ? POLL_FAST_MS : POLL_SLOW_MS
  } catch {
    return predictNotify.unread > 0 ? POLL_FAST_MS : POLL_SLOW_MS
  }
}

function onVisibility() {
  if (document.hidden) {
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
    return
  }
  void pollAll()
  if (started && !pollTimer) {
    pollTimer = setInterval(() => void pollAll(), pollIntervalMs)
  }
}

export function startHeaderNotificationPoll() {
  if (started || typeof document === 'undefined') return
  if (!isLoggedIn.value) return
  started = true
  void pollAll()
  pollTimer = setInterval(() => void pollAll(), pollIntervalMs)
  document.addEventListener('visibilitychange', onVisibility)
}

export function stopHeaderNotificationPoll() {
  resetHeaderNotifications()
  started = false
  document.removeEventListener('visibilitychange', onVisibility)
}

export async function markReferralRead() {
  if (!referralNotify.latest) return
  await markNotificationsRead([referralNotify.latest.id])
  referralNotify.unread = Math.max(0, referralNotify.unread - 1)
  referralNotify.latest = null
  await pollAll()
}

export async function markCollectibleRead() {
  if (!collectibleNotify.latest) return
  await markNotificationsRead([collectibleNotify.latest.id])
  collectibleNotify.unread = Math.max(0, collectibleNotify.unread - 1)
  collectibleNotify.latest = null
  await pollAll()
}

export async function markGrowthRead() {
  if (!growthNotify.latest) return
  await markNotificationsRead([growthNotify.latest.id])
  growthNotify.unread = Math.max(0, growthNotify.unread - 1)
  growthNotify.latest = null
  await pollAll()
}

export function currentPredictNotification(): UserNotification | null {
  return predictReveal.queue[predictReveal.index] ?? null
}

function advanceOrClose() {
  const current = predictReveal.queue[predictReveal.index]
  if (current) {
    predictReveal.queue = predictReveal.queue.filter((n) => n.id !== current.id)
  }
  if (predictReveal.queue.length === 0) {
    predictReveal.visible = false
    predictReveal.index = 0
    predictNotify.latest = null
    return
  }
  if (predictReveal.index >= predictReveal.queue.length) {
    predictReveal.index = predictReveal.queue.length - 1
  }
}

export async function markPredictRead(onAfter?: () => void | Promise<void>) {
  const note = currentPredictNotification() ?? predictNotify.latest
  if (!note) return
  await markNotificationsRead([note.id])
  predictNotify.unread = Math.max(0, predictNotify.unread - 1)
  advanceOrClose()
  await onAfter?.()
  await pollAll()
}

export async function markAllPredictRead(onAfter?: () => void | Promise<void>) {
  const ids = predictReveal.queue.map((n) => n.id)
  if (!ids.length) return
  await markNotificationsRead(ids)
  predictNotify.unread = Math.max(0, predictNotify.unread - ids.length)
  predictReveal.queue = []
  predictReveal.index = 0
  predictReveal.visible = false
  predictNotify.latest = null
  await onAfter?.()
  await pollAll()
}

export function goPredictReveal(delta: number) {
  if (predictReveal.queue.length <= 1) return
  const next = predictReveal.index + delta
  if (next < 0 || next >= predictReveal.queue.length) return
  predictReveal.index = next
}

export function resetHeaderNotifications() {
  referralNotify.unread = 0
  referralNotify.latest = null
  predictNotify.unread = 0
  predictNotify.latest = null
  collectibleNotify.unread = 0
  collectibleNotify.latest = null
  growthNotify.unread = 0
  growthNotify.latest = null
  predictReveal.visible = false
  predictReveal.queue = []
  predictReveal.index = 0
  shownPredictIds.clear()
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

/** Called from WebSocket when predict_settled arrives. */
export function handlePredictSettledPush(payload: Record<string, unknown>) {
  if (!isLoggedIn.value) return
  const status = String(payload.status || '')
  const team1 = String(payload.team1 || '?')
  const team2 = String(payload.team2 || '?')
  const synthetic: UserNotification = {
    id: Number(payload.prediction_id || Date.now()),
    category: 'predict_settled',
    title: status === 'won' ? '竞猜猜中了' : status === 'void' ? '竞猜流局' : '竞猜未中',
    body: `${team1} vs ${team2} 比分 ${payload.final_score || '—'}`,
    payload,
  }
  synthetic.payload = enrichNotificationPayload(synthetic)
  predictNotify.unread += 1
  predictNotify.latest = synthetic
  mergePredictQueue([synthetic])
}

registerLogoutCleanup(resetHeaderNotifications)
