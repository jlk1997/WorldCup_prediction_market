<template>
  <div v-if="insight?.has_data" class="live-insight-chip">
    <span class="tag">AI</span>
    <span class="pick">{{ insight.pick_label || insight.predicted_score }}</span>
  </div>
</template>

<script setup lang="ts">
import type { AgentInsight } from '@/types/api'

defineProps<{ insight: AgentInsight | null | undefined }>()
</script>

<style scoped>
.live-insight-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-top: 6px;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(163, 113, 247, 0.15);
  font-size: 0.68rem;
}
.tag {
  color: #a371f7;
  font-weight: 600;
}
.pick {
  color: var(--wc-text-secondary);
}
</style>
