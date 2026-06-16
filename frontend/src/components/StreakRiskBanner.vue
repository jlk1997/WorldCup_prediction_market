<template>
  <div
    v-if="message"
    class="streak-risk-banner glass-panel"
    role="button"
    tabindex="0"
    @click="go"
    @keydown.enter="go"
  >
    🔥 {{ message }}
    <span class="streak-cta">{{ ctaLabel }}</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import type { DailyStatus } from '@/api/commerce'

const props = withDefaults(
  defineProps<{
    status?: DailyStatus | null
    ctaLabel?: string
  }>(),
  { ctaLabel: '再猜一场 →' },
)

const router = useRouter()

const message = computed(() => props.status?.streak_risk?.message ?? '')

function go() {
  const mid = props.status?.streak_risk?.match_id
  router.push(mid ? { path: '/predict', query: { highlight: String(mid) } } : '/predict')
}
</script>

<style scoped>
.streak-risk-banner {
  margin: 0 0 12px;
  padding: 10px 14px;
  border-radius: 12px;
  border: 1px solid rgba(230, 162, 60, 0.45);
  background: rgba(230, 162, 60, 0.1);
  font-size: 0.82rem;
  color: rgba(255, 255, 255, 0.88);
  cursor: pointer;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  transition: border-color 0.2s, background 0.2s;
}

.streak-risk-banner:hover {
  border-color: rgba(230, 162, 60, 0.65);
  background: rgba(230, 162, 60, 0.14);
}

.streak-cta {
  margin-left: auto;
  font-weight: 700;
  color: #e6a23c;
}
</style>
