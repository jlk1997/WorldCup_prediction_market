<template>
  <div class="focus-insight glass-panel" :class="{ compact }" v-loading="loading">
    <div class="insight-head">
      <span class="label">AI 快览</span>
      <el-tag v-if="insight?.has_data" size="small" type="info">{{ modeLabel }}</el-tag>
    </div>

    <template v-if="insight?.has_data">
      <p class="summary">{{ insight.summary || '暂无摘要' }}</p>
      <div class="stats-row">
        <span>预测 <strong>{{ insight.predicted_score }}</strong></span>
        <span v-if="insight.confidence != null">置信 <strong>{{ Math.round(insight.confidence * 100) }}%</strong></span>
      </div>
      <div v-if="insight.win_probability" class="prob-text">
        胜率 {{ team1Short }} {{ pct(insight.win_probability.team1) }}
        · 平 {{ pct(insight.win_probability.draw) }}
        · {{ team2Short }} {{ pct(insight.win_probability.team2) }}
      </div>
      <div class="actions">
        <el-button size="small" type="primary" @click="openFull">查看完整报告</el-button>
        <el-button size="small" plain @click="refreshAnalysis">重新分析</el-button>
      </div>
    </template>

    <template v-else>
      <div class="empty-row">
        <p class="empty-tip">还没有 AI 分析</p>
        <el-button type="primary" size="small" @click="startAnalysis">立即分析</el-button>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { apiClient } from '@/api/client'
import type { AgentInsight } from '@/types/api'
import { useAgentNavigate, type AgentMode } from '@/composables/useAgentNavigate'

const props = withDefaults(
  defineProps<{
    team1: string
    team2: string
    mode: AgentMode
    compact?: boolean
  }>(),
  { compact: false },
)

const { goAgent } = useAgentNavigate()
const loading = ref(false)
const insight = ref<AgentInsight | null>(null)

const team1Short = computed(() => props.team1.slice(0, 2))
const team2Short = computed(() => props.team2.slice(0, 2))

const modeLabel = computed(() => {
  const map: Record<string, string> = { pre_match: '赛前', live: '赛中', post_match: '赛后' }
  return map[props.mode] || props.mode
})

function pct(v: number) {
  return `${Math.round(v * 100)}%`
}

async function fetchInsight() {
  if (!props.team1 || !props.team2) return
  loading.value = true
  try {
    const res = await apiClient.get<{ data: AgentInsight }>('/api/agent/insight', {
      params: { team1: props.team1, team2: props.team2, mode: props.mode },
    })
    insight.value = res.data.data
  } catch {
    insight.value = null
  } finally {
    loading.value = false
  }
}

function startAnalysis() {
  goAgent(props.team1, props.team2, { auto: true, mode: props.mode })
}

function refreshAnalysis() {
  goAgent(props.team1, props.team2, { auto: true, mode: props.mode, forceRefresh: true })
}

function openFull() {
  if (insight.value?.run_id) {
    goAgent(props.team1, props.team2, { mode: props.mode })
  } else {
    startAnalysis()
  }
}

watch(() => [props.team1, props.team2, props.mode], fetchInsight, { immediate: true })
</script>

<style scoped>
.focus-insight {
  margin-top: 10px;
  padding: 12px 14px;
  text-align: left;
  max-width: 100%;
  background: rgba(18, 18, 18, 0.42) !important;
  backdrop-filter: blur(8px);
  pointer-events: auto;
}

.focus-insight.compact {
  margin-top: 8px;
  padding: 10px 12px;
}

.insight-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.label {
  font-size: 0.72rem;
  color: #D2A76D;
  font-weight: bold;
  letter-spacing: 1px;
}

.summary {
  font-size: 0.82rem;
  line-height: 1.5;
  color: rgba(255, 255, 255, 0.82);
  margin: 0 0 8px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.stats-row {
  display: flex;
  gap: 14px;
  font-size: 0.78rem;
  color: rgba(255, 255, 255, 0.55);
  margin-bottom: 6px;
}

.stats-row strong { color: #D2A76D; }

.prob-text {
  font-size: 0.75rem;
  color: rgba(255, 255, 255, 0.5);
  margin-bottom: 8px;
}

.empty-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.empty-tip {
  font-size: 0.8rem;
  color: rgba(255, 255, 255, 0.55);
  margin: 0;
}

.actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.compact .actions {
  margin-top: 4px;
}
</style>
