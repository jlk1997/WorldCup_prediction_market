<template>
  <div class="team-detail mobile-page" v-loading="loading">
    <el-button plain class="back-btn" @click="$router.push('/teams')">&lt; 返回球队库</el-button>

    <div v-if="team" class="header glass-panel">
      <h1>{{ team.name }}</h1>
      <div class="meta-row">
        <span v-if="team.fifa_ranking" class="meta-chip">FIFA #{{ team.fifa_ranking }}</span>
        <span v-if="team.group_name" class="meta-chip">{{ team.group_name }} 组</span>
        <span v-if="team.coach" class="meta-chip">主帅 {{ team.coach }}</span>
        <span v-if="team.formation" class="meta-chip">阵型 {{ team.formation }}</span>
        <span v-if="team.stadium" class="meta-chip">主场 {{ team.stadium }}</span>
      </div>
    </div>

    <div class="section glass-panel">
      <h3>近期比赛</h3>

      <div v-if="isMobile" class="mobile-list">
        <div v-for="(row, idx) in recentMatches" :key="idx" class="mobile-card glass-inner">
          <div class="card-top">
            <span class="card-date">{{ row.date || '日期待定' }}</span>
            <span class="card-status">{{ statusLabel(row.status) }}</span>
          </div>
          <div class="card-match">{{ row.team1 }} vs {{ row.team2 }}</div>
          <div class="card-score">
            <template v-if="row.home_score != null">{{ row.home_score }} : {{ row.away_score }}</template>
            <template v-else>未开赛</template>
          </div>
          <el-button type="primary" plain size="small" class="card-action" @click="analyzeMatchRow(row)">
            AI 分析
          </el-button>
        </div>
        <p v-if="!recentMatches.length" class="empty-text">暂无赛程记录</p>
      </div>

      <div v-else class="table-scroll-wrap">
        <el-table :data="recentMatches" size="small" empty-text="暂无赛程记录" class="team-table-compact">
          <el-table-column prop="date" label="日期" width="140" />
          <el-table-column label="对阵">
            <template #default="{ row }">{{ row.team1 }} vs {{ row.team2 }}</template>
          </el-table-column>
          <el-table-column label="比分" width="80">
            <template #default="{ row }">
              <span v-if="row.home_score != null">{{ row.home_score }}:{{ row.away_score }}</span>
              <span v-else>-</span>
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="90" />
          <el-table-column label="操作" width="100">
            <template #default="{ row }">
              <el-button link size="small" @click="analyzeMatchRow(row)">分析</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <div class="section glass-panel">
      <h3>阵容</h3>

      <div v-if="isMobile" class="mobile-list">
        <div v-for="row in team?.players || []" :key="row.id" class="mobile-card glass-inner player-card">
          <div class="player-main">
            <router-link :to="`/players/${row.id}`" class="link player-name">{{ row.name }}</router-link>
            <el-tag v-if="row.is_starter" size="small" type="success">首发</el-tag>
          </div>
          <div class="player-meta">
            <span>{{ row.position || '—' }}</span>
            <span>能力 {{ row.overall_rating ?? '—' }}</span>
          </div>
        </div>
        <p v-if="!team?.players?.length" class="empty-text">暂无球员数据</p>
      </div>

      <div v-else class="table-scroll-wrap">
        <el-table :data="team?.players || []" size="small" max-height="360" class="team-table-compact">
          <el-table-column prop="name" label="球员">
            <template #default="{ row }">
              <router-link :to="`/players/${row.id}`" class="link">{{ row.name }}</router-link>
            </template>
          </el-table-column>
          <el-table-column prop="position" label="位置" width="80" />
          <el-table-column prop="overall_rating" label="能力" width="70" />
          <el-table-column prop="is_starter" label="首发" width="70">
            <template #default="{ row }">
              <el-tag v-if="row.is_starter" size="small" type="success">是</el-tag>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <div v-if="injured.length" class="section glass-panel">
      <h3>伤病名单</h3>

      <div v-if="isMobile" class="mobile-list">
        <div v-for="row in injured" :key="row.id" class="mobile-card glass-inner">
          <strong class="injury-name">{{ row.name }}</strong>
          <p v-if="row.injury_status" class="injury-status">{{ row.injury_status }}</p>
          <p v-if="row.injury_detail" class="injury-detail">{{ row.injury_detail }}</p>
        </div>
      </div>

      <div v-else class="table-scroll-wrap">
        <el-table :data="injured" size="small" class="team-table-compact">
          <el-table-column prop="name" label="球员" />
          <el-table-column prop="injury_status" label="状态" />
          <el-table-column prop="injury_detail" label="详情" />
        </el-table>
      </div>
    </div>

    <div class="section glass-panel">
      <h3>相关新闻</h3>
      <div v-for="a in news" :key="a.id" class="news-item">
        <a v-if="a.url" :href="a.url" target="_blank" rel="noopener">{{ a.title }}</a>
        <span v-else>{{ a.title }}</span>
      </div>
      <el-empty v-if="!news.length" description="暂无相关新闻" />
    </div>

    <div class="section glass-panel agent-box">
      <h3>AI 对阵分析</h3>
      <div class="agent-row mobile-form-full">
        <span class="agent-team">{{ team?.name }}</span>
        <span class="agent-vs">vs</span>
        <el-select v-model="opponent" filterable placeholder="选择对手" class="agent-opponent-select">
          <el-option v-for="t in otherTeams" :key="t" :label="t" :value="t" />
        </el-select>
        <el-select v-model="agentMode" class="agent-mode-select">
          <el-option label="赛前" value="pre_match" />
          <el-option label="赛中" value="live" />
          <el-option label="赛后" value="post_match" />
        </el-select>
        <el-button type="primary" :disabled="!opponent" @click="startAgent(true)">立即分析</el-button>
        <el-button plain :disabled="!opponent" @click="startAgent(false)">打开工作台</el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { apiClient } from '@/api/client'
