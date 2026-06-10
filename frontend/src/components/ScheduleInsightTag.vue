<template>
  <span v-if="insight?.has_data" class="insight-tag" @click.stop="emit('click')">
    AI {{ insight.predicted_score }}
    <template v-if="insight.confidence != null"> · {{ Math.round(insight.confidence * 100) }}%</template>
  </span>
  <span v-else class="insight-tag muted" @click.stop="emit('click')">AI 未分析</span>
</template>

<script setup lang="ts">
import type { AgentInsight } from '@/types/api'

defineProps<{ insight?: AgentInsight | null }>()
const emit = defineEmits<{ click: [] }>()
</script>

<style scoped>
.insight-tag {
  display: inline-block;
  margin-top: 6px;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.68rem;
  background: rgba(210, 167, 109, 0.15);
  color: #D2A76D;
  border: 1px solid rgba(210, 167, 109, 0.35);
  cursor: pointer;
}
.insight-tag.muted {
  color: #6e7681;
  border-color: #30363d;
  background: rgba(0, 0, 0, 0.2);
}
.insight-tag:hover {
  background: rgba(210, 167, 109, 0.25);
}
</style>
