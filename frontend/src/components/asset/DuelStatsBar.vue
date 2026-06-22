<template>
  <div v-if="stats" class="duel-stats-bar glass-inner">
    <div class="ds-main">
      <span class="ds-tier">{{ stats.elo_tier?.label || '青铜' }}</span>
      <strong class="ds-elo">{{ stats.duel_elo }}</strong>
      <span class="ds-sub">ELO</span>
    </div>
    <div class="ds-chips">
      <span class="chip">胜 {{ stats.wins }} / 负 {{ stats.losses }}</span>
      <span v-if="stats.win_rate" class="chip">胜率 {{ stats.win_rate }}%</span>
      <span v-if="stats.current_streak >= 2" class="chip hot">
        {{ stats.streak_type === 'win' ? '连胜' : '连败' }} {{ stats.current_streak }}
      </span>
    </div>
    <router-link to="/leaderboard?board=duel_elo" class="ds-link">排位榜 →</router-link>
  </div>
  <div v-else-if="loading" class="duel-stats-bar skeleton">
    <el-skeleton :rows="1" animated />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { getDuelStats, type DuelStats } from '@/api/asset'

const stats = ref<DuelStats | null>(null)
const loading = ref(true)

onMounted(async () => {
  try {
    stats.value = await getDuelStats()
  } catch {
    stats.value = null
  } finally {
    loading.value = false
  }
})

defineExpose({ refresh: async () => {
  try {
    stats.value = await getDuelStats()
  } catch { /* guest */ }
} })
</script>

<style scoped>
.duel-stats-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px 14px;
  padding: 10px 14px;
  margin-bottom: 12px;
  border-radius: 12px;
  border: 1px solid rgba(232, 200, 138, 0.22);
  background: rgba(8, 12, 28, 0.55);
}
.duel-stats-bar.skeleton {
  padding: 12px;
}
.ds-main {
  display: flex;
  align-items: baseline;
  gap: 6px;
}
.ds-tier {
  font-size: 0.72rem;
  font-weight: 700;
  color: #e8c88a;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(232, 200, 138, 0.12);
}
.ds-elo {
  font-size: 1.35rem;
  font-weight: 900;
  color: #f5f0e8;
  line-height: 1;
}
.ds-sub {
  font-size: 0.65rem;
  color: rgba(255, 255, 255, 0.45);
}
.ds-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  flex: 1;
}
.chip {
  font-size: 0.68rem;
  padding: 3px 8px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.06);
  color: rgba(255, 255, 255, 0.65);
}
.chip.hot {
  background: rgba(232, 93, 93, 0.15);
  color: #f0a0a0;
}
.ds-link {
  font-size: 0.72rem;
  color: #9ec8ff;
  text-decoration: none;
  white-space: nowrap;
}
.ds-link:hover {
  color: #e8c88a;
}
</style>