import type { ScheduleItem, TeamBrief, TeamDetail, NewsArticle } from '@/types/api'
import { useAgentNavigate, type AgentMode } from '@/composables/useAgentNavigate'
import { useBreakpoint } from '@/composables/useBreakpoint'
import { usePageMeta } from '@/composables/usePageMeta'

const route = useRoute()
const { goAgent: navigateToAgent } = useAgentNavigate()
const { isMobile } = useBreakpoint()

const loading = ref(false)
const team = ref<TeamDetail | null>(null)
const news = ref<NewsArticle[]>([])
const allTeams = ref<TeamBrief[]>([])
const recentMatches = ref<ScheduleItem[]>([])
const opponent = ref('')
const agentMode = ref<AgentMode>('pre_match')

const routeTeamName = computed(() => decodeURIComponent(String(route.params.name || '')))

usePageMeta(() => {
  const name = team.value?.name || routeTeamName.value
  return {
    title: `${name} — 2026 世界杯球队档案 | 最后一舞`,
    description: `查看 ${name} 的 2026 世界杯阵容、赛程、伤病名单与相关资讯。`,
    path: `/teams/${encodeURIComponent(name)}`,
  }
})

const injured = computed(() =>
  (team.value?.players || []).filter((p) => p.injury_status || p.injuries),
)

const otherTeams = computed(() =>
  allTeams.value.map((t) => t.name).filter((n) => n !== team.value?.name),
)

function statusLabel(status?: string | null) {
  if (status === 'finished') return '已结束'
  if (status === 'live') return '进行中'
  return '未开赛'
}

async function load() {
  const name = decodeURIComponent(route.params.name as string)
  loading.value = true
  try {
    const [teamRes, newsRes, teamsRes, matchesRes] = await Promise.all([
      apiClient.get<{ status: string; data: TeamDetail }>(`/api/team/${encodeURIComponent(name)}`),
      apiClient.get<NewsArticle[]>(`/api/news?team=${encodeURIComponent(name)}&limit=10`),
      apiClient.get<TeamBrief[]>('/api/teams'),
      apiClient.get<{ data: ScheduleItem[] }>(`/api/team/${encodeURIComponent(name)}/matches?limit=12`),
    ])
    team.value = teamRes.data.data
    news.value = newsRes.data
    allTeams.value = teamsRes.data
    recentMatches.value = matchesRes.data.data
  } finally {
    loading.value = false
  }
}

