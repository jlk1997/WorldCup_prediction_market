import { ref } from 'vue'
import { getTodayHome, type TodayHomeData } from '@/api/commerce'
import { authState } from '@/stores/authStore'
import { registerLogoutCleanup } from '@/stores/logoutRegistry'
import { setDailyStatus } from '@/stores/dailyStatusStore'

const todayHome = ref<TodayHomeData | null>(null)
let lastFetchAt = 0
let inflight: Promise<TodayHomeData | null> | null = null
const CACHE_MS = 20_000

export function useTodayHomeRef() {
  return todayHome
}

export async function fetchTodayHome(force = false): Promise<TodayHomeData | null> {
  if (!authState.accessToken) {
    todayHome.value = null
    lastFetchAt = 0
    return null
  }
  const now = Date.now()
  if (!force && todayHome.value && now - lastFetchAt < CACHE_MS) {
    return todayHome.value
  }
  if (inflight) return inflight

  inflight = (async () => {
    try {
      const data = await getTodayHome()
      todayHome.value = data
      lastFetchAt = Date.now()
      if (data.daily) {
        setDailyStatus(data.daily)
      }
      return data
    } catch {
      return todayHome.value
    } finally {
      inflight = null
    }
  })()

  return inflight
}

export function clearTodayHome() {
  todayHome.value = null
  lastFetchAt = 0
  inflight = null
}

registerLogoutCleanup(clearTodayHome)
