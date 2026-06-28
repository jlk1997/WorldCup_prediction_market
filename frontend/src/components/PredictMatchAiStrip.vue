<template>
  <div v-if="showStrip" class="predict-ai-strip glass-inner" :class="{ followed: followed }">
    <div class="strip-head">
      <span class="label">✨ AI 参考</span>
      <el-tag v-if="insight?.has_data" size="small" type="info">仅供参考</el-tag>
      <span v-if="confidencePct != null" class="conf-pill">{{ confidencePct }}% 置信</span>
    </div>
    <template v-if="insight?.has_data">
      <p class="summary">{{ insight.summary || '暂无摘要' }}</p>
      <div v-if="insight.win_probability" class="prob-bar" aria-hidden="true">
        <span class="seg home" :style="{ flex: insight.win_probability.team1 }" />
        <span class="seg draw" :style="{ flex: insight.win_probability.draw }" />
        <span class="seg away" :style="{ flex: insight.win_probability.team2 }" />
      </div>
      <div class="pick-row">
        <span v-if="insight.pick_label" class="ai-pick">
          倾向 <strong>{{ insight.pick_label }}</strong>
          <span v-if="insight.predicted_score"> · {{ insight.predicted_score }}</span>
        </span>
        <div class="actions">
          <el-button
            v-if="insight.betting_pick && !predicted"
            size="small"
            type="primary"
            plain
            @click="followAi"
          >
            跟 AI 选
          </el-button>
          <el-button size="small" plain @click="openAgent">深度分析</el-button>
        </div>
      </div>
    </template>
    <template v-else>
      <div class="empty-row">
        <span class="empty-tip">生成 AI 倾向，辅助你的竞猜决策</span>
        <el-button size="small" type="primary" plain @click="openAgent">生成分析</el-button>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { AgentInsight } from '@/types/api'
import { useAgentNavigate, resolveAgentMode } from '@/composables/useAgentNavigate'
import { trackEvent } from '@/utils/analytics'

const props = defineProps<{
  team1: string
  team2: string
  insight: AgentInsight | null | undefined
  predicted?: boolean
  status?: string | null
  isLive?: boolean
}>()

const emit = defineEmits<{ follow: [pick: string] }>()

const { goAgent } = useAgentNavigate()
const followed = ref(false)

const showStrip = computed(() => !!props.team1 && !!props.team2)

const confidencePct = computed(() => {
  const c = props.insight?.confidence
  if (c == null || !Number.isFinite(c)) return null
  return Math.round(c * 100)
})

function mode() {
  if (props.isLive) return 'live' as const
  if (props.status === 'finished') return 'post_match' as const
  return resolveAgentMode({ is_live: !!props.isLive, status: props.status || 'scheduled' })
}

function followAi() {
  const pick = props.insight?.betting_pick
  if (!pick) return
  trackEvent('predict_follow_ai', { team1: props.team1, team2: props.team2 })
  followed.value = true
  ElMessage.success(`已跟 AI 选：${props.insight?.pick_label || pick}`)
  emit('follow', pick)
}

function openAgent() {
  goAgent(props.team1, props.team2, { mode: mode() })
}
</script>

<style scoped>
.predict-ai-strip {
  margin: 10px 0 12px;
  padding: 12px 14px;
  text-align: left;
  border-radius: 12px;
  border: 1px solid rgba(120, 140, 255, 0.2);
  background: linear-gradient(135deg, rgba(80, 100, 200, 0.08), rgba(212, 165, 116, 0.06));
  transition: border-color 0.25s ease, box-shadow 0.25s ease;
}
.predict-ai-strip.followed {
  border-color: rgba(212, 165, 116, 0.45);
  box-shadow: 0 0 0 1px rgba(212, 165, 116, 0.15);
}
.strip-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.label {
  font-size: 0.78rem;
  font-weight: 700;
  color: #9eb4ff;
}
.conf-pill {
  margin-left: auto;
  font-size: 0.68rem;
  color: var(--wc-accent-gold);
}
.summary {
  margin: 0 0 8px;
  font-size: 0.82rem;
  line-height: 1.45;
  color: var(--wc-text-secondary);
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.prob-bar {
  display: flex;
  height: 4px;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 10px;
  gap: 2px;
}
.prob-bar .seg {
  min-width: 4px;
  border-radius: 2px;
}
.prob-bar .home {
  background: #67c23a;
}
.prob-bar .draw {
  background: #909399;
}
.prob-bar .away {
  background: #409eff;
}
.pick-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.ai-pick {
  font-size: 0.8rem;
  color: var(--wc-text-muted);
}
.ai-pick strong {
  color: var(--wc-text-primary);
}
.actions {
  display: flex;
  gap: 6px;
}
.empty-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}
.empty-tip {
  font-size: 0.8rem;
  color: var(--wc-text-muted);
}
</style>
