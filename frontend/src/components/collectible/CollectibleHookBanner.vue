<template>
  <div v-if="summary && showBanner" class="collectible-hook glass-panel">
    <div class="hook-main">
      <span class="hook-icon">🃏</span>
      <div>
        <p class="hook-title">{{ title }}</p>
        <p class="hook-sub">{{ subtitle }}</p>
      </div>
    </div>
    <el-button size="small" type="primary" plain @click="$router.push('/collection')">
      收藏册
    </el-button>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { getCollectibleSummary, type CollectibleSummary } from '@/api/collectible'
import { authState } from '@/stores/authStore'

const props = withDefaults(
  defineProps<{
    signinStreak?: number
    forceShow?: boolean
  }>(),
  { signinStreak: 0, forceShow: false },
)

const summary = ref<CollectibleSummary | null>(null)

const showBanner = computed(() => {
  if (!authState.user) return false
  if (props.forceShow) return true
  if (!summary.value) return false
  return summary.value.owned_count === 0 || !!summary.value.next_signin_milestone
})

const title = computed(() => {
  const s = summary.value
  if (!s) return '球星收藏册'
  if (s.owned_count === 0) return '猜中 · 签到 · 比赛日获得球星卡'
  if (s.next_signin_milestone) return s.next_signin_milestone.label
  return `已收集 ${s.owned_count} 张 · 完成度 ${s.completion_pct}%`
})

const subtitle = computed(() => {
  const s = summary.value
  if (!s) return ''
  if (s.owned_count === 0) return '虚拟数字藏品，无金钱价值，仅供收藏炫耀'
  const ms = s.next_signin_milestone
  if (ms) return `当前连签 ${s.signin_streak} 天 · 里程碑奖励等你拿`
  return '继续竞猜收集更多球星卡'
})

onMounted(async () => {
  if (!authState.user) return
  try {
    summary.value = await getCollectibleSummary()
  } catch {
    summary.value = null
  }
})
</script>

<style scoped>
.collectible-hook {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
  margin-bottom: 14px;
  border-radius: 12px;
  border: 1px solid rgba(212, 165, 116, 0.25);
}
.hook-main {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  min-width: 0;
}
.hook-icon {
  font-size: 1.4rem;
  line-height: 1;
}
.hook-title {
  margin: 0 0 4px;
  font-size: 0.88rem;
  color: var(--wc-gold, #d4a574);
}
.hook-sub {
  margin: 0;
  font-size: 0.72rem;
  color: var(--wc-text-muted);
  line-height: 1.35;
}
</style>
