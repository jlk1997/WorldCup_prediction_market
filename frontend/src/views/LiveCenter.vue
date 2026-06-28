<template>
  <div class="live-page page-shell">
    <div class="page-header-row">
      <h2>赛事中心</h2>
      <div class="page-header-actions">
        <el-button type="primary" size="small" @click="refresh" :loading="loading && !wsConnected">刷新</el-button>
        <span v-if="!wsConnected" class="ws-fallback-hint">轮询兜底中</span>
      </div>
    </div>

    <div class="tabs-panel tabs-scroll" :class="{ 'is-mobile-tabs': isMobile }">
      <div v-if="isMobile" class="live-segment mobile-segment">
        <button
          v-for="item in tabItems"
          :key="item.name"
          type="button"
          class="seg-btn"
          :class="{ active: tab === item.name }"
          @click="tab = item.name"
        >
          {{ item.shortLabel }}
        </button>
      </div>
      <el-tabs v-model="tab" class="live-tabs" :class="{ 'hide-header': isMobile }" lazy>
        <el-tab-pane :label="myTeamsTabLabel" name="myteams">
      <div v-if="!authState.accessToken" class="myteams-login-hint">
        <GuestLoginBanner />
      </div>
          <template v-else-if="myTeamNames.size">
          <div v-if="authState.accessToken" class="arena-banner glass-panel" @click="$router.push('/arena')">
            <span>球迷擂台</span>
            <span v-if="nextMainArena">
              下一场战力 {{ nextMainArena.home.power }} : {{ nextMainArena.away.power }}
            </span>
            <span v-else>查看军团贡献与球星热力 →</span>
          </div>
          <div class="match-list">
            <div
              v-for="m in myMatchesSorted"
              :key="m.id"
              class="match-card glass-panel"
              :class="{ live: m.is_live || m.status === 'live', stale: isMatchStaleScheduled(m) }"
            >
              <div class="card-main" @click="goMatch(m)">
                <div class="score">{{ formatMatchScore(m.home_score, m.away_score, { status: m.status, isLive: m.is_live }) }}</div>
                <div class="teams">{{ m.team1 }} vs {{ m.team2 }}</div>
                <div class="meta">{{ matchStatusLabel(m) }}</div>
                <LiveInsightChip :insight="matchInsight(m)" />
                <div v-if="arenaByMatch[m.id!]" class="mini-arena">
                  擂台 {{ arenaByMatch[m.id!].home.power }} : {{ arenaByMatch[m.id!].away.power }}
                </div>
              </div>
              <div class="card-actions">
                <el-button size="small" @click.stop="goMatch(m)">详情</el-button>
                <el-button
                  v-if="isMatchPredictable(m)"
                  size="small"
                  plain
                  @click.stop="$router.push({ path: '/predict', query: { highlight: String(m.id) } })"
                >
                  竞猜
                </el-button>
                <el-button
                  v-if="isMatchPredictable(m)"
                  size="small"
                  plain
                  @click.stop="$router.push(`/cheer/${m.id}`)"
                >
                  助威
                </el-button>
                <el-button size="small" type="primary" @click.stop="goAgent(m, m.is_live)">AI 分析</el-button>
              </div>
            </div>
            <el-empty v-if="!myMatches.length" description="暂无主/副队比赛" />
          </div>
          </template>
          <el-empty v-else description="请先在球迷中心选择主队或副队" />
        </el-tab-pane>

        <el-tab-pane :label="`进行中 (${liveNow.length})`" name="live">
          <div class="match-list">
            <div v-for="m in liveNow" :key="m.id" class="match-card glass-panel live">
              <div class="card-main" @click="goMatch(m)">
                <div class="score">{{ m.home_score ?? 0 }} : {{ m.away_score ?? 0 }}</div>
                <div class="teams">{{ m.team1 }} vs {{ m.team2 }}</div>
                <div class="meta">{{ m.minute }}' · {{ m.period || 'LIVE' }}</div>
                <LiveInsightChip :insight="matchInsight(m)" />
              </div>
              <div class="card-actions">
                <el-button size="small" @click.stop="goMatch(m)">详情</el-button>
                <el-button
                  v-if="isMatchPredictable(m)"
                  size="small"
                  plain
                  @click.stop="$router.push({ path: '/predict', query: { highlight: String(m.id) } })"
                >
                  竞猜
                </el-button>
                <el-button size="small" type="primary" @click.stop="goAgent(m, true)">赛中 AI</el-button>
              </div>
            </div>
            <el-empty v-if="!liveNow.length" description="暂无进行中比赛，比分由后台自动同步" />
          </div>
        </el-tab-pane>

        <el-tab-pane :label="`未开赛 (${scheduled.length})`" name="scheduled">
          <MatchMobileList v-if="isMobile" :rows="scheduled" @analyze="(m) => goAgent(m)" />
          <MatchTable v-else :rows="scheduled" @analyze="(m) => goAgent(m)" />
        </el-tab-pane>

        <el-tab-pane :label="`已结束 (${finished.length})`" name="finished">
          <MatchMobileList v-if="isMobile" :rows="finished" @analyze="(m) => goAgent(m)" />
          <MatchTable v-else :rows="finished" @analyze="(m) => goAgent(m)" />
        </el-tab-pane>

        <el-tab-pane label="淘汰赛" name="knockout">
          <p v-if="isMobile" class="bracket-hint">左右滑动查看完整对阵树</p>
          <KnockoutBracket :rounds="bracketRounds" @select="onBracketSelect" />
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useLiveMatches } from '@/composables/useLiveMatches'
import { useAgentNavigate } from '@/composables/useAgentNavigate'
import { useScheduleInsights } from '@/composables/useScheduleInsights'
import LiveInsightChip from '@/components/LiveInsightChip.vue'
import { apiClient } from '@/api/client'
import { getMatchArena, type MatchArena } from '@/api/arena'
import { authState } from '@/stores/authStore'
import { fetchRecommendations, profileState } from '@/stores/profileStore'
import type { LiveMatch, ScheduleItem } from '@/types/api'
import MatchTable from '@/components/MatchTable.vue'
import MatchMobileList from '@/components/MatchMobileList.vue'
import GuestLoginBanner from '@/components/GuestLoginBanner.vue'
import KnockoutBracket, { type BracketRound } from '@/components/KnockoutBracket.vue'
import { useBreakpoint } from '@/composables/useBreakpoint'
import { usePageMeta } from '@/composables/usePageMeta'
import {
  formatMatchScore,
  isMatchPredictable,
  isMatchStaleScheduled,
  matchStatusLabel,
  parseMatchKickoff,
} from '@/utils/matchKickoff'

