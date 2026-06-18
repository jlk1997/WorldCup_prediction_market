<template>
  <div v-if="visible" class="comeback-banner glass-inner">
    <div class="bar-text">
      <strong>{{ nudge?.title || '再来一场' }}</strong>
      <span>{{ nudge?.body || '第二猜是养成习惯的第一步' }}</span>
      <span v-if="redeemGap > 0" class="redeem-hint">
        离「{{ redeemName }}」还差 {{ redeemGap }} 分
      </span>
    </div>
    <el-button type="primary" size="small" @click="goCta">
      {{ nudge?.cta_label || '再猜一场' }}
    </el-button>
  </div>
</template>

<script setup lang="ts">
import { computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import type { DailyStatus } from '@/api/commerce'
import { authState } from '@/stores/authStore'
import { trackEvent } from '@/utils/analytics'

const props = defineProps<{
  status?: DailyStatus | null
}>()

const router = useRouter()

const nudge = computed(() => props.status?.activation_nudge)
const redeemGap = computed(() => props.status?.redeem_progress?.gap ?? 0)
const redeemName = computed(() => props.status?.redeem_progress?.next_name ?? '兑换好礼')

const visible = computed(
  () =>
    !!authState.accessToken &&
    props.status?.activation_segment === 'one_and_done' &&
    !!props.status?.next_predictable_match,
)

watch(
  () => visible.value,
  (show) => {
    if (show) trackEvent('comeback_banner_show')
  },
)

function goCta() {
  trackEvent('comeback_banner_click')
  const path =
    nudge.value?.path ||
    props.status?.next_action?.path ||
    (props.status?.next_predictable_match?.match_id
      ? `/predict?highlight=${props.status.next_predictable_match.match_id}`
      : '/predict')
  router.push(path.startsWith('/') ? path : '/predict')
}
</script>

<style scoped>
.comeback-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
  margin-top: 10px;
  border-radius: 12px;
  border: 1px solid rgba(103, 194, 58, 0.35);
  background: rgba(103, 194, 58, 0.08);
}

.bar-text {
  display: flex;
  flex-direction: column;
  gap: 3px;
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

.redeem-hint {
  color: #67c23a !important;
  font-weight: 500;
}
</style>
