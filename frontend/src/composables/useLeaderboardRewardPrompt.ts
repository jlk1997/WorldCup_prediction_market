import { onMounted, onUnmounted, ref, watch, type Ref } from 'vue'
import { useRoute } from 'vue-router'
import { shouldShowLeaderboardRewardPrompt } from '../utils/leaderboardRewardPrompt'
import { isLoggedIn } from '../stores/authStore'
import { isFeatureTourPending } from './useGuideModal'
import {
  GuidePriority,
  isGuideBlocked,
  notifyGuideClosed,
  notifyGuideOpened,
  registerGuide,
  requestGuide,
  unregisterGuide,
} from './useGuideOrchestrator'

/** 进入这些页面时展示「冲榜神秘大礼」弹窗 */
export const REWARD_PROMPT_ROUTES = ['/', '/predict', '/leaderboard'] as const

export type RewardPromptRoute = (typeof REWARD_PROMPT_ROUTES)[number]

const REWARD_GUIDE_ID = 'leaderboard-reward'

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

    if (!isLoggedIn.value) return
    if (!isRewardPromptRoute(route.path)) return
    if (options?.blocked?.value) return
    if (isFeatureTourPending()) return
    if (isGuideBlocked(GuidePriority.LeaderboardReward)) {
      requestGuide(REWARD_GUIDE_ID)
      return
    }
    if (!shouldShowLeaderboardRewardPrompt()) return

    timer = setTimeout(() => {
      if (!isLoggedIn.value) return
      if (!isRewardPromptRoute(route.path)) return
      if (options?.blocked?.value) return
      if (isFeatureTourPending()) return
      if (isGuideBlocked(GuidePriority.LeaderboardReward)) {
        requestGuide(REWARD_GUIDE_ID)
        return
      }
      if (!shouldShowLeaderboardRewardPrompt()) return
      showRewardDialog.value = true
      notifyGuideOpened(REWARD_GUIDE_ID, GuidePriority.LeaderboardReward)
      timer = null
    }, 450)
  }

  function closeRewardDialog() {
    showRewardDialog.value = false
    notifyGuideClosed(REWARD_GUIDE_ID)
  }

  onMounted(() => {
    registerGuide(REWARD_GUIDE_ID, {
      priority: GuidePriority.LeaderboardReward,
      isActive: () => showRewardDialog.value,
      open: () => {
        if (!isLoggedIn.value) return
        if (shouldShowLeaderboardRewardPrompt() && isRewardPromptRoute(route.path)) {
          showRewardDialog.value = true
          notifyGuideOpened(REWARD_GUIDE_ID, GuidePriority.LeaderboardReward)
        }
      },
    })
    tryOpen()
  })

  watch(() => route.path, tryOpen)
  if (options?.blocked) {
    watch(options.blocked, tryOpen)
  }

  watch(showRewardDialog, (open) => {
    if (!open) notifyGuideClosed(REWARD_GUIDE_ID)
  })

  onUnmounted(() => {
    clearTimer()
    unregisterGuide(REWARD_GUIDE_ID)
    notifyGuideClosed(REWARD_GUIDE_ID)
  })

  return { showRewardDialog, closeRewardDialog }
}
