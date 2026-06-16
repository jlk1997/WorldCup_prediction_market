import { onUnmounted, ref, watch, type Ref } from 'vue'
import { useRoute } from 'vue-router'
import { shouldShowLeaderboardRewardPrompt } from '../utils/leaderboardRewardPrompt'
import { isFeatureTourPending } from './useGuideModal'

/** 进入这些页面时展示「冲榜神秘大礼」弹窗 */
export const REWARD_PROMPT_ROUTES = ['/', '/predict', '/leaderboard'] as const

export type RewardPromptRoute = (typeof REWARD_PROMPT_ROUTES)[number]

export function isRewardPromptRoute(path: string): path is RewardPromptRoute {
  return (REWARD_PROMPT_ROUTES as readonly string[]).includes(path)
}

export function useLeaderboardRewardPrompt(options?: {
  blocked?: Ref<boolean>
}) {
  const route = useRoute()
  const showRewardDialog = ref(false)
  let timer: ReturnType<typeof setTimeout> | null = null

  function clearTimer() {
    if (timer) {
      clearTimeout(timer)
      timer = null
    }
  }

  function tryOpen() {
    clearTimer()
    showRewardDialog.value = false

    if (!isRewardPromptRoute(route.path)) return
    if (options?.blocked?.value) return
    if (isFeatureTourPending()) return
    if (!shouldShowLeaderboardRewardPrompt()) return

    timer = setTimeout(() => {
      if (!isRewardPromptRoute(route.path)) return
      if (options?.blocked?.value) return
      if (isFeatureTourPending()) return
      if (!shouldShowLeaderboardRewardPrompt()) return
      showRewardDialog.value = true
      timer = null
    }, 450)
  }

  watch(() => route.path, tryOpen, { immediate: true })
  if (options?.blocked) {
    watch(options.blocked, tryOpen)
  }

  onUnmounted(clearTimer)

  return { showRewardDialog }
}
