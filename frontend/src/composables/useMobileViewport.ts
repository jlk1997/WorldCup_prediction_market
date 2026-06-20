import { shouldTrackVisualViewport } from '@/utils/visualViewport'

/** Compensate iOS / WeChat WebView toolbar resize via CSS variables on the shell. */
export function initMobileViewport(): () => void {
  if (typeof window === 'undefined') return () => {}
  if (!shouldTrackVisualViewport()) return () => {}

  function apply() {
    const vv = window.visualViewport
    const h = vv?.height ?? window.innerHeight
    const offsetTop = vv?.offsetTop ?? 0
    document.documentElement.style.setProperty('--app-height', `${Math.round(h)}px`)
    document.documentElement.style.setProperty('--app-offset-top', `${Math.round(offsetTop)}px`)
    document.documentElement.style.setProperty(
      '--visual-viewport-height',
      `${Math.round(h)}px`,
    )
  }

  apply()
  window.visualViewport?.addEventListener('resize', apply)
  window.visualViewport?.addEventListener('scroll', apply)
  window.addEventListener('orientationchange', apply)
  window.addEventListener('resize', apply)

  return () => {
    window.visualViewport?.removeEventListener('resize', apply)
    window.visualViewport?.removeEventListener('scroll', apply)
    window.removeEventListener('orientationchange', apply)
    window.removeEventListener('resize', apply)
  }
}
