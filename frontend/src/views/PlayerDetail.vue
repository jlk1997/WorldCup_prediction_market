<template>
  <div class="player-detail" v-loading="loading">
    <el-button plain @click="$router.push('/players')">&lt; 返回球员库</el-button>
    <el-alert v-if="loadError" type="error" :title="loadError" show-icon class="load-error" />
    <div v-if="player" class="header glass-panel">
      <h1>{{ player.name }}</h1>
      <div class="meta">
        <span>{{ player.team_name }}</span>
        <span>{{ player.position }}</span>
        <span v-if="player.age">{{ player.age }} 岁</span>
        <span v-if="player.overall_rating" class="rating">能力 {{ player.overall_rating }}</span>
        <el-tag v-if="player.is_starter" type="success" size="small">首发</el-tag>
      </div>
    </div>

    <div class="grid">
      <div class="section glass-panel" v-if="player?.stats && Object.keys(player.stats).length">
        <h3>能力六维</h3>
        <PlayerRadar :stats="player.stats" />
      </div>

      <div class="section glass-panel">
        <h3>基本信息</h3>
        <p v-if="player?.club">俱乐部：{{ player.club }}</p>
        <p v-if="player?.height">身高：{{ player.height }} cm</p>
        <p v-if="player?.weight">体重：{{ player.weight }} kg</p>
        <p v-if="player?.preferred_foot">惯用脚：{{ player.preferred_foot }}</p>
        <p v-if="player?.market_value">市值：{{ player.market_value }}</p>
      </div>

      <div v-if="player?.injury_status || player?.injury_detail" class="section glass-panel warn">
        <h3>伤病</h3>
        <p>{{ player.injury_status }} — {{ player.injury_detail }}</p>
      </div>

      <div v-if="player?.honors?.length" class="section glass-panel">
        <h3>荣誉</h3>
        <ul><li v-for="(h, i) in player.honors" :key="i">{{ h }}</li></ul>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { apiClient } from '@/api/client'
import type { PlayerDetailed } from '@/types/api'
import PlayerRadar from '@/components/PlayerRadar.vue'

type PlayerDetail = PlayerDetailed & { team_name?: string }

const route = useRoute()
const loading = ref(false)
const loadError = ref('')
const player = ref<PlayerDetail | null>(null)

async function load() {
  const id = route.params.id
  loading.value = true
  loadError.value = ''
  try {
    const res = await apiClient.get<{ status: string; data: PlayerDetail }>(`/api/players/${id}`)
    player.value = res.data.data
  } catch {
    player.value = null
    loadError.value = '球员详情加载失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(() => route.params.id, load)
</script>

<style scoped>
.player-detail { padding: 24px; max-width: 900px; margin: 0 auto; }
.header { padding: 20px; margin: 16px 0; }
.meta { display: flex; gap: 16px; flex-wrap: wrap; color: var(--wc-text-muted); margin-top: 8px; align-items: center; }
.rating { color: var(--wc-accent-gold); font-weight: bold; }
.grid { display: grid; gap: 16px; }
.section { padding: 16px 20px; }
.section.warn { border-left: 3px solid var(--wc-accent-rose); }
.stats-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
.stat-item { background: rgba(212, 165, 116, 0.08); padding: 8px; border-radius: 4px; text-align: center; }
.stat-item strong { display: block; color: var(--wc-accent-gold); font-size: 1.2rem; }

@media (max-width: 768px) {
  .player-detail { padding: 12px 16px; }
  .stats-grid { grid-template-columns: 1fr 1fr; }
  .section { padding: 12px 14px; }
}

@media (max-width: 480px) {
  .stats-grid { grid-template-columns: 1fr; }
}
</style>
