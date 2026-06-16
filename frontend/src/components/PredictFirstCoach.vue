<template>
  <Teleport to="body">
    <div v-if="visible" class="predict-coach-root">
      <div class="coach-backdrop" @click.self="dismiss" />
      <div v-if="spotlight" class="coach-spotlight" :style="spotlightStyle" />
      <div v-if="tooltipStyle" class="coach-tooltip glass-panel" :style="tooltipStyle">
        <p class="coach-step">{{ step + 1 }} / {{ steps.length }}</p>
        <h3>{{ steps[step].title }}</h3>
        <p>{{ steps[step].desc }}</p>
        <div class="coach-actions">
          <el-button text @click="dismiss">跳过</el-button>
          <el-button type="primary" @click="next">{{ step >= steps.length - 1 ? '知道了' : '下一步' }}</el-button>
        </div>
      </div>
      <div v-else class="coach-fallback glass-panel">
        <p class="coach-step">{{ step + 1 }} / {{ steps.length }}</p>
        <h3>{{ steps[step].title }}</h3>
        <p>{{ steps[step].desc }}</p>
        <p class="coach-hint">请向下滚动到第一场可竞猜的比赛卡片</p>
        <div class="coach-actions">
          <el-button text @click="dismiss">跳过</el-button>
          <el-button type="primary" @click="next">{{ step >= steps.length - 1 ? '知道了' : '下一步' }}</el-button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { trackEvent } from '@/utils/analytics'

const STORAGE_KEY = 'wc_first_predict_coach'

const steps = [
  { coach: 'pick', title: '先选胜 / 平 / 负', desc: '在第一场还没猜的比赛上，点你要的结果。' },
  { coach: 'free', title: '勾选免费竞猜', desc: '每天 1 次免费机会，猜中得积分冲榜。' },
  { coach: 'submit', title: '点提交', desc: '确认后等待赛后自动开奖，猜中会有弹窗通知。' },
]

const visible = ref(false)
const step = ref(0)
const rect = ref<DOMRect | null>(null)

const spotlight = computed(() => !!rect.value && rect.value.width > 0)

const spotlightStyle = computed(() => {
  const r = rect.value
  if (!r) return {}
  const pad = 8
  return {
    top: `${Math.max(0, r.top - pad)}px`,
    left: `${Math.max(0, r.left - pad)}px`,
    width: `${r.width + pad * 2}px`,
    height: `${r.height + pad * 2}px`,
  }
})

const tooltipStyle = computed(() => {
  const r = rect.value
  if (!r) return null
  const w = Math.min(360, window.innerWidth - 32)
  let top = r.bottom + 14
  let left = Math.min(Math.max(16, r.left), window.innerWidth - w - 16)
  if (top + 180 > window.innerHeight) {
    top = Math.max(16, r.top - 190)
  }
  return { top: `${top}px`, left: `${left}px`, width: `${w}px` }
})

function findTarget(): HTMLElement | null {
  const key = steps[step.value]?.coach
  if (!key) return null
  return document.querySelector(`[data-coach="${key}"]`) as HTMLElement | null
}

function updateSpotlight() {
  const el = findTarget()
  if (!el) {
    rect.value = null
    return
  }
  el.scrollIntoView({ block: 'center', behavior: 'smooth' })
  window.setTimeout(() => {
    rect.value = el.getBoundingClientRect()
  }, 280)
}

function dismiss() {
  visible.value = false
  try {
    localStorage.setItem(STORAGE_KEY, '1')
  } catch {
    /* ignore */
  }
  trackEvent('predict_coach_dismiss', { step: step.value })
}

function next() {
  if (step.value >= steps.length - 1) {
    trackEvent('predict_coach_complete')
    dismiss()
    return
  }
  step.value += 1
}

watch(step, () => {
  void nextTick().then(updateSpotlight)
})

function onResize() {
  if (visible.value) updateSpotlight()
}

onMounted(() => {
  try {
    if (localStorage.getItem(STORAGE_KEY)) return
  } catch {
    /* ignore */
  }
  visible.value = true
  trackEvent('predict_coach_show')
  void nextTick().then(() => {
    window.setTimeout(updateSpotlight, 400)
  })
  window.addEventListener('resize', onResize)
  window.addEventListener('scroll', onResize, true)
})

onUnmounted(() => {
  window.removeEventListener('resize', onResize)
  window.removeEventListener('scroll', onResize, true)
})
</script>

<style scoped>
.predict-coach-root {
  position: fixed;
  inset: 0;
  z-index: 9000;
  pointer-events: none;
}

.coach-backdrop {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.55);
  pointer-events: auto;
}

.coach-spotlight {
  position: fixed;
  border-radius: 14px;
  box-shadow:
    0 0 0 9999px rgba(0, 0, 0, 0.55),
    0 0 0 3px rgba(212, 165, 116, 0.85),
    0 0 28px rgba(212, 165, 116, 0.45);
  pointer-events: none;
  z-index: 1;
  transition: top 0.25s ease, left 0.25s ease, width 0.25s ease, height 0.25s ease;
}

.coach-tooltip,
.coach-fallback {
  position: fixed;
  z-index: 2;
  padding: 18px 16px;
  border-radius: 14px;
  pointer-events: auto;
}

.coach-fallback {
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  max-width: 380px;
  width: calc(100% - 32px);
}

.coach-step {
  margin: 0 0 6px;
  font-size: 12px;
  color: var(--wc-accent-gold, #d4a574);
  font-weight: 600;
}

.coach-tooltip h3,
.coach-fallback h3 {
  margin: 0 0 8px;
  font-size: 1.05rem;
  color: var(--wc-text-primary);
}

.coach-tooltip p,
.coach-fallback p {
  margin: 0 0 14px;
  font-size: 0.88rem;
  line-height: 1.55;
  color: var(--wc-text-muted);
}

.coach-hint {
  font-size: 0.8rem !important;
  color: var(--wc-accent-gold, #d4a574) !important;
}

.coach-actions {
  display: flex;
  justify-content: center;
  gap: 10px;
}
</style>