function startAgent(auto: boolean) {
  if (team.value && opponent.value) {
    navigateToAgent(team.value.name, opponent.value, { auto, mode: agentMode.value })
  }
}

function analyzeMatchRow(row: ScheduleItem) {
  if (!team.value || !row.team1 || !row.team2) return
  const other = row.team1 === team.value.name ? row.team2 : row.team1
  navigateToAgent(team.value.name, other, { auto: true, mode: agentMode.value })
}

onMounted(load)
watch(() => route.params.name, load)
</script>

<style scoped>
.team-detail {
  max-width: 900px;
  margin: 0 auto;
  width: 100%;
  overflow-x: hidden;
  box-sizing: border-box;
}

@media (min-width: 769px) {
  .team-detail {
    padding: 24px;
  }
}

.back-btn {
  margin-bottom: 8px;
}

.header {
  padding: 18px 20px;
  margin: 12px 0 14px;
  width: 100%;
  box-sizing: border-box;
}

.header h1 {
  margin: 0;
  font-size: 1.5rem;
  word-break: break-word;
}

.meta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.meta-chip {
  font-size: 0.78rem;
  padding: 5px 10px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.06);
  color: var(--wc-text-muted);
  line-height: 1.3;
  max-width: 100%;
  word-break: break-word;
}

.section {
  padding: 16px 18px;
  margin-bottom: 14px;
  width: 100%;
  box-sizing: border-box;
}

.section h3 {
  margin: 0 0 12px;
  font-size: 1rem;
}

.mobile-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  width: 100%;
}

.mobile-card {
  padding: 14px 16px;
  border-radius: 10px;
  width: 100%;
  box-sizing: border-box;
}

.card-top {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  font-size: 0.75rem;
  color: var(--wc-text-muted);
  margin-bottom: 6px;
}

.card-match {
  font-size: 0.95rem;
  font-weight: 700;
  color: #f5f0e8;
  line-height: 1.4;
  word-break: break-word;
  margin-bottom: 4px;
}

.card-score {
  font-size: 1.1rem;
  font-weight: 800;
  color: var(--wc-accent-gold);
  margin-bottom: 10px;
}

.card-action {
  width: 100%;
  min-height: 40px;
}

.player-card .player-main {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  margin-bottom: 6px;
}

.player-name {
  font-size: 0.95rem;
  font-weight: 700;
  word-break: break-word;
}

.player-meta {
  display: flex;
  gap: 14px;
  font-size: 0.8rem;
  color: var(--wc-text-muted);
}

.injury-name {
  display: block;
  color: #f5f0e8;
  margin-bottom: 4px;
}

.injury-status {
  margin: 0 0 4px;
  font-size: 0.82rem;
  color: #f89898;
}

.injury-detail {
  margin: 0;
  font-size: 0.78rem;
  color: var(--wc-text-muted);
  word-break: break-word;
}

.empty-text {
  text-align: center;
  color: var(--wc-text-muted);
  font-size: 0.85rem;
  padding: 12px 0;
}

.news-item {
  padding: 10px 0;
  border-bottom: 1px dashed rgba(139, 41, 66, 0.35);
  word-break: break-word;
}

.news-item:last-child {
  border-bottom: none;
}

.news-item a,
.link {
  color: var(--wc-accent-gold);
  text-decoration: none;
}

.agent-row {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
  margin-top: 8px;
}

@media (max-width: 768px) {
  .team-detail {
    max-width: 100%;
  }

  .header {
    padding: 14px 16px;
  }

  .header h1 {
    font-size: 1.3rem;
  }

  .section {
    padding: 14px 16px;
  }

  .back-btn {
    width: 100%;
    min-height: 44px;
  }

  .agent-row {
    flex-direction: column;
    align-items: stretch;
  }

  .agent-team,
  .agent-vs {
    text-align: center;
  }

  .agent-row .el-button {
    width: 100%;
    min-height: 44px;
    margin: 0;
  }

  .agent-opponent-select,
  .agent-mode-select,
  .agent-row .el-select {
    width: 100% !important;
  }
}
</style>
