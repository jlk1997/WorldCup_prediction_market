const STORAGE_KEY = 'wc_device_id'

function randomId(): string {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID().replace(/-/g, '')
  }
  return `d${Date.now().toString(36)}${Math.random().toString(36).slice(2, 12)}`
}

/** Stable anonymous device id for anti-cheat rate limits (v2). */
export function getDeviceId(): string {
  if (typeof localStorage === 'undefined') return randomId()
  let id = localStorage.getItem(STORAGE_KEY)
  if (!id || id.length < 8) {
    id = randomId()
    localStorage.setItem(STORAGE_KEY, id)
  }
  return id
}
