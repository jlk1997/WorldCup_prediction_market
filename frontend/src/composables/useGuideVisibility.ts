import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { authState, isLoggedIn } from '@/stores/authStore'

/** Routes where onboarding / profile prompts must not appear. */
export const AUTH_FLOW_PREFIXES = ['/login', '/onboarding'] as const

/** Pages visited during the 6-step product tour (home appears twice: steps 1 & 4). */
export const FEATURE_TOUR_ROUTES = ['/', '/live', '/agent', '/predict', '/invite'] as const

export function isFeatureTourRoute(path: string) {
  return FEATURE_TOUR_ROUTES.some((p) => path === p || path.startsWith(`${p}/`))
}

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

  /** 6-step product tour — follows user across tour pages until finished/skipped. */
  const showFeatureTour = computed(() => {
    if (!isLoggedIn.value || !authState.user?.profile_completed) return false
    if (localStorage.getItem('wc2026_onboarded')) return false
    return isFeatureTourRoute(route.path)
  })

  return {
    isAuthFlow,
    profileIncomplete,
    showProfileBanner,
    showProfileHeaderChip,
    showFeatureTour,
  }
}
