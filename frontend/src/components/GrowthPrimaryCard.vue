<template>
  <div v-if="visible" class="growth-primary glass-panel" :class="`variant-${variant}`">
    <div class="growth-main">
      <span class="growth-tag">{{ tagLabel }}</span>
      <strong class="growth-title">{{ title }}</strong>
      <p class="growth-body">{{ body }}</p>
      <p v-if="matchLabel" class="growth-match">{{ matchLabel }}</p>
      <p v-if="redeemHint" class="growth-redeem">{{ redeemHint }}</p>
    </div>
    <div class="growth-actions">
      <el-button type="primary" size="default" class="growth-cta" @click="goPrimary">
        {{ ctaLabel }}
      </el-button>
      <button v-if="canDismiss" type="button" class="growth-dismiss" @click="dismiss">稍后</button>
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
const cardNudge = computed(() => props.status?.card_nudge)
const duelSegment = computed(() => props.status?.duel_segment)
const primaryPillar = computed(() => props.status?.primary_pillar)
const nextMatch = computed(() => props.status?.next_predictable_match)

const preferCardNudge = computed(() => {
  if (!cardNudge.value) return false
  if (primaryPillar.value === 'cards') return true
  if ((props.status?.card_owned_count ?? 0) > 0 && duelSegment.value === 'never_dueled') return true
  return false
})

const variant = computed(() => {
  if (preferCardNudge.value) return 'cards'
  if (segment.value === 'one_and_done') return 'comeback'
  return 'activation'
})

const tagLabel = computed(() => {
  if (preferCardNudge.value) return '卡牌中心'
  if (segment.value === 'profile_only') return '还差一步'
  if (segment.value === 'never_predicted') return '首猜有礼'
  if (segment.value === 'one_and_done') return '养成习惯'
  return '推荐'
})

const title = computed(() => {
  if (preferCardNudge.value) return cardNudge.value!.title
  return nudge.value?.title || props.status?.next_action?.label || '完成竞猜'
})
const body = computed(() => {
  if (preferCardNudge.value) return cardNudge.value!.body
  return nudge.value?.body || '免费 · 约 30 秒 · 猜中得积分'
})
const ctaLabel = computed(() => {
  if (preferCardNudge.value) {
    return duelSegment.value === 'never_dueled' ? '快速匹配' : '去卡牌中心'
  }
  return nudge.value?.cta_label || '去竞猜'
})
const matchLabel = computed(() => nextMatch.value?.label || null)

const redeemHint = computed(() => {
  if (segment.value !== 'one_and_done') return null
  const rp = props.status?.redeem_progress
  if (!rp || rp.gap <= 0) return null
  return `离「${rp.next_name}」还差 ${rp.gap} 分`
})

const targetPath = computed(() => {
  if (preferCardNudge.value) return cardNudge.value!.path
  return (
    nudge.value?.path ||
    props.status?.next_action?.path ||
    (nextMatch.value?.match_id ? `/predict?highlight=${nextMatch.value.match_id}` : '/predict')
  )
})

const shouldShow = computed(() => {
  if (!authState.accessToken) return false
  if (preferCardNudge.value) return true
  const seg = segment.value
  return seg === 'never_predicted' || seg === 'profile_only' || seg === 'one_and_done'
})

const canDismiss = computed(
  () => segment.value === 'never_predicted' || segment.value === 'profile_only',
)

const visible = computed(() => shouldShow.value && !dismissed.value)

function isDismissedRecently() {
  if (!canDismiss.value) return false
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
  trackEvent('growth_primary_dismiss', { segment: segment.value || '' })
}

function goPrimary() {
  trackEvent('growth_primary_click', { segment: segment.value || '' })
  const path = targetPath.value
  const full = path.startsWith('/') ? path : '/predict'
  if (router.currentRoute.value.path === '/predict') {
    if (full !== router.currentRoute.value.fullPath) {
      void router.push(full).then(() => {
        window.dispatchEvent(new CustomEvent('predict-scroll-highlight'))
      })
    } else {
      window.dispatchEvent(new CustomEvent('predict-scroll-highlight'))
    }
    return
  }
  router.push(full)
}

watch(
  () => visible.value,
  (show) => {
    if (show) trackEvent('growth_primary_show', { segment: segment.value || '' })
  },
)

watch(() => props.status?.activation_segment, syncDismiss)
onMounted(syncDismiss)

</script>

<style scoped>
.growth-primary {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 16px 18px;
  margin-top: 10px;
  border-radius: 14px;
  animation: growthEnter 0.35s ease-out;
}

@keyframes growthEnter {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.variant-activation {
  border: 1px solid rgba(212, 165, 116, 0.5);
  background: linear-gradient(135deg, rgba(212, 165, 116, 0.14), rgba(212, 165, 116, 0.04));
}

.variant-comeback {
  border: 1px solid rgba(103, 194, 58, 0.45);
  background: linear-gradient(135deg, rgba(103, 194, 58, 0.12), rgba(103, 194, 58, 0.03));
}

.growth-tag {
  display: inline-block;
  font-size: 0.7rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  color: var(--wc-accent-gold, #d4a574);
  margin-bottom: 4px;
}

.variant-comeback .growth-tag {
  color: #67c23a;
}

.growth-title {
  display: block;
  font-size: 1.02rem;
  color: #f5f0e8;
  margin: 0 0 6px;
  line-height: 1.35;
}

.growth-body {
  margin: 0;
  font-size: 0.82rem;
  color: var(--wc-text-muted);
  line-height: 1.45;
}

.growth-match {
  margin: 8px 0 0;
  font-size: 0.88rem;
  font-weight: 600;
  color: #f5f0e8;
}

.growth-redeem {
  margin: 6px 0 0;
  font-size: 0.78rem;
  color: #67c23a;
}

.growth-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.growth-cta {
  min-width: 120px;
  font-weight: 600;
}

.growth-dismiss {
  border: none;
  background: transparent;
  color: var(--wc-text-muted);
  font-size: 0.78rem;
  cursor: pointer;
  padding: 6px 8px;
}

.growth-dismiss:hover {
  color: #f5f0e8;
}

@media (min-width: 520px) {
  .growth-primary {
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
  }

  .growth-actions {
    flex-shrink: 0;
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
