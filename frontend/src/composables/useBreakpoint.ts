import { computed, onMounted, onUnmounted, ref } from 'vue'

export const BP_MOBILE = 768
export const BP_TABLET = 960

function readBreakpoints() {
  const w = typeof window !== 'undefined' ? window.innerWidth : 1200
  return {
    isMobile: w <= BP_MOBILE,
    isTablet: w > BP_MOBILE && w <= BP_TABLET,
    isDesktop: w > BP_TABLET,
    width: w,
  }
}

const shared = ref(readBreakpoints())
let listenerCount = 0

function onResize() {
  shared.value = readBreakpoints()
}

function attach() {
  if (listenerCount === 0) {
    window.addEventListener('resize', onResize, { passive: true })
  }
  listenerCount += 1
}

function detach() {
  listenerCount -= 1
  if (listenerCount <= 0) {
    listenerCount = 0
    window.removeEventListener('resize', onResize)
  }
}

/** Reactive viewport breakpoints for mobile H5 layout branching. */
export function useBreakpoint() {
  onMounted(attach)
  onUnmounted(detach)

  return {
    isMobile: computed(() => shared.value.isMobile),
    isTablet: computed(() => shared.value.isTablet),
    isDesktop: computed(() => shared.value.isDesktop),
    width: computed(() => shared.value.width),
  }
}

/** Non-component usage (e.g. store init). */
export function getBreakpointSnapshot() {
  return readBreakpoints()
}
