import { computed, ref } from 'vue'
import { getDailyStatus, type DailyStatus } from '@/api/commerce'
import { authState } from '@/stores/authStore'
import { registerLogoutCleanup } from '@/stores/logoutRegistry'

const dailyStatus = ref<DailyStatus | null>(null)
let lastFetchAt = 0
let inflight: Promise<DailyStatus | null> | null = null
const CACHE_MS = 15_000

export const activationSegment = computed(() => dailyStatus.value?.activation_segment ?? null)
export const predictCountTotal = computed(() => dailyStatus.value?.predict_count_total ?? 0)
export const nextPredictableMatch = computed(() => dailyStatus.value?.next_predictable_match ?? null)
export const activationNudge = computed(() => dailyStatus.value?.activation_nudge ?? null)
export const collectionPassNudge = computed(() => dailyStatus.value?.collection_pass_nudge ?? null)
export const needsFirstPredict = computed(
  () =>
    activationSegment.value === 'never_predicted' || activationSegment.value === 'profile_only',
)
export const needsSecondPredict = computed(() => activationSegment.value === 'one_and_done')

export function useDailyStatusRef() {
  return dailyStatus
}

export async function fetchDailyStatus(force = false): Promise<DailyStatus | null> {
  if (!authState.accessToken) {
    dailyStatus.value = null
    lastFetchAt = 0
    return null
  }
  const now = Date.now()
  if (!force && dailyStatus.value && now - lastFetchAt < CACHE_MS) {
    return dailyStatus.value
  }
  if (inflight) return inflight

  inflight = (async () => {
    try {
      const data = await getDailyStatus()
      dailyStatus.value = data
      lastFetchAt = Date.now()
      return data
    } catch {
      return dailyStatus.value
    } finally {
      inflight = null
    }
  })()

  return inflight
}

export function clearDailyStatus() {
  dailyStatus.value = null
  lastFetchAt = 0
  inflight = null
}

registerLogoutCleanup(clearDailyStatus)

export function setDailyStatus(data: DailyStatus | null) {
  dailyStatus.value = data
  if (data) lastFetchAt = Date.now()
}
