/** Page scroll root is el-main.main-content (see App.vue). */

export function getScrollRoot(from?: Element | null): HTMLElement {
  if (from) {
    const root = from.closest('.main-content') as HTMLElement | null
    if (root) return root
  }
  const main = document.querySelector('.el-main.main-content') as HTMLElement | null
  if (main) return main
  return (document.scrollingElement ?? document.documentElement) as HTMLElement
}

export async function scrollElementIntoRootView(el: HTMLElement) {
  await new Promise<void>((resolve) => {
    requestAnimationFrame(() => requestAnimationFrame(() => resolve()))
  })
  const scrollRoot = getScrollRoot(el)
  if (scrollRoot && scrollRoot !== document.documentElement) {
    const rootRect = scrollRoot.getBoundingClientRect()
    const cardRect = el.getBoundingClientRect()
    const targetTop =
      scrollRoot.scrollTop +
      cardRect.top -
      rootRect.top -
      Math.max(0, (rootRect.height - cardRect.height) / 2)
    scrollRoot.scrollTo({ top: Math.max(0, targetTop), behavior: 'smooth' })
    return
  }
  el.scrollIntoView({ behavior: 'smooth', block: 'center' })
}

export function waitForElement(
  selector: string,
  maxMs = 2000,
): Promise<HTMLElement | null> {
  const start = Date.now()
  return new Promise((resolve) => {
    function tick() {
      const el = document.querySelector(selector) as HTMLElement | null
      if (el && el.getBoundingClientRect().width > 0) {
        resolve(el)
        return
      }
      if (Date.now() - start >= maxMs) {
        resolve(null)
        return
      }
      requestAnimationFrame(tick)
    }
    tick()
  })
}

/** Clear stale Element Plus body scroll-lock after dialogs close. */
export function cleanupElementScrollLock() {
  if (typeof document === 'undefined') return
  document.body.classList.remove('el-popup-parent--hidden')
  document.body.style.removeProperty('overflow')
  document.body.style.removeProperty('padding-right')
}
