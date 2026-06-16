import { ref } from 'vue'

const OPT_IN_KEY = 'wc_browser_notify_opt_in'
const PROMPTED_KEY = 'wc_browser_notify_prompted'

export function canUseBrowserNotify() {
  return typeof window !== 'undefined' && 'Notification' in window
}

export function browserNotifyOptIn(): boolean {
  try {
    return localStorage.getItem(OPT_IN_KEY) === '1'
  } catch {
    return false
  }
}

export function markBrowserNotifyOptIn() {
  try {
    localStorage.setItem(OPT_IN_KEY, '1')
  } catch {
    /* ignore */
  }
}

export function wasNotifyPromptShown() {
  try {
    return localStorage.getItem(PROMPTED_KEY) === '1'
  } catch {
    return false
  }
}

export function markNotifyPromptShown() {
  try {
    localStorage.setItem(PROMPTED_KEY, '1')
  } catch {
    /* ignore */
  }
}

const permission = ref(
  typeof Notification !== 'undefined' ? Notification.permission : ('denied' as NotificationPermission),
)

export function showNotification(title: string, body: string, path?: string) {
  if (!canUseBrowserNotify() || Notification.permission !== 'granted') return
  try {
    const n = new Notification(title, {
      body,
      icon: '/favicon.ico',
      tag: 'wc2026-notify',
    })
    if (path) {
      n.onclick = () => {
        window.focus()
        window.location.href = path
      }
    }
  } catch {
    /* ignore */
  }
}

export async function maybePromptForNotify(reason: string) {
  if (!canUseBrowserNotify()) return
  if (browserNotifyOptIn() || wasNotifyPromptShown()) return
  if (Notification.permission !== 'default') return
  markNotifyPromptShown()
  try {
    const result = await Notification.requestPermission()
    permission.value = result
    if (result === 'granted') {
      markBrowserNotifyOptIn()
      showNotification('提醒已开启', reason, '/predict')
    }
  } catch {
    /* ignore */
  }
}

export function useBrowserNotify() {
  async function requestPermission(): Promise<boolean> {
    if (!canUseBrowserNotify()) return false
    if (Notification.permission === 'granted') {
      permission.value = 'granted'
      markBrowserNotifyOptIn()
      return true
    }
    if (Notification.permission === 'denied') {
      permission.value = 'denied'
      return false
    }
    try {
      const result = await Notification.requestPermission()
      permission.value = result
      if (result === 'granted') markBrowserNotifyOptIn()
      return result === 'granted'
    } catch {
      return false
    }
  }

  return {
    permission,
    requestPermission,
    showNotification,
    maybePromptForNotify,
  }
}

export function notifyIfHidden(title: string, body: string, path?: string) {
  if (typeof document === 'undefined' || !document.hidden) return
  if (!canUseBrowserNotify() || Notification.permission !== 'granted') return
  try {
    const n = new Notification(title, { body, icon: '/favicon.ico', tag: 'wc2026-notify' })
    if (path) {
      n.onclick = () => {
        window.focus()
        window.location.href = path
      }
    }
  } catch {
    /* ignore */
  }
}
