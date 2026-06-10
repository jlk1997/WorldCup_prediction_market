import { onMounted, onUnmounted, ref } from 'vue'

/** Poll only when tab is visible; pause in background to save requests. */
export function useVisibilityPoll(fn: () => void | Promise<void>, intervalMs = 60000) {
  const active = ref(typeof document !== 'undefined' ? !document.hidden : true)
  let timer: ReturnType<typeof setInterval> | null = null

  function start() {
    stop()
    if (!active.value) return
    timer = setInterval(() => {
      void fn()
    }, intervalMs)
  }

  function stop() {
    if (timer) {
      clearInterval(timer)
      timer = null
    }
  }

  function onVisibility() {
    active.value = !document.hidden
    if (active.value) {
      void fn()
      start()
    } else {
      stop()
    }
  }

  onMounted(() => {
    void fn()
    start()
    document.addEventListener('visibilitychange', onVisibility)
  })

  onUnmounted(() => {
    stop()
    document.removeEventListener('visibilitychange', onVisibility)
  })

  return { active, refresh: fn }
}
