<template>
  <div class="team-compare glass-panel" v-if="data">
    <h4>实力对比</h4>
    <div class="compare-row">
      <div class="side">
        <strong>{{ data.team1.name }}</strong>
        <span>FIFA #{{ data.team1.fifa_ranking ?? '-' }}</span>
        <span>{{ data.team1.formation }}</span>
      </div>
      <div class="vs">VS</div>
      <div class="side">
        <strong>{{ data.team2.name }}</strong>
        <span>FIFA #{{ data.team2.fifa_ranking ?? '-' }}</span>
        <span>{{ data.team2.formation }}</span>
      </div>
    </div>
    <p class="rank-hint" v-if="rankGap > 0">
      FIFA 排名：{{ strongerName }} 更靠前（#{{ strongerRank }} vs #{{ weakerRank }}，相差 {{ rankGap }} 个名次）
    </p>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { apiClient } from '@/api/client'

const props = defineProps<{ team1: string; team2: string }>()

interface CompareData {
  team1: { name: string; fifa_ranking: number | null; formation: string | null }
  team2: { name: string; fifa_ranking: number | null; formation: string | null }
  ranking_diff: number
}

const data = ref<CompareData | null>(null)

const rankGap = computed(() => {
  if (!data.value?.team1.fifa_ranking || !data.value?.team2.fifa_ranking) return 0
  return Math.abs(data.value.team1.fifa_ranking - data.value.team2.fifa_ranking)
})

const strongerName = computed(() => {
  if (!data.value?.team1.fifa_ranking || !data.value?.team2.fifa_ranking) return ''
  return data.value.team1.fifa_ranking < data.value.team2.fifa_ranking ? props.team1 : props.team2
})

const strongerRank = computed(() => {
  if (!data.value?.team1.fifa_ranking || !data.value?.team2.fifa_ranking) return '-'
  return Math.min(data.value.team1.fifa_ranking, data.value.team2.fifa_ranking)
})

const weakerRank = computed(() => {
  if (!data.value?.team1.fifa_ranking || !data.value?.team2.fifa_ranking) return '-'
  return Math.max(data.value.team1.fifa_ranking, data.value.team2.fifa_ranking)
})

async function load() {
  if (!props.team1 || !props.team2) {
    data.value = null
    return
  }
  try {
    const res = await apiClient.get<{ data: CompareData }>('/api/teams/compare', {
      params: { team1: props.team1, team2: props.team2 },
    })
    data.value = res.data.data
  } catch {
    data.value = null
  }
}

watch(() => [props.team1, props.team2], load, { immediate: true })
</script>

<style scoped>
.team-compare { padding: 14px 18px; margin-bottom: 16px; }
.team-compare h4 { margin: 0 0 10px; color: #D2A76D; font-size: 0.9rem; }
.compare-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.side { display: flex; flex-direction: column; gap: 4px; font-size: 0.85rem; color: #A0A0A0; }
.side strong { color: #fff; font-size: 1rem; }
.vs { color: #D2A76D; font-weight: bold; }
.rank-hint { margin: 10px 0 0; font-size: 0.8rem; color: #6e7681; }

@media (max-width: 520px) {
  .compare-row {
    flex-direction: column;
    align-items: stretch;
    text-align: center;
  }
  .vs { padding: 4px 0; }
}
</style>
