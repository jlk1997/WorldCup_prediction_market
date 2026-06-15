import { reactive } from 'vue'
import {
  getNotifications,
  getUnreadNotificationCount,
  markNotificationsRead,
  getPendingPredictionsCount,
  type UserNotification,
} from '@/api/notifications'
import { isLoggedIn } from '@/stores/authStore'

const POLL_FAST_MS = 30_000
const POLL_SLOW_MS = 120_000

export const referralNotify = reactive({ unread: 0, latest: null as UserNotification | null })
export const predictNotify = reactive({ unread: 0, latest: null as UserNotification | null })

export const predictReveal = reactive({
  visible: false,
  notification: null as UserNotification | null,
})

const shownPredictIds = new Set<number>()

let pollTimer: ReturnType<typeof setInterval> | null = null
let pollIntervalMs = POLL_SLOW_MS
let started = false

function openPredictReveal(note: UserNotification) {
  if (shownPredictIds.has(note.id)) return
  shownPredictIds.add(note.id)
  predictReveal.notification = note
  predictReveal.visible = true
}

async function resolvePollInterval(): Promise<number> {
  try {
    const pending = await getPendingPredictionsCount()
    return pending > 0 ? POLL_FAST_MS : POLL_SLOW_MS
  } catch {
    return predictNotify.unread > 0 ? POLL_FAST_MS : POLL_SLOW_MS
  }
}

async function pollAll() {
  if (!isLoggedIn.value) {
    referralNotify.unread = 0
    referralNotify.latest = null
    predictNotify.unread = 0
    predictNotify.latest = null
    return
  }
  try {
    const [refCount, predCount] = await Promise.all([
      getUnreadNotificationCount('referral_reward'),
      getUnreadNotificationCount('predict_settled'),
    ])
    referralNotify.unread = refCount
    predictNotify.unread = predCount

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
      fetches.push(
        getNotifications({ unread_only: true, category: 'predict_settled', limit: 1 }).then((rows) => {
          const note = rows[0] ?? null
          predictNotify.latest = note
          if (note) openPredictReveal(note)
        }),
      )
    } else {
      predictNotify.latest = null
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
  started = true
  void pollAll()
  pollTimer = setInterval(() => void pollAll(), pollIntervalMs)
  document.addEventListener('visibilitychange', onVisibility)
}

export async function markReferralRead() {
  if (!referralNotify.latest) return
  await markNotificationsRead([referralNotify.latest.id])
  referralNotify.unread = Math.max(0, referralNotify.unread - 1)
  referralNotify.latest = null
  await pollAll()
}

export async function markPredictRead(onAfter?: () => void | Promise<void>) {
  const note = predictReveal.notification ?? predictNotify.latest
  if (!note) return
  await markNotificationsRead([note.id])
  predictNotify.unread = Math.max(0, predictNotify.unread - 1)
  predictNotify.latest = null
  predictReveal.visible = false
  predictReveal.notification = null
  await onAfter?.()
  await pollAll()
}

/** Called from WebSocket when predict_settled arrives. */
export function handlePredictSettledPush(payload: Record<string, unknown>) {
  const status = String(payload.status || '')
  const synthetic: UserNotification = {
    id: Number(payload.prediction_id || Date.now()),
    category: 'predict_settled',
    title: status === 'won' ? '竞猜猜中了' : status === 'void' ? '竞猜流局' : '竞猜未中',
    body: `${payload.team1 || '?'} vs ${payload.team2 || '?'}`,
    payload,
  }
  predictNotify.unread += 1
  predictNotify.latest = synthetic
  openPredictReveal(synthetic)
}
