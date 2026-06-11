import { reactive } from 'vue'
import {
  getNotifications,
  getUnreadNotificationCount,
  markNotificationsRead,
  type UserNotification,
} from '@/api/notifications'
import { isLoggedIn } from '@/stores/authStore'

const POLL_MS = 120_000

export const referralNotify = reactive({ unread: 0, latest: null as UserNotification | null })
export const predictNotify = reactive({ unread: 0, latest: null as UserNotification | null })

let pollTimer: ReturnType<typeof setInterval> | null = null
let started = false

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
          predictNotify.latest = rows[0] ?? null
        }),
      )
    } else {
      predictNotify.latest = null
    }
    await Promise.all(fetches)
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
    pollTimer = setInterval(() => void pollAll(), POLL_MS)
  }
}

export function startHeaderNotificationPoll() {
  if (started || typeof document === 'undefined') return
  started = true
  void pollAll()
  pollTimer = setInterval(() => void pollAll(), POLL_MS)
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
  if (!predictNotify.latest) return
  await markNotificationsRead([predictNotify.latest.id])
  predictNotify.unread = Math.max(0, predictNotify.unread - 1)
  predictNotify.latest = null
  await onAfter?.()
  await pollAll()
}
