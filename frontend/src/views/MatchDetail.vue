<template>



  <div class="match-detail" v-loading="loading">



    <el-button plain @click="$router.push('/live')">&lt; 返回赛事中心</el-button>



    <el-alert v-if="loadError" type="error" :title="loadError" show-icon class="load-error" />



    <div v-if="match" class="header glass-panel">



      <div class="score-line">



        <span class="team">{{ match.team1 }}</span>



        <span class="score">{{ match.home_score ?? 0 }} : {{ match.away_score ?? 0 }}</span>



        <span class="team">{{ match.team2 }}</span>



      </div>



      <div class="meta">



        <el-tag v-if="match.is_live" type="danger">LIVE {{ match.minute }}'</el-tag>



        <el-tag v-else-if="match.status === 'finished'" type="info">已结束</el-tag>



        <span>{{ match.group }} · {{ match.date }} {{ match.time }}</span>



        <span>{{ match.stadium }}</span>



      </div>



    </div>







    <TeamCompareBar v-if="match?.team1 && match?.team2" :team1="match.team1" :team2="match.team2" />







    <FocusInsightCard



      v-if="match?.team1 && match?.team2"



      :team1="match.team1"



      :team2="match.team2"



      :mode="agentMode"



      class="insight-wrap"



    />







    <PredictCard

      v-if="match?.id && match.status !== 'finished' && !match.is_live"

      :match-id="match.id"

    />







    <div class="section glass-panel" v-if="match">



      <MatchEventsTimeline :items="match.events" title="比赛事件" show-empty />



    </div>







    <div class="actions">



      <el-button type="primary" @click="goAgent(true)">{{ agentLabel }}</el-button>



      <el-button plain @click="goAgent(false)">仅打开工作台</el-button>



    </div>



  </div>



</template>







<script setup lang="ts">



import { ref, onMounted, watch, computed } from 'vue'



import { useRoute } from 'vue-router'



import { apiClient } from '@/api/client'



import type { LiveMatch } from '@/types/api'



import { useAgentNavigate } from '@/composables/useAgentNavigate'



import { useLiveMatchesStore } from '@/stores/liveMatchesStore'



import MatchEventsTimeline from '@/components/MatchEventsTimeline.vue'



import TeamCompareBar from '@/components/TeamCompareBar.vue'



import FocusInsightCard from '@/components/FocusInsightCard.vue'



import PredictCard from '@/components/PredictCard.vue'







const route = useRoute()



const { goAgentFromMatch, resolveAgentMode, agentButtonLabel } = useAgentNavigate()



const { matches: livePool } = useLiveMatchesStore()



const loading = ref(false)

const loadError = ref('')

const match = ref<LiveMatch | null>(null)

const matchId = computed(() => Number(route.params.id) || null)



const agentMode = computed(() => (match.value ? resolveAgentMode(match.value) : 'pre_match'))



const agentLabel = computed(() => (match.value ? `${agentButtonLabel(match.value)}（自动运行）` : 'AI 分析'))







async function load() {



  const id = route.params.id



  loading.value = true

  loadError.value = ''



  try {



    const res = await apiClient.get<LiveMatch>(`/api/live/match/${id}`)



    match.value = res.data



  } catch {



    match.value = null

    loadError.value = '比赛详情加载失败，请稍后重试'



  } finally {



    loading.value = false



  }



}







function syncFromLivePool() {

  const id = matchId.value

  if (!id || !match.value) return

  const live = livePool.value.find((m) => m.id === id)

  if (!live) return

  if (match.value.status === 'live' || live.is_live || live.status === 'live') {

    match.value = { ...match.value, ...live }

  }

}







function goAgent(auto: boolean) {



  if (!match.value) return



  goAgentFromMatch(match.value, { auto })



}







onMounted(() => {
  load()
})



watch(() => route.params.id, load)

watch(livePool, syncFromLivePool, { deep: true })



</script>







<style scoped>

.match-detail { padding: 24px; max-width: 720px; margin: 0 auto; }

.load-error { margin: 12px 0; }

.header { padding: 20px; margin: 16px 0; text-align: center; }

.score-line { display: flex; align-items: center; justify-content: center; gap: 20px; flex-wrap: wrap; }

.score-line .score { font-size: 2.5rem; font-weight: 900; color: var(--wc-accent-gold); font-variant-numeric: tabular-nums; }

.score-line .team { font-size: 1.2rem; font-weight: bold; }

.meta { display: flex; gap: 12px; justify-content: center; flex-wrap: wrap; margin-top: 12px; color: var(--wc-text-muted); font-size: 0.85rem; }

.insight-wrap { margin: 16px 0; max-width: 100%; }

.section { padding: 16px 20px; margin-bottom: 16px; }

.actions { display: flex; gap: 12px; justify-content: center; flex-wrap: wrap; }



@media (max-width: 768px) {

  .match-detail { padding: 12px 16px; }

  .match-detail > .el-button { min-height: 44px; margin-bottom: 8px; }

  .header { padding: 14px; margin: 12px 0; }

  .score-line { gap: 12px; }

  .score-line .score { font-size: 2rem; }

  .actions { flex-direction: column; }

  .actions .el-button { width: 100%; min-height: 44px; }

}

</style>






