import { isMobileBrowser, isWeChatBrowser } from '@/utils/payEnv'

/** iPhone / iPod / iPad (incl. iPadOS desktop UA). */
export function isIOSWebKit(): boolean {
  if (typeof navigator === 'undefined') return false
  const ua = navigator.userAgent
  if (/iPad|iPhone|iPod/.test(ua)) return true
  return navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1
}

/** Track visualViewport for shell height on touch / iOS browsers. */
export function shouldTrackVisualViewport(): boolean {
  if (typeof window === 'undefined') return false
  return isIOSWebKit() || isWeChatBrowser() || isMobileBrowser()
}

export function getVisualViewportHeight(): number {
  return Math.round(window.visualViewport?.height ?? window.innerHeight)
}

export function getVisualViewportWidth(): number {
  return Math.round(window.visualViewport?.width ?? window.innerWidth)
}

export function getVisualViewportOffsetTop(): number {
  return Math.round(window.visualViewport?.offsetTop ?? 0)
}
