<template>
  <div class="knockout-bracket">
    <div v-for="round in rounds" :key="round.round" class="round-col">
      <h4>{{ round.title }}</h4>
      <div
        v-for="m in round.matches"
        :key="m.id || m.team1 + m.team2"
        class="bracket-match glass-panel"
        @click="onMatchClick(m)"
      >
        <div class="teams">
          <span>{{ m.team1 }}</span>
          <span class="vs">vs</span>
          <span>{{ m.team2 }}</span>
        </div>
        <div class="meta">
          <span v-if="m.home_score != null" class="score">{{ m.home_score }}:{{ m.away_score }}</span>
          <span v-else>{{ m.date }} {{ m.time }}</span>
          <el-tag v-if="m.is_live" type="danger" size="small">LIVE</el-tag>
        </div>
      </div>
    </div>
    <el-empty v-if="!rounds.length" description="暂无淘汰赛数据" />
  </div>
</template>

<script setup lang="ts">
import type { ScheduleItem } from '@/types/api'

export interface BracketRound {
  round: string
  title: string
  matches: ScheduleItem[]
}

defineProps<{ rounds: BracketRound[] }>()
const emit = defineEmits<{ select: [match: ScheduleItem] }>()

function onMatchClick(m: ScheduleItem) {
  emit('select', m)
}
</script>

<style scoped>
.knockout-bracket {
  display: flex;
  gap: 16px;
  overflow-x: auto;
  padding: 12px 0;
  scroll-snap-type: x mandatory;
  -webkit-overflow-scrolling: touch;
}
.round-col {
  min-width: 220px;
  flex-shrink: 0;
  scroll-snap-align: start;
}
.round-col h4 {
  color: var(--wc-accent-gold);
  font-size: 0.85rem;
  margin: 0 0 10px;
  text-align: center;
  font-family: var(--wc-font-serif);
}
.bracket-match {
  padding: 10px 12px;
  margin-bottom: 10px;
  cursor: pointer;
  font-size: 0.8rem;
}
.bracket-match:hover {
  background: rgba(212, 165, 116, 0.08);
}
.teams {
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-weight: 600;
}
.vs { color: #6e7681; font-size: 0.7rem; font-weight: normal; }
.meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 6px;
  color: #8b949e;
  font-size: 0.72rem;
  flex-wrap: wrap;
}
.score { color: var(--wc-accent-gold); font-weight: bold; }

@media (max-width: 768px) {
  .round-col { min-width: 180px; }
}
</style>
