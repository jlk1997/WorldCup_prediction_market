const cleanups: Array<() => void> = []

export function registerLogoutCleanup(fn: () => void) {
  cleanups.push(fn)
}

export function runLogoutCleanups() {
  for (const fn of cleanups) {
    try {
      fn()
    } catch {
      /* ignore cleanup errors */
    }
  }
}
