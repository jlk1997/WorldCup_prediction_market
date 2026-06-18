<template>
  <Teleport to="body">
    <div v-if="visible" class="second-coach-root">
      <div class="coach-backdrop" @click.self="dismiss" />
      <div class="coach-sheet glass-panel">
        <p class="coach-tag">养成习惯</p>
        <h3>{{ title }}</h3>
        <p class="coach-body">{{ body }}</p>
        <div class="coach-actions">
          <el-button type="primary" @click="goPredict">{{ ctaLabel }}</el-button>
          <el-button text @click="dismiss">稍后再说</el-button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { trackEvent } from '@/utils/analytics'
import type { DailyStatus } from '@/api/commerce'
import { fetchDailyStatus, useDailyStatusRef } from '@/stores/dailyStatusStore'

const props = defineProps<{
  status?: DailyStatus | null
}>()

const router = useRouter()
const storeStatus = useDailyStatusRef()
const visible = ref(false)

const effectiveStatus = computed(() => props.status ?? storeStatus.value)

const SESSION_KEY = 'wc_second_predict_coach_shown'

const title = computed(() => effectiveStatus.value?.activation_nudge?.title || '再来一场')
const body = computed(() => {
  const nudgeBody = effectiveStatus.value?.activation_nudge?.body
  if (nudgeBody) return nudgeBody
  const gap = effectiveStatus.value?.redeem_progress?.gap
  if (gap && gap > 0) {
    return `再猜一场 · 离「${effectiveStatus.value?.redeem_progress?.next_name}」还差 ${gap} 分`
  }
  return '第二猜是养成习惯的第一步 · 免费机会别浪费'
})
const ctaLabel = computed(() => effectiveStatus.value?.activation_nudge?.cta_label || '再猜一场')
const targetPath = computed(
  () =>
    effectiveStatus.value?.activation_nudge?.path ||
    (effectiveStatus.value?.next_predictable_match?.match_id
      ? `/predict?highlight=${effectiveStatus.value.next_predictable_match.match_id}`
      : '/predict'),
)

function shouldOpen() {
  if (effectiveStatus.value?.activation_segment !== 'one_and_done') return false
  try {
    return sessionStorage.getItem(SESSION_KEY) !== '1'
  } catch {
    return true
  }
}

function open() {
  if (!shouldOpen()) return
  visible.value = true
  trackEvent('second_predict_coach_show')
}

function markShown() {
  try {
    sessionStorage.setItem(SESSION_KEY, '1')
  } catch {
    /* ignore */
  }
}

function dismiss() {
  visible.value = false
  markShown()
}

function goPredict() {
  markShown()
  visible.value = false
  trackEvent('second_predict_coach_click')
  router.push(targetPath.value)
}

async function onCoachRequest() {
  await fetchDailyStatus(true)
  open()
}

onMounted(() => {
  window.addEventListener('second-predict-coach', onCoachRequest)
  if (effectiveStatus.value?.activation_segment === 'one_and_done') void onCoachRequest()
})

onUnmounted(() => {
  window.removeEventListener('second-predict-coach', onCoachRequest)
})

defineExpose({ open })
</script>

<style scoped>
.second-coach-root {
  position: fixed;
  inset: 0;
  z-index: 5200;
  display: flex;
  align-items: flex-end;
  justify-content: center;
}

.coach-backdrop {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.55);
}

.coach-sheet {
  position: relative;
  width: min(420px, 100%);
  margin: 0 0 max(16px, env(safe-area-inset-bottom));
  padding: 20px 18px 18px;
  border-radius: 16px 16px 12px 12px;
  animation: coachSlideUp 0.32s ease-out;
}

@keyframes coachSlideUp {
  from {
    opacity: 0;
    transform: translateY(24px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.coach-tag {
  font-size: 0.72rem;
  color: var(--wc-accent-gold, #d4a574);
  margin: 0 0 6px;
}

.coach-sheet h3 {
  margin: 0 0 8px;
  font-size: 1.05rem;
  color: #f5f0e8;
}

.coach-body {
  margin: 0 0 16px;
  font-size: 0.85rem;
  color: var(--wc-text-muted);
  line-height: 1.5;
}

.coach-actions {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
</style>