usePageMeta({
  title: '2026 世界杯赛程与 Live 比分 — 赛事中心 | 最后一舞',
  description:
    '2026 美加墨世界杯完整赛程、实时比分、淘汰赛对阵与 AI 赛前分析入口。免费查看 104 场比赛安排。',
  path: '/live',
})

const { isMobile } = useBreakpoint()

const tab = ref('live')
const bracketRounds = ref<BracketRound[]>([])

const tabItems = computed(() => {
  const items = [
    { name: 'live', shortLabel: `进行中 (${liveNow.value.length})` },
    { name: 'scheduled', shortLabel: `未开赛 (${scheduled.value.length})` },
    { name: 'finished', shortLabel: `已结束 (${finished.value.length})` },
    { name: 'knockout', shortLabel: '淘汰赛' },
  ]
  items.unshift({
    name: 'myteams',
    shortLabel: authState.accessToken
      ? (myTeamNames.value.size ? `我的 (${myMatches.value.length})` : '我的球队')
      : '我的球队',
  })
  return items
})

const myTeamsTabLabel = computed(() => {
  if (!authState.accessToken) return '我的球队'
  if (!myTeamNames.value.size) return '我的球队'
  return `我的球队 (${myMatches.value.length})`
})

const { goAgentFromMatch, goMatchDetail } = useAgentNavigate()
const { matches, loading, refresh, wsConnected } = useLiveMatches(30000)

