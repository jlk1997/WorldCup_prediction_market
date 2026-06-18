<template>
  <div v-if="visible" class="activation-recovery-bar glass-inner">
    <div class="bar-text">
      <strong>{{ nudge?.title || '完成首猜' }}</strong>
      <span>{{ nudge?.body || '免费 · 约 30 秒 · 猜中得积分' }}</span>
    </div>
    <div class="bar-actions">
      <el-button type="primary" size="small" @click="goCta">
        {{ nudge?.cta_label || '去竞猜' }}
      </el-button>
      <button type="button" class="dismiss-btn" aria-label="稍后" @click="dismiss">稍后</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import type { DailyStatus } from '@/api/commerce'
import { authState } from '@/stores/authStore'
import { trackEvent } from '@/utils/analytics'

const props = defineProps<{
  status?: DailyStatus | null
}>()

const router = useRouter()
const dismissed = ref(false)

const DISMISS_KEY = 'wc_activation_nudge_dismissed_at'
const DISMISS_MS = 24 * 60 * 60 * 1000

const segment = computed(() => props.status?.activation_segment)
const nudge = computed(() => props.status?.activation_nudge)

const shouldShow = computed(() => {
  if (!authState.accessToken) return false
  const seg = segment.value
  return seg === 'never_predicted' || seg === 'profile_only'
})

const visible = computed(() => shouldShow.value && !dismissed.value && !!nudge.value)

function isDismissedRecently() {
  try {
    const raw = localStorage.getItem(DISMISS_KEY)
    if (!raw) return false
    return Date.now() - Number(raw) < DISMISS_MS
  } catch {
    return false
  }
}

function syncDismiss() {
  dismissed.value = isDismissedRecently()
}

function dismiss() {
  try {
    localStorage.setItem(DISMISS_KEY, String(Date.now()))
  } catch {
    /* ignore */
  }
  dismissed.value = true
}

function goCta() {
  trackEvent('activation_recovery_click', { segment: segment.value || '' })
  const path = nudge.value?.path || props.status?.next_action?.path || '/predict'
  if (path.startsWith('/')) router.push(path)
  else router.push('/predict')
}

watch(
  () => visible.value,
  (show) => {
    if (show) trackEvent('activation_recovery_show', { segment: segment.value || '' })
  },
)

watch(() => props.status?.activation_segment, syncDismiss)
onMounted(syncDismiss)
</script>

<style scoped>
.activation-recovery-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
  margin-top: 10px;
  border-radius: 12px;
  border: 1px solid rgba(212, 165, 116, 0.45);
  background: rgba(212, 165, 116, 0.1);
}

.bar-text {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.bar-text strong {
  font-size: 0.88rem;
  color: #f5f0e8;
}

.bar-text span {
  font-size: 0.75rem;
  color: var(--wc-text-muted);
  line-height: 1.4;
}

.bar-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.dismiss-btn {
  border: none;
  background: transparent;
  color: var(--wc-text-muted);
  font-size: 0.75rem;
  cursor: pointer;
  padding: 4px 6px;
}

.dismiss-btn:hover {
  color: #f5f0e8;
}
</style>
