<template>
  <div class="betting-guide glass-panel">
    <div class="guide-head">
      <div>
        <span class="eyebrow">竞猜参考 · 仅供娱乐</span>
        <h3>{{ guide.one_line_verdict || '综合 AI 分析结论' }}</h3>
      </div>
      <div class="pick-badge" :class="pickClass">
        <span class="pick-code">{{ guide.recommended_pick }}</span>
        <span class="pick-label">{{ guide.pick_label }}</span>
        <span class="pick-prob">{{ Math.round((guide.pick_probability || 0) * 100) }}%</span>
      </div>
    </div>

    <div class="metric-row">
      <div class="metric">
        <span class="metric-label">预测比分</span>
        <strong>{{ guide.predicted_score || '-' }}</strong>
      </div>
      <div class="metric">
        <span class="metric-label">模型置信</span>
        <strong>{{ Math.round((guide.model_confidence || 0) * 100) }}%</strong>
        <span class="metric-sub">{{ guide.confidence_tier }}倾向</span>
      </div>
      <div class="metric">
        <span class="metric-label">进球预期</span>
        <strong class="metric-text">{{ guide.total_goals_hint }}</strong>
      </div>
      <div class="metric">
        <span class="metric-label">牌局风险</span>
        <strong class="metric-text">{{ guide.card_penalty_hint }}</strong>
      </div>
    </div>

    <WinProbChart :team1="team1" :team2="team2" :win-probability="guide.win_probability" />

    <p v-if="guide.rationale" class="rationale">{{ guide.rationale }}</p>
    <p v-if="guide.stake_suggestion" class="stake-tip">{{ guide.stake_suggestion }}</p>

    <div v-if="watchPoints.length" class="watch-block">
      <h4>观赛前必看</h4>
      <ul>
        <li v-for="(w, i) in watchPoints" :key="i">{{ w }}</li>
      </ul>
    </div>

    <div v-if="guide.key_risks?.length" class="risk-block">
      <h4>不确定因素</h4>
      <el-tag v-for="(r, i) in guide.key_risks" :key="i" type="warning" effect="dark" class="risk-tag">{{ r }}</el-tag>
    </div>

    <div class="cta-row">
      <el-button type="primary" @click="$emit('predict')">按 AI 建议去竞猜</el-button>
      <span class="disclaimer">AI 不保证准确，请理性娱乐</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { BettingGuide } from '@/types/api'
import WinProbChart from '@/components/WinProbChart.vue'

const props = defineProps<{
  team1: string
  team2: string
  guide: BettingGuide
  watchPoints?: string[]
}>()

defineEmits<{ predict: [] }>()

const watchPoints = computed(() => props.watchPoints?.length ? props.watchPoints : props.guide.watch_points || [])

const pickClass = computed(() => {
  const tier = props.guide.confidence_tier
  if (tier === '较高') return 'pick-strong'
  if (tier === '分散') return 'pick-split'
  return 'pick-mid'
})
</script>

<style scoped>
.betting-guide {
  padding: 20px 22px;
  margin-bottom: 16px;
  border: 1px solid rgba(210, 167, 109, 0.25);
}

.guide-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 16px;
}

.eyebrow {
  display: block;
  font-size: 0.72rem;
  color: var(--wc-accent-gold);
  letter-spacing: 1px;
  margin-bottom: 6px;
}

.guide-head h3 {
  margin: 0;
  font-size: 1.15rem;
  line-height: 1.45;
  color: #f0f3f6;
}

.pick-badge {
  flex-shrink: 0;
  text-align: center;
  padding: 10px 16px;
  border-radius: 10px;
  background: rgba(46, 160, 67, 0.15);
  border: 1px solid rgba(46, 160, 67, 0.45);
}

.pick-badge.pick-mid {
  background: rgba(210, 167, 109, 0.12);
  border-color: rgba(210, 167, 109, 0.45);
}

.pick-badge.pick-split {
  background: rgba(248, 81, 73, 0.1);
  border-color: rgba(248, 81, 73, 0.35);
}

.pick-code {
  display: block;
  font-size: 1.6rem;
  font-weight: 800;
  color: #D2A76D;
  line-height: 1;
}

.pick-label {
  display: block;
  font-size: 0.82rem;
  color: #c9d1d9;
  margin: 4px 0;
}

.pick-prob {
  font-size: 0.75rem;
  color: #8b949e;
}

.metric-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 14px;
}

.metric {
  background: rgba(0, 0, 0, 0.22);
  border-radius: 8px;
  padding: 10px 12px;
}

.metric-label {
  display: block;
  font-size: 0.72rem;
  color: #8b949e;
  margin-bottom: 4px;
}

.metric strong {
  color: #D2A76D;
  font-size: 1rem;
}

.metric-text {
  font-size: 0.82rem !important;
  line-height: 1.35;
  display: block;
}

.metric-sub {
  display: block;
  font-size: 0.7rem;
  color: #6e7681;
  margin-top: 2px;
}

.rationale {
  margin: 14px 0 8px;
  line-height: 1.65;
  color: #c9d1d9;
  font-size: 0.92rem;
}

.stake-tip {
  margin: 0 0 12px;
  padding: 10px 12px;
  background: rgba(210, 167, 109, 0.08);
  border-left: 3px solid var(--wc-accent-gold);
  color: #b1bac4;
  font-size: 0.85rem;
  line-height: 1.5;
}

.watch-block h4,
.risk-block h4 {
  margin: 0 0 8px;
  font-size: 0.85rem;
  color: var(--wc-accent-gold);
}

.watch-block ul {
  margin: 0 0 12px;
  padding-left: 18px;
  color: #c9d1d9;
  font-size: 0.88rem;
  line-height: 1.55;
}

.risk-tag {
  margin: 0 8px 8px 0;
  white-space: normal;
  height: auto;
  line-height: 1.35;
  max-width: 100%;
}

.cta-row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  margin-top: 8px;
}

.disclaimer {
  font-size: 0.75rem;
  color: #6e7681;
}

@media (max-width: 900px) {
  .guide-head {
    flex-direction: column;
  }
  .metric-row {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