const liveNow = computed(() => matches.value.filter((m) => m.is_live || m.status === 'live'))
const scheduled = computed(() => matches.value.filter((m) => (m.status || 'scheduled') === 'scheduled'))
const finished = computed(() => matches.value.filter((m) => m.status === 'finished'))

const myTeamNames = computed(() => {
  const names = new Set<string>()
  const fi = profileState.recommendations?.fan_identity
  if (fi?.main_team?.name) names.add(fi.main_team.name)
  if (fi?.secondary_team?.name) names.add(fi.secondary_team.name)
  return names
})

const myMatches = computed(() =>
  matches.value.filter(
    (m) => m.team1 && m.team2 && (myTeamNames.value.has(m.team1) || myTeamNames.value.has(m.team2))
  )
)

function myMatchSortKey(m: LiveMatch): number {
  if (m.is_live || m.status === 'live') return 0
  if (isMatchPredictable(m)) return 1
  if (isMatchStaleScheduled(m)) return 2
  if (m.status === 'finished') return 3
  return 4
}

const myMatchesSorted = computed(() =>
  [...myMatches.value].sort((a, b) => {
    const ka = myMatchSortKey(a)
    const kb = myMatchSortKey(b)
    if (ka !== kb) return ka - kb
    const ta = parseMatchKickoff(a.date, a.time)?.getTime() ?? 0
    const tb = parseMatchKickoff(b.date, b.time)?.getTime() ?? 0
    return ka === 3 ? tb - ta : ta - tb
  }),
)

const insightMatches = computed(() =>
  [...liveNow.value, ...myMatchesSorted.value.slice(0, 12)]
    .filter((m, i, arr) => m.team1 && m.team2 && arr.findIndex((x) => x.id === m.id) === i)
    .map(
      (m) =>
        ({
          id: m.id,
          team1: m.team1,
          team2: m.team2,
          is_live: m.is_live,
          status: m.status,
        }) as ScheduleItem,
    ),
)

const { getInsight } = useScheduleInsights(insightMatches, {
  enabled: computed(() => !!authState.accessToken),
})

function matchInsight(m: LiveMatch) {
  if (!m.team1 || !m.team2) return null
  return getInsight({
    id: m.id,
    team1: m.team1,
    team2: m.team2,
    is_live: m.is_live,
    status: m.status,
  } as ScheduleItem)
}

const nextMainArena = ref<MatchArena | null>(null)
const arenaByMatch = ref<Record<number, MatchArena>>({})

async function loadArenaData() {
  if (!authState.accessToken) return
  const mainId = profileState.recommendations?.next_main_match?.id
  if (mainId) {
    try {
      nextMainArena.value = await getMatchArena(mainId)
    } catch {
      nextMainArena.value = null
    }
  }
  const map: Record<number, MatchArena> = {}
  const targets = myMatches.value.filter((m) => m.id).slice(0, 8)
  let idx = 0
  async function worker() {
    while (idx < targets.length) {
      const i = idx++
      const m = targets[i]
      if (!m.id) continue
      try {
        map[m.id] = await getMatchArena(m.id)
      } catch {
        /* skip */
      }
    }
  }
  await Promise.all([worker(), worker()])
  arenaByMatch.value = map
}

async function loadGrouped() {
  try {
    const res = await apiClient.get<{ data: { rounds: BracketRound[] } }>('/api/schedule/bracket')
    bracketRounds.value = res.data.data?.rounds || []
  } catch {
    bracketRounds.value = []
  }
}

function goMatch(m: LiveMatch) {
  goMatchDetail(m)
}

function goAgent(m: LiveMatch, auto = false) {
  goAgentFromMatch(m, { auto })
}

function onBracketSelect(m: LiveMatch) {
  if (m.id) goMatchDetail(m)
  else if (m.team1 && m.team2) goAgentFromMatch(m)
}

