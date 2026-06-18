<template>
  <div v-if="visible" class="match-day-share-bar glass-inner">
    <div class="bar-text">
      <strong>比赛日 · 邀球友一起猜</strong>
      <span>{{ matchLabel }} · 复制带深链的邀请</span>
    </div>
    <el-button type="primary" size="small" :loading="copying" @click="copyLink">复制链接</el-button>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { DailyStatus } from '@/api/commerce'
import { getReferralMe } from '@/api/referral'
import { copyToClipboard } from '@/utils/copyToClipboard'
import { trackEvent } from '@/utils/analytics'

const props = defineProps<{
  status?: DailyStatus | null
}>()

const copying = ref(false)

const visible = computed(() => !!props.status?.match_day)

const matchId = computed(
  () =>
    props.status?.next_predictable_match?.match_id ||
    props.status?.streak_risk?.match_id ||
    props.status?.next_pending_match?.match_id ||
    null,
)

const matchLabel = computed(
  () =>
    props.status?.next_predictable_match?.label ||
    props.status?.streak_risk?.label ||
    props.status?.next_pending_match?.label ||
    '今日焦点战',
)

async function copyLink() {
  copying.value = true
  try {
    const me = await getReferralMe().catch(() => null)
    const origin = typeof window !== 'undefined' ? window.location.origin : 'https://loveaibaby.cn'
    const ref = me?.invite_code ? `ref=${encodeURIComponent(me.invite_code)}` : ''
    const highlight = matchId.value ? `highlight=${matchId.value}` : ''
    const qs = [ref, highlight].filter(Boolean).join('&')
    const url = `${origin}/predict${qs ? `?${qs}` : ''}`
    const ok = await copyToClipboard(`${matchLabel.value} 开猜了 · 一起来猜\n${url}`)
    if (ok) {
      ElMessage.success('比赛日邀请链接已复制')
      trackEvent('match_day_share_copy', { match_id: matchId.value ?? 0 })
    } else {
      ElMessage.warning('复制失败，请手动复制')
    }
  } finally {
    copying.value = false
  }
}
</script>

<style scoped>
.match-day-share-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 14px;
  border-radius: 12px;
  border: 1px solid rgba(88, 166, 255, 0.35);
  background: rgba(88, 166, 255, 0.08);
}

.bar-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.bar-text strong {
  font-size: 0.85rem;
  color: #f5f0e8;
}

.bar-text span {
  font-size: 0.72rem;
  color: var(--wc-text-muted);
}
</style>
