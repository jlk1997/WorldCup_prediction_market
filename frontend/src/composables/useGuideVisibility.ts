import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { authState, isLoggedIn } from '@/stores/authStore'

/** Routes where onboarding / profile prompts must not appear. */
export const AUTH_FLOW_PREFIXES = ['/login', '/onboarding'] as const

export function isAuthFlowPath(path: string) {
  return AUTH_FLOW_PREFIXES.some((p) => path === p || path.startsWith(`${p}/`))
}

export function useGuideVisibility() {
  const route = useRoute()

  const isAuthFlow = computed(() => isAuthFlowPath(route.path))

  const profileIncomplete = computed(
    () => isLoggedIn.value && !!authState.user && !authState.user.profile_completed,
  )

  /** Top banner — one place to nudge profile completion on normal pages. */
  const showProfileBanner = computed(() => {
    if (isAuthFlow.value) return false
    if (!profileIncomplete.value) return false
    if (localStorage.getItem('wc_skip_profile_banner')) return false
    if (localStorage.getItem('wc_skip_profile_hint')) return false
    return true
  })

  /** Header chip — only when banner is hidden but profile still incomplete. */
  const showProfileHeaderChip = computed(() => profileIncomplete.value && !showProfileBanner.value && !isAuthFlow.value)

  /** 5-step product tour — after profile is done, first visit to dashboard only. */
  const showFeatureTour = computed(() => {
    if (route.path !== '/') return false
    if (!isLoggedIn.value || !authState.user?.profile_completed) return false
    if (localStorage.getItem('wc2026_onboarded')) return false
    return true
  })

  return {
    isAuthFlow,
    profileIncomplete,
    showProfileBanner,
    showProfileHeaderChip,
    showFeatureTour,
  }
}
