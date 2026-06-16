import { getDailyStatus } from '@/api/commerce'
import { fetchRecommendations, profileState } from '@/stores/profileStore'
import { isLoggedIn } from '@/stores/authStore'
import {
  browserNotifyOptIn,
  canUseBrowserNotify,
  maybePromptForNotify,
  showNotification,
  wasNotifyPromptShown,
} from '@/composables/useBrowserNotify'

const REMINDER_KEY = 'wc_match_reminder_sent'
const PENDING_NOTIFY_KEY = 'wc_pending_result_notify'
const TWO_HOURS_MS = 2 * 60 * 60 * 1000

const scheduledTimers = new Map<number, number>()

function reminderStorageKey(matchId: number) {
  return `${REMINDER_KEY}_${matchId}`
}

function alreadyReminded(matchId: number): boolean {
  try {
    return !!sessionStorage.getItem(reminderStorageKey(matchId))
  } catch {
    return false
  }
}

function markReminded(matchId: number) {
  try {
    sessionStorage.setItem(reminderStorageKey(matchId), String(Date.now()))
  } catch {
    /* ignore */
  }
}

function pendingNotifyKey(matchId: number) {
  return `${PENDING_NOTIFY_KEY}_${matchId}`
}

function alreadyPendingNotified(matchId: number): boolean {
  try {
    const raw = sessionStorage.getItem(pendingNotifyKey(matchId))
    if (!raw) return false
    return Date.now() - Number(raw) < 3600_000
  } catch {
    return false
  }
}

function markPendingNotified(matchId: number) {
  try {
    sessionStorage.setItem(pendingNotifyKey(matchId), String(Date.now()))
  } catch {
    /* ignore */
  }
}

function scheduleReminder(matchId: number, label: string, hoursUntil: number) {
  if (alreadyReminded(matchId) || scheduledTimers.has(matchId)) return
  const ms = hoursUntil * 3600 * 1000
  if (ms <= 0 || ms > TWO_HOURS_MS * 1.5) return

  const fireIn = Math.max(5000, ms - TWO_HOURS_MS)
  const timerId = window.setTimeout(() => {
    scheduledTimers.delete(matchId)
    if (alreadyReminded(matchId)) return
    markReminded(matchId)
    showNotification(
      '主队比赛快开了',
      `${label} 约 2 小时后开赛 · 去竞猜或看 Live`,
      `/predict?highlight=${matchId}`,
    )
  }, fireIn)
  scheduledTimers.set(matchId, timerId)
}

function fireImmediateIfSoon(matchId: number, label: string, hoursUntil: number | null | undefined) {
  if (hoursUntil == null || hoursUntil > 2 || hoursUntil < 0) return
  if (alreadyReminded(matchId)) return
  markReminded(matchId)
  showNotification(
    '比赛日提醒',
    `${label} 约 ${Math.max(0.5, hoursUntil).toFixed(1)} 小时后开赛`,
    `/predict?highlight=${matchId}`,
  )
}

export async function syncMatchKickoffReminders() {
  if (!isLoggedIn.value || !canUseBrowserNotify()) return

  if (!browserNotifyOptIn() && !wasNotifyPromptShown()) {
    await maybePromptForNotify('开启后可收到主队开赛前 2 小时提醒')
    if (!browserNotifyOptIn() && Notification.permission === 'default') return
  }

  if (Notification.permission !== 'granted') return

  try {
    if (!profileState.recommendations) {
      await fetchRecommendations()
    }
    const main = profileState.recommendations?.next_main_match
    if (main?.id && main.hours_until != null) {
      fireImmediateIfSoon(main.id, `${main.team1} vs ${main.team2}`, main.hours_until)
      scheduleReminder(main.id, `${main.team1} vs ${main.team2}`, main.hours_until)
    }

    const daily = await getDailyStatus().catch(() => null)
    const pending = daily?.next_pending_match
    if (
      pending?.match_id &&
      pending.hours_until != null &&
      pending.hours_until <= 3 &&
      !alreadyPendingNotified(pending.match_id)
    ) {
      markPendingNotified(pending.match_id)
      showNotification(
        '待开奖提醒',
        `「${pending.label}」即将出结果`,
        '/me?focus=predictions',
      )
    }
  } catch {
    /* optional */
  }
}
