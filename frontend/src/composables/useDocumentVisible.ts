import { onMounted, onUnmounted, ref } from 'vue'

/** 页面不可见时暂停动画/轮询，减少后台开销 */
export function useDocumentVisible() {
  const visible = ref(typeof document === 'undefined' ? true : !document.hidden)

  function sync() {
    visible.value = !document.hidden
  }

  onMounted(() => document.addEventListener('visibilitychange', sync))
  onUnmounted(() => document.removeEventListener('visibilitychange', sync))

  return visible
}
