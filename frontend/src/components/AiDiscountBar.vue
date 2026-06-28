<template>
  <div v-if="visible" class="ai-discount-bar glass-inner">
    <span class="icon">✨</span>
    <span class="text">
      持相关球队卡 AI 分析省 <strong>{{ discountPct }}%</strong>
      <span v-if="liveCredits"> · 分析包剩余 live {{ liveCredits }} 次</span>
    </span>
    <button type="button" class="link" @click="$router.push('/shop')">购分析包</button>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { apiClient } from '@/api/client'
import { authState } from '@/stores/authStore'

const props = withDefaults(
  defineProps<{ discountPct?: number }>(),
  { discountPct: 30 },
)

const liveCredits = ref(0)

const visible = computed(() => !!authState.user)

onMounted(async () => {
  if (!authState.user) return
  try {
    const res = await apiClient.get<{ data: { ai_pack_live_credits?: number } }>(
      '/api/agent/billing-status',
    )
    liveCredits.value = res.data.data?.ai_pack_live_credits ?? 0
  } catch {
    /* ignore */
  }
})
</script>

<style scoped>
.ai-discount-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  margin: 8px 0;
  font-size: 0.78rem;
  color: var(--wc-text-secondary);
}
.text strong {
  color: #a371f7;
}
.link {
  margin-left: auto;
  border: none;
  background: transparent;
  color: var(--wc-accent-gold);
  cursor: pointer;
  font-size: 0.75rem;
}
</style>
