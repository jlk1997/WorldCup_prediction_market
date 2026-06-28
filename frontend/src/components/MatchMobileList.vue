<template>
  <div class="match-mobile-list">
    <div v-for="m in rows" :key="m.id ?? `${m.team1}-${m.team2}`" class="match-card glass-panel">
      <div class="card-main" @click="m.id && goDetail(m)">
        <div class="teams">{{ m.team1 }} vs {{ m.team2 }}</div>
        <div class="meta">{{ m.group }} · {{ matchStatusLabel(m) }}</div>
        <div class="score">{{ formatMatchScore(m.home_score, m.away_score, { status: m.status, isLive: m.is_live }) }}</div>
        <div v-if="m.stadium" class="stadium">{{ m.stadium }}</div>
      </div>
      <div class="card-actions">
        <el-button v-if="m.id" size="small" class="mobile-full-btn" @click.stop="goDetail(m)">详情</el-button>
        <el-button
          v-if="m.id && isMatchPredictable(m)"
          size="small"
          plain
          class="mobile-full-btn"
          @click.stop="goPredict(m)"
        >
          竞猜
        </el-button>
        <el-button size="small" type="primary" class="mobile-full-btn" @click.stop="$emit('analyze', m)">
          {{ label(m) }}
        </el-button>
      </div>
    </div>
    <el-empty v-if="!rows.length" description="暂无比赛" />
  </div>
</template>

<script setup lang="ts">
import type { LiveMatch } from '@/types/api'
import { useRouter } from 'vue-router'
import { useAgentNavigate } from '@/composables/useAgentNavigate'
import { formatMatchScore, isMatchPredictable, matchStatusLabel } from '@/utils/matchKickoff'

defineProps<{ rows: LiveMatch[] }>()
defineEmits<{ analyze: [row: LiveMatch] }>()

const router = useRouter()
const { goMatchDetail, agentButtonLabel } = useAgentNavigate()

function label(row: LiveMatch) {
  return agentButtonLabel(row)
}

function goDetail(row: LiveMatch) {
  goMatchDetail(row)
}

function goPredict(row: LiveMatch) {
  if (!row.id) return
  router.push({ path: '/predict', query: { highlight: String(row.id) } })
}
</script>

<style scoped>
.match-mobile-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 8px 0;
}

.match-card {
  padding: 14px 16px;
}

.card-main {
  cursor: pointer;
}

.teams {
  font-weight: 700;
  font-size: 1rem;
  color: var(--wc-text-primary);
}

.meta {
  font-size: 0.82rem;
  color: var(--wc-text-muted);
  margin-top: 4px;
}

.score {
  font-size: 1.4rem;
  font-weight: 800;
  color: var(--wc-accent-gold);
  margin-top: 8px;
}

.stadium {
  font-size: 0.75rem;
  color: var(--wc-text-muted);
  margin-top: 4px;
}

.card-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 12px;
}
</style>
