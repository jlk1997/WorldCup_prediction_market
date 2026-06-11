import type { RouteLocationNormalizedLoaded, Router } from 'vue-router'

export type DailyNextAction = {
  key: string
  path?: string | null
  label?: string
}

const FOCUS_BY_KEY: Record<string, string> = {
  quiz: 'quiz',
  signin: 'signin',
  pending: 'predictions',
}

export function scrollMeFocus(focus: string) {
  const el = document.getElementById(`${focus}-section`)
  if (!el) return
  el.scrollIntoView({ behavior: 'smooth', block: 'center' })
  el.classList.add('focus-flash')
  window.setTimeout(() => el.classList.remove('focus-flash'), 2200)
}

export function navigateDailyAction(
  router: Router,
  route: RouteLocationNormalizedLoaded,
  action: DailyNextAction | null | undefined,
) {
  if (!action) return
  const focus = FOCUS_BY_KEY[action.key]
  if (focus) {
    if (route.path === '/me') {
      if (focus === 'predictions') {
        router.replace({ path: '/me', query: { ...route.query, tab: 'records', focus } })
        return
      }
      const tab = route.query.tab
      if (typeof tab === 'string' && tab !== 'overview') {
        router.replace({ path: '/me', query: { ...route.query, tab: 'overview', focus } })
        return
      }
      scrollMeFocus(focus)
      return
    }
    if (focus === 'predictions') {
      router.push({ path: '/me', query: { tab: 'records', focus } })
      return
    }
    router.push({ path: '/me', query: { tab: 'overview', focus } })
    return
  }
  if (action.path) router.push(action.path)
}