onMounted(async () => {
  loadGrouped()
  if (authState.accessToken) {
    try {
      await fetchRecommendations()
      await loadArenaData()
      if (myTeamNames.value.size) tab.value = 'myteams'
    } catch {
      /* ignore */
    }
  } else {
    tab.value = 'myteams'
  }
})

watch(myMatches, () => {
  if (authState.accessToken) loadArenaData()
})
</script>

<style scoped>
.live-page { max-width: 1200px; margin: 0 auto; min-height: min-content; }
.tabs-panel {
  background: rgba(10, 12, 24, 0.72);
  border: 1px solid var(--wc-border-soft);
  border-radius: var(--wc-radius-sm);
  padding: 4px 12px 16px;
  margin-top: 4px;
  overflow: hidden;
}

.live-segment {
  margin: 8px 0 12px;
  padding: 0 2px;
}

.seg-btn {
  flex-shrink: 0;
  padding: 8px 14px;
  border-radius: 999px;
  border: 1px solid rgba(212, 165, 116, 0.25);
  background: rgba(18, 22, 40, 0.85);
  color: var(--wc-text-muted);
  font-size: 0.78rem;
  font-weight: 600;
  white-space: nowrap;
  cursor: pointer;
}

.seg-btn.active {
  color: #1a1208;
  background: linear-gradient(135deg, #f0d9b5, var(--wc-accent-gold));
  border-color: var(--wc-accent-gold);
}

.live-tabs.hide-header :deep(.el-tabs__header) {
  display: none;
}

.bracket-hint {
  font-size: 0.78rem;
  color: var(--wc-text-muted);
  margin: 0 0 8px;
  padding: 0 4px;
}
.match-list { display: flex; flex-wrap: wrap; gap: 16px; padding: 12px 0; }
.match-card {
  padding: 16px 20px;
  min-width: 240px;
  flex: 1 1 280px;
  max-width: 100%;
}
.match-card.live { border-left: 3px solid var(--wc-accent-rose); }
.match-card.stale { border-left: 3px solid rgba(230, 162, 60, 0.85); }
.match-card.stale .meta { color: #e6a23c; }
.card-main { cursor: pointer; }
.card-actions { display: flex; gap: 8px; margin-top: 12px; }
.card-actions .el-button { flex: 1; min-height: 40px; }
.score {
  font-size: 2rem;
  font-weight: 900;
  color: var(--wc-accent-gold);
  font-variant-numeric: tabular-nums;
}
.teams { font-weight: bold; margin: 6px 0; color: var(--wc-text-primary); }
.meta { color: #c9d1d9; font-size: 0.85rem; }
.myteams-login-hint {
  margin: 12px 0;
}
.myteams-login-hint :deep(.guest-login-banner) {
  margin-top: 0;
}
.arena-banner {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  margin-bottom: 12px;
  cursor: pointer;
  color: var(--wc-accent-gold);
  font-size: 0.9rem;
}
.mini-arena {
  margin-top: 6px;
  font-size: 0.75rem;
  color: var(--wc-accent-gold);
  opacity: 0.9;
}
.ws-fallback-hint {
  font-size: 0.75rem;
  color: var(--wc-accent-rose);
  margin-left: 8px;
}

@media (max-width: 768px) {
  .tabs-panel {
    padding: 8px 0 16px;
    border-left: none;
    border-right: none;
    border-radius: 0;
    background: transparent;
    border-top: none;
    border-bottom: none;
  }

  .live-segment {
    margin: 0 0 14px;
  }

  .seg-btn {
    padding: 10px 16px;
    font-size: 0.82rem;
  }

  .match-card {
    min-width: 0;
    flex: 1 1 100%;
    width: 100%;
  }
  .card-actions { flex-direction: column; }
  .card-actions .el-button { width: 100%; min-height: 44px; }
  .arena-banner {
    flex-direction: column;
    align-items: flex-start;
    gap: 6px;
  }
  .bracket-hint {
    font-size: 0.78rem;
    color: var(--wc-text-muted);
    margin: 0 0 8px;
    padding: 0 4px;
  }
}
</style>
