import { onMounted, onUnmounted, ref, type Ref } from 'vue'

/** 轻量倒计时：每秒刷新，组件卸载自动清理。 */
export function useCountdownTick(intervalMs = 1000) {
  const tick = ref(0)
  let timer: ReturnType<typeof setInterval> | null = null

  onMounted(() => {
    timer = setInterval(() => {
      tick.value += 1
    }, intervalMs)
  })

  onUnmounted(() => {
    if (timer) clearInterval(timer)
  })

  return tick
}

export function formatCountdown(iso?: string | null, _tick?: Ref<number>): string {
  if (!iso) return ''
  const diff = new Date(iso).getTime() - Date.now()
  if (diff <= 0) return '已结束'
  const h = Math.floor(diff / 3600000)
  const m = Math.floor((diff % 3600000) / 60000)
  const s = Math.floor((diff % 60000) / 1000)
  if (h >= 24) return `${Math.floor(h / 24)}天${h % 24}时`
  if (h > 0) return `${h}时${m}分`
  return `${m}分${s}秒`
}

export function formatTimeUntil(iso?: string | null, prefix = '还剩'): string {
  if (!iso) return ''
  const diff = new Date(iso).getTime() - Date.now()
  if (diff <= 0) return '已开始'
  const h = Math.floor(diff / 3600000)
  const m = Math.floor((diff % 3600000) / 60000)
  if (h >= 24) return `${prefix} ${Math.floor(h / 24)}天${h % 24}小时`
  if (h > 0) return `${prefix} ${h}小时${m}分`
  return `${prefix} ${m}分钟`
}
