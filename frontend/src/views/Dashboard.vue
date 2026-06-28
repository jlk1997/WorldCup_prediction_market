<template>
  <div class="dashboard-fullscreen">
    <!-- 最底层：超弱透明度的暗蓝灰数据网格 -->
    <div class="tech-grid"></div>
    
    <!-- 巨型柔和暗金环境光晕 (Ethereal backlight) -->
    <div class="ethereal-glow"></div>

    <!-- 球星背景由 App.vue 全站统一渲染 -->
    
    <!-- 顶部：统计 + 邀友/QQ 群 + 连胜守护（文档流排列，避免与焦点赛重叠） -->
    <div class="dashboard-top-stack">
      <div class="stats-strip glass-panel">
        <div class="stats-group stats-group--user" v-if="authState.accessToken && (mainTeamLabel || dailyStatus || arenaMini)">
          <span v-if="mainTeamLabel" class="stat-chip stat-chip--main">
            <em>主队</em>{{ mainTeamLabel }}
          </span>
          <button
            v-if="dailyStatus"
            type="button"
            class="stat-chip stat-chip--link"
            @click="goDailyNext"
          >
            <em>今日</em>{{ dailyStatus.ritual_progress?.done ?? 0 }}/{{ dailyStatus.ritual_progress?.total ?? 3 }}
          </button>
          <button
            v-if="arenaMini"
            type="button"
            class="stat-chip stat-chip--link"
            @click="$router.push('/arena')"
          >
            <em>擂台</em>{{ arenaMini.home.power }}:{{ arenaMini.away.power }}
          </button>
        </div>
        <div class="stats-group stats-group--global">
          <span class="stat-chip"><em>开幕</em>{{ countdownDays }} 天</span>
          <span class="stat-chip"><em>球队</em>48</span>
          <span class="stat-chip"><em>场次</em>{{ stats.matches || 104 }}</span>
          <span v-if="stats.live_matches" class="stat-chip stat-chip--live"><em>LIVE</em>{{ stats.live_matches }}</span>
        </div>
      </div>

      <div v-if="authState.accessToken" class="dashboard-invite-wrap">
        <InvitePromptBar scene="dashboard" :match-day="!!dailyStatus?.match_day" />
        <OfficialQqGroupBar
          :match-day="!!dailyStatus?.match_day"
          :today-signin-count="dailyStatus?.today_signin_count ?? 0"
        />
      </div>

      <StreakRiskBanner :status="dailyStatus" class="dashboard-streak-banner" />

      <GrowthPrimaryCard :status="dailyStatus" />
      <TodayHomePanel v-if="authState.accessToken" />
      <CollectionPassMiniCard />
      <CollectionPassNudgeBar :status="dailyStatus" />
      <MatchDayShareBar
        v-if="dailyStatus?.match_day && dailyStatus?.activation_segment === 'active'"
        :status="dailyStatus"
      />
    </div>

    <!-- 核心聚焦区 -->
    <div class="focus-section" v-if="focusMatch" :class="{ 'lineup-open': showSideDetails && !isMobile, 'schedule-open': scheduleExpanded && !isMobile }">
      <div class="focus-title">
        <div class="live-dot" :class="{ 'is-live': focusMatch?.is_live }"></div>
        <span class="focus-title-text">
          <template v-if="focusMatch?.is_live">进行中 · {{ focusMatch.minute }}'</template>
          <template v-else-if="focusMatch?.status === 'finished'">已结束</template>
          <template v-else>{{ isMainTeamFocus ? '我的主队 · 下一场' : '即将开赛' }}</template>
        </span>
        <button type="button" class="detail-toggle" @click.stop="showSideDetails = !showSideDetails">
          {{ showSideDetails ? '收起阵容' : '展开阵容' }}
        </button>
      </div>
      
      <div class="focus-match-display" :class="{ 'side-expanded': showSideDetails && !isMobile }">
        <!-- 展开阵容：左右球队详情 -->
        <aside v-show="showSideDetails && !isMobile" class="focus-column left-column">
          <TeamLineupColumn
            v-if="leftPanel"
            :team-name="leftPanel.teamName"
            :tag-label="leftPanel.tagLabel"
            :tag-class="leftPanel.tagClass"
            :data="leftPanel.data"
            :loading="leftPanel.loading"
            :top-player="leftPanel.topPlayer"
            :lineup="leftPanel.lineup"
            :bench="leftPanel.bench"
            @header-click="onFocusCardClick(focusMatch)"
          />
        </aside>

        <!-- 中间：对阵主卡片（默认仅显示此区域，留出 3D 球场） -->
        <main class="focus-center">
          <div v-if="!showSideDetails" class="match-hub glass-panel">
            <div class="hub-team">
              <span class="hub-tag" :class="leftPanel?.tagClass">{{ leftPanel?.tagLabel || '主队' }}</span>
              <strong class="hub-name">{{ leftPanel?.teamName || focusMatch.team1 }}</strong>
              <span v-if="leftPanel?.data?.fifa_ranking" class="hub-meta">FIFA {{ leftPanel.data.fifa_ranking }}</span>
            </div>
            <div class="hub-center">
              <span v-if="focusMatch.is_live || focusMatch.home_score != null" class="hub-score">
                {{ focusMatch.home_score ?? 0 }} : {{ focusMatch.away_score ?? 0 }}
              </span>
              <span v-else class="hub-vs">VS</span>
            </div>
            <div class="hub-team hub-team--away">
              <span class="hub-tag" :class="rightPanel?.tagClass">{{ rightPanel?.tagLabel || '客队' }}</span>
              <strong class="hub-name">{{ rightPanel?.teamName || focusMatch.team2 }}</strong>
              <span v-if="rightPanel?.data?.fifa_ranking" class="hub-meta">FIFA {{ rightPanel.data.fifa_ranking }}</span>
            </div>
          </div>

          <div class="vs-panel glass-panel" @click="onFocusCardClick(focusMatch)">
            <div v-if="showSideDetails && (focusMatch.is_live || focusMatch.home_score != null)" class="live-score">
              {{ focusMatch.home_score ?? 0 }} : {{ focusMatch.away_score ?? 0 }}
            </div>
            <div v-else-if="showSideDetails" class="vs-text">VS</div>
            <div class="match-info-pill">
              <span class="group">{{ focusMatch.group }}</span>
              <span class="time">{{ focusMatch.date }} {{ focusMatch.time }}</span>
            </div>
            <div class="stadium"><el-icon><Location /></el-icon> {{ focusMatch.stadium }}</div>
            <div v-if="focusEvents.length && showSideDetails" class="focus-events glass-panel">
              <MatchEventsTimeline :items="focusEvents" title="最新事件" />
            </div>
            <div class="focus-actions">
              <el-button
                v-if="focusMatch.id"
                plain
                class="cyber-btn-secondary"
                @click.stop="goMatchDetail(focusMatch)"
              >
                赛事详情
              </el-button>
              <el-button
                v-if="focusMatch.id && focusCanPredict"
                plain
                class="cyber-btn-secondary"
                @click.stop="$router.push({ path: '/predict', query: { highlight: String(focusMatch.id) } })"
              >
                去竞猜
              </el-button>
              <el-button
                v-if="focusMatch.id && focusCanCheer && authState.user?.profile_completed"
                plain
                class="cyber-btn-secondary"
                @click.stop="$router.push(`/cheer/${focusMatch.id}`)"
              >
                助威
              </el-button>
              <el-button type="primary" class="cyber-btn" @click.stop="goAgentAnalysis(focusMatch)">
                {{ focusMatch.is_live ? '赛中 AI 分析' : '启动 AI 分析' }}
                <span v-if="needsPredictBeforeAi" class="ai-hint-badge">先猜</span>
              </el-button>
            </div>
            <FocusInsightCard
              v-if="focusMatch.team1 && focusMatch.team2"
              :team1="focusMatch.team1"
              :team2="focusMatch.team2"
              :mode="focusAgentMode"
              compact
            />
          </div>
        </main>

        <aside v-show="showSideDetails && !isMobile" class="focus-column right-column">
          <TeamLineupColumn
            v-if="rightPanel"
            :team-name="rightPanel.teamName"
            :tag-label="rightPanel.tagLabel"
            :tag-class="rightPanel.tagClass"
            :data="rightPanel.data"
            :loading="rightPanel.loading"
            :top-player="rightPanel.topPlayer"
            :lineup="rightPanel.lineup"
            :bench="rightPanel.bench"
            @header-click="onFocusCardClick(focusMatch)"
          />
        </aside>
      </div>
    </div>

    <!-- 底部赛程区：始终显示全部，向上展开后更易浏览 -->
    <div class="schedule-section" :class="{ 'is-expanded': scheduleExpanded }">
      <div class="schedule-toolbar">
        <div class="section-title">
          <span class="section-title-cn">后续赛程</span>
          <span v-if="upcomingMatches.length" class="schedule-count">{{ upcomingMatches.length }} 场</span>
        </div>
        <button
          type="button"
          class="expand-btn"
          :class="{ 'is-expanded': scheduleExpanded || scheduleDrawerOpen }"
          @click="toggleSchedule"
        >
          <el-icon :size="14">
            <ArrowUp v-if="!scheduleExpanded && !scheduleDrawerOpen" />
            <ArrowDown v-else />
          </el-icon>
          <span class="expand-btn-text">{{ scheduleExpanded || scheduleDrawerOpen ? '收起' : (isMobile ? '查看全部' : '展开全部') }}</span>
        </button>
      </div>

      <div v-if="!upcomingMatches.length" class="schedule-empty">暂无后续赛程</div>

      <div v-else class="match-grid-wrap" :class="{ 'is-expanded': scheduleExpanded }">
        <!-- 折叠：仅预览前 8 场，避免 ~100 卡片全量挂载 -->
        <div v-if="!scheduleExpanded" class="match-grid match-grid-preview">
          <div
            class="grid-card glass-panel"
            v-for="match in previewMatches"
            :key="match.id ?? `${match.team1}-${match.team2}`"
            @click="onScheduleCardClick(match)"
          >
            <div class="card-header">
              <span class="card-group">{{ match.group }}</span>
              <span class="card-time">{{ match.time }}</span>
            </div>
            <div class="card-teams">
              <span class="t-name">{{ match.team1 }}</span>
              <span v-if="match.home_score != null" class="t-score">{{ match.home_score }}:{{ match.away_score }}</span>
              <span v-else class="t-vs">vs</span>
              <span class="t-name">{{ match.team2 }}</span>
              <el-tag v-if="match.is_live" type="danger" size="small" class="live-tag">LIVE</el-tag>
            </div>
            <div class="card-footer">
              {{ match.date }} · {{ match.stadium }}
            </div>
          </div>
        </div>

        <!-- 展开：双列网格浏览全部（桌面端） -->
        <div v-else-if="!isMobile" class="match-grid match-grid-expanded">
          <div
            class="grid-card glass-panel"
            v-for="match in upcomingMatches"
            :key="match.id ?? `${match.team1}-${match.team2}`"
            @click="onScheduleCardClick(match)"
          >
            <div class="card-header">
              <span class="card-group">{{ match.group }}</span>
              <span class="card-time">{{ match.time }}</span>
            </div>
            <div class="card-teams">
              <span class="t-name">{{ match.team1 }}</span>
              <span v-if="match.home_score != null" class="t-score">{{ match.home_score }}:{{ match.away_score }}</span>
              <span v-else class="t-vs">vs</span>
              <span class="t-name">{{ match.team2 }}</span>
              <el-tag v-if="match.is_live" type="danger" size="small" class="live-tag">LIVE</el-tag>
            </div>
            <div class="card-footer">
              {{ match.date }} · {{ match.stadium }}
            </div>
            <ScheduleInsightTag
              :insight="getInsight(match)"
              @click="goAgentAnalysis(match)"
            />
          </div>
        </div>
        <div v-if="!scheduleExpanded && !scheduleDrawerOpen" class="scroll-fade" aria-hidden="true" />
      </div>
    </div>
    <WinFeedBar
      :items="winFeed"
      :recent-count="winFeedRecentCount"
      :above-bottom-nav="isMobile"
      :pinned="isMobile"
      :highlight-match-id="dailyStatus?.streak_risk?.match_id ?? profileState.recommendations?.next_main_match?.id ?? null"
    />

    <MobileLineupDrawer
      v-if="isMobile"
      v-model="showSideDetails"
      :left-panel="leftPanel"
      :right-panel="rightPanel"
      :match-label="focusMatch ? `${focusMatch.team1} vs ${focusMatch.team2}` : ''"
      @team-click="focusMatch && onFocusCardClick(focusMatch)"
    />

    <MobileScheduleDrawer
      v-if="isMobile"
      v-model="scheduleDrawerOpen"
      :matches="upcomingMatches"
      @select="onScheduleCardClick"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { apiClient } from '../api/client'
import { ElMessage } from 'element-plus'
import { Location, ArrowDown, ArrowUp } from '@element-plus/icons-vue'
import type { MatchEvent, ScheduleItem, StatsOverview } from '../types/api'
import { useStadiumScene } from '../composables/useStadiumScene'
import { useLiveMatches } from '../composables/useLiveMatches'
import { buildFormationDots } from '../config/formationPositions'
import MatchEventsTimeline from '../components/MatchEventsTimeline.vue'
import FocusInsightCard from '../components/FocusInsightCard.vue'
import ScheduleInsightTag from '../components/ScheduleInsightTag.vue'

import { mergeLiveMatches } from '../stores/liveMatchesStore'
import { useAgentNavigate } from '../composables/useAgentNavigate'
import { useScheduleInsights } from '../composables/useScheduleInsights'
import { authState } from '../stores/authStore'
import { fetchRecommendations, profileState } from '../stores/profileStore'
import { getMatchArena, type MatchArena } from '../api/arena'
import { getWinFeed, type WinFeedItem } from '../api/commerce'
import { fetchDailyStatus, useDailyStatusRef } from '../stores/dailyStatusStore'
import TeamLineupColumn from '../components/TeamLineupColumn.vue'
import MobileLineupDrawer from '../components/MobileLineupDrawer.vue'
import MobileScheduleDrawer from '../components/MobileScheduleDrawer.vue'
import InvitePromptBar from '../components/InvitePromptBar.vue'
import OfficialQqGroupBar from '../components/OfficialQqGroupBar.vue'
import StreakRiskBanner from '../components/StreakRiskBanner.vue'
import GrowthPrimaryCard from '../components/GrowthPrimaryCard.vue'
import TodayHomePanel from '../components/TodayHomePanel.vue'
import CollectionPassNudgeBar from '../components/collectible/CollectionPassNudgeBar.vue'
import CollectionPassMiniCard from '../components/collectible/CollectionPassMiniCard.vue'
import MatchDayShareBar from '../components/MatchDayShareBar.vue'
import WinFeedBar from '../components/WinFeedBar.vue'
import { useBreakpoint } from '../composables/useBreakpoint'
import { usePageMeta } from '../composables/usePageMeta'
import { isMatchPredictable } from '../utils/matchKickoff'
import { injectJsonLd } from '../utils/jsonLd'

usePageMeta({
  title: '最后一舞：世界杯2026',
  description:
    '2026 世界杯球迷互动平台 — 竞猜、AI 分析、擂台与排行榜，与传奇同框见证最后一舞。',
  path: '/',
})
import { useStadiumStore } from '../stores/stadiumStore'
import {
  computeTopPlayer,
  panelTag,
  playersFromTeamData,
  resolveFocusSides,
  splitLineup,
  teamNamesMatch,
} from '../composables/useTeamLineup'
import type { LineupPlayer } from '../components/TeamLineupColumn.vue'

const router = useRouter()
const { isMobile } = useBreakpoint()
const { setUiOverlay } = useStadiumStore()

const { goAgentFromMatch, goMatchDetail, resolveAgentMode } = useAgentNavigate()
const { setMatchContext, onScoreChange, triggerGoalEffect: triggerGoalFromScene } = useStadiumScene()
const scheduleData = ref<ScheduleItem[]>([])
const prevScores = ref<Record<number, { h: number | null; a: number | null }>>({})
const stats = ref<Partial<StatsOverview>>({ matches: 104 })
const prevEventCount = ref(0)

const { matches: liveMatches, refresh: refreshLive } = useLiveMatches(30000)
type TeamCacheEntry = { data: Record<string, unknown> | null; loading: boolean }
const teamCache = ref<Record<string, TeamCacheEntry>>({})
const showSideDetails = ref(false)
const scheduleExpanded = ref(false)
const scheduleDrawerOpen = ref(false)
let teamFetchGeneration = 0
const arenaMini = ref<MatchArena | null>(null)
const dailyStatus = useDailyStatusRef()
const winFeed = ref<WinFeedItem[]>([])
const winFeedRecentCount = ref(0)

const needsPredictBeforeAi = computed(() => {
  const seg = dailyStatus.value?.activation_segment
  return seg === 'never_predicted' || seg === 'profile_only'
})

function toggleSchedule() {
  if (isMobile.value) {
    scheduleDrawerOpen.value = !scheduleDrawerOpen.value
    return
  }
  scheduleExpanded.value = !scheduleExpanded.value
}

watch([showSideDetails, scheduleDrawerOpen], ([lineup, schedule]) => {
  setUiOverlay('dashboard', Boolean(lineup || schedule))
})

const countdownDays = computed(() => {
  const today = new Date()
  const kickoff = new Date('2026-06-11T00:00:00') // 2026美加墨世界杯揭幕战时间
  const diff = kickoff.getTime() - today.getTime()
  return diff > 0 ? Math.ceil(diff / (1000 * 3600 * 24)) : 0
})

const focusMatch = computed(() => {
  const live = scheduleData.value.find((m) => m.is_live)
  if (live) return live
  const mainId = profileState.recommendations?.next_main_match?.id
  if (mainId) {
    const main = scheduleData.value.find((m) => m.id === mainId)
    if (main) return main
  }
  return scheduleData.value.length > 0 ? scheduleData.value[0] : null
})

const mainTeamName = computed(
  () => profileState.recommendations?.fan_identity?.main_team?.name ?? null,
)

const mainTeamLabel = computed(() => mainTeamName.value)

const isMainTeamFocus = computed(() => {
  const main = profileState.recommendations?.next_main_match
  const fm = focusMatch.value
  if (!main || !fm?.id) return false
  return main.id === fm.id
})

function buildSidePanel(teamName: string) {
  const fm = focusMatch.value
  if (!fm?.team1 || !fm?.team2) return null
  const cache = teamCache.value[teamName]
  const raw = cache?.data ?? null
  const loading = Boolean(cache?.loading)
  let data = raw
  if (raw && !loading) {
    const apiName = String(raw.name ?? '')
    if (apiName && !teamNamesMatch(apiName, teamName)) {
      data = null
    }
  }
  const players = playersFromTeamData(data as { players?: LineupPlayer[] } | null)
  const { lineup, bench } = splitLineup(players)
  const tag = panelTag(teamName, fm.team1, mainTeamName.value, isMainTeamFocus.value)
  return {
    teamName,
    tagLabel: tag.tagLabel,
    tagClass: tag.tagClass,
    data,
    loading,
    topPlayer: computeTopPlayer(players),
    lineup,
    bench,
  }
}

const focusSides = computed(() => {
  const fm = focusMatch.value
  if (!fm?.team1 || !fm?.team2) return null
  return resolveFocusSides(fm.team1, fm.team2, mainTeamName.value)
})

const leftPanel = computed(() => (focusSides.value ? buildSidePanel(focusSides.value.left) : null))
const rightPanel = computed(() => (focusSides.value ? buildSidePanel(focusSides.value.right) : null))

const focusCanCheer = computed(
  () => profileState.recommendations?.next_main_match?.can_cheer ?? false
)

const focusCanPredict = computed(() => {
  const m = focusMatch.value
  return !!m?.id && isMatchPredictable(m)
})

const focusEvents = computed(() => {
  const ev = focusMatch.value?.events
  if (!ev || !Array.isArray(ev)) return []
  return (ev as MatchEvent[]).slice(-5).reverse()
})

const focusAgentMode = computed(() => {
  if (!focusMatch.value) return 'pre_match' as const
  return resolveAgentMode(focusMatch.value)
})

const upcomingMatches = computed(() => {
  const rest = scheduleData.value.length > 1 ? scheduleData.value.slice(1) : []
  return rest.filter(
    (m) =>
      (m.status === 'scheduled' || !m.status) &&
      m.home_score == null &&
      m.away_score == null,
  )
})

const previewMatches = computed(() => upcomingMatches.value.slice(0, 4))

const { getInsight } = useScheduleInsights(upcomingMatches, { enabled: scheduleExpanded })

async function fetchTeamByName(teamName: string, generation: number) {
  teamCache.value = {
    ...teamCache.value,
    [teamName]: {
      data: teamCache.value[teamName]?.data ?? null,
      loading: true,
    },
  }
  try {
    const res = await apiClient.get<{ status: string; data: Record<string, unknown> }>(
      `/api/team/${encodeURIComponent(teamName)}`,
    )
    if (generation !== teamFetchGeneration) return
    const fm = focusMatch.value
    if (!fm?.team1 || !fm?.team2) return
    const inFocus =
      teamNamesMatch(teamName, fm.team1) || teamNamesMatch(teamName, fm.team2)
    if (!inFocus) return
    const data = res.data?.data ?? null
    teamCache.value = {
      ...teamCache.value,
      [teamName]: { data, loading: false },
    }
  } catch {
    if (generation !== teamFetchGeneration) return
    teamCache.value = {
      ...teamCache.value,
      [teamName]: { data: null, loading: false },
    }
  }
}

function loadFocusTeams() {
  const fm = focusMatch.value
  if (!fm?.team1 || !fm?.team2) return
  const sides = resolveFocusSides(fm.team1, fm.team2, mainTeamName.value)
  const generation = ++teamFetchGeneration
  void fetchTeamByName(sides.left, generation)
  void fetchTeamByName(sides.right, generation)
}

let lastContextKey = ''

watch(focusEvents, (ev) => {
  if (ev.length > prevEventCount.value && prevEventCount.value > 0) {
    const latest = ev[0]
    const t = (latest?.type || '').toLowerCase()
    if (t.includes('goal')) triggerGoalFromScene()
  }
  prevEventCount.value = ev.length
})

watch(liveMatches, (list) => {
  for (const m of list) {
    if (!m.id) continue
    const prev = prevScores.value[m.id]
    if (prev) {
      onScoreChange(prev.h, prev.a, m.home_score, m.away_score)
    }
    prevScores.value[m.id] = { h: m.home_score ?? null, a: m.away_score ?? null }
  }
  if (list.length) {
    scheduleData.value = mergeLiveMatches(scheduleData.value as Parameters<typeof mergeLiveMatches>[0], list) as ScheduleItem[]
  }
})

watch(focusMatch, (newMatch) => {
  teamCache.value = {}
  if (!newMatch?.team1 || !newMatch?.team2) return
  loadFocusTeams()
})

watch(showSideDetails, (open) => {
  if (open) loadFocusTeams()
})

watch(mainTeamName, () => {
  if (focusMatch.value?.team1 && focusMatch.value?.team2) {
    loadFocusTeams()
  }
})

watch([focusMatch, teamCache], ([newMatch]) => {
  if (!newMatch?.team1 || !newMatch?.team2) return
  const ctxKey = `${newMatch.id}-${newMatch.home_score}-${newMatch.away_score}-${newMatch.minute}-${newMatch.status}`
  if (ctxKey === lastContextKey) return
  lastContextKey = ctxKey
  const t1 = teamCache.value[newMatch.team1]?.data as { players?: LineupPlayer[] } | null
  const t2 = teamCache.value[newMatch.team2]?.data as { players?: LineupPlayer[] } | null
  const dots = [
    ...buildFormationDots(t1?.players || [], 'home'),
    ...buildFormationDots(t2?.players || [], 'away'),
  ]
  setMatchContext({
    team1: newMatch.team1,
    team2: newMatch.team2,
    homeScore: newMatch.home_score,
    awayScore: newMatch.away_score,
    minute: newMatch.minute,
    status: newMatch.status,
    stadium: newMatch.stadium,
    formationDots: dots,
  })
}, { deep: true })

const fetchSchedule = async () => {
  try {
    await refreshLive()
    if (!scheduleData.value.length) {
      const res = await apiClient.get<ScheduleItem[]>('/api/schedule')
      scheduleData.value = res.data
    }
  } catch {
    ElMessage.error('无法加载赛程数据，请检查后端服务')
  }
}

function goAgentAnalysis(match: ScheduleItem) {
  if (needsPredictBeforeAi.value) {
    ElMessage.info('先完成首猜，再解锁 AI 分析')
    const path = dailyStatus.value?.activation_nudge?.path || dailyStatus.value?.next_action?.path || '/predict'
    router.push(path.startsWith('/') ? path : '/predict')
    return
  }
  goAgentFromMatch(match, { auto: true })
}

function onFocusCardClick(match: ScheduleItem) {
  if (match.id) goMatchDetail(match)
}

function onScheduleCardClick(match: ScheduleItem) {
  if (match.id) {
    goMatchDetail(match)
    return
  }
  goAgentFromMatch(match)
}

function goDailyNext() {
  const path = dailyStatus.value?.next_action?.path ?? '/predict'
  router.push(path)
}

onMounted(async () => {
  injectJsonLd({
    '@context': 'https://schema.org',
    '@graph': [
      {
        '@type': 'WebSite',
        name: '最后一舞',
        url: 'https://loveaibaby.cn/',
        description:
          '2026 世界杯球迷互动平台 — 竞猜、AI 分析、擂台与排行榜，与传奇同框见证最后一舞。',
      },
      {
        '@type': 'Organization',
        name: '最后一舞',
        url: 'https://loveaibaby.cn/',
        logo: 'https://loveaibaby.cn/share-og.png',
      },
    ],
  })
  try {
    const res = await apiClient.get<{ data: StatsOverview }>('/api/stats/overview')
    stats.value = res.data.data
  } catch {
    /* ignore */
  }
  if (authState.accessToken) {
    try {
      if (!profileState.recommendations) {
        await fetchRecommendations()
      }
      const mid = profileState.recommendations?.next_main_match?.id
      if (mid) {
        arenaMini.value = await getMatchArena(mid)
      }
      await fetchDailyStatus(true)
    } catch {
      /* ignore */
    }
  }
  try {
    const res = await getWinFeed(12)
    winFeed.value = res.items
    winFeedRecentCount.value = res.recent_count
  } catch {
    winFeed.value = []
  }
  await fetchSchedule()
})
</script>

<style scoped>
/* 全局网格背景 */
.dashboard-fullscreen::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-image: 
    linear-gradient(rgba(210, 167, 109, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(210, 167, 109, 0.03) 1px, transparent 1px);
  background-size: 30px 30px;
  z-index: 0;
  pointer-events: none;
}

.dashboard-fullscreen {
  height: 100%;
  width: 100%;
  display: flex;
  flex-direction: column;
  color: #fff;
  overflow: hidden;
  position: relative;
  pointer-events: none; /* 让顶层穿透 */
  background: transparent; /* 确保自身透明 */
}

/* ================= 科幻指挥中心环境底座 ================= */
.tech-grid {
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  /* 极微弱的暗蓝灰色网格，透明度 < 4% */
  background-image: 
    linear-gradient(rgba(44, 58, 71, 0.035) 1px, transparent 1px),
    linear-gradient(90deg, rgba(44, 58, 71, 0.035) 1px, transparent 1px);
  background-size: 50px 50px;
  z-index: 0;
  pointer-events: none;
}

/* 巨型、柔和的环境光晕 — 玫瑰金 + 淡紫 */
.ethereal-glow {
  position: absolute;
  top: -10%;
  left: 50%;
  transform: translateX(-50%);
  width: 1400px;
  height: 900px;
  background:
    radial-gradient(ellipse at top center, var(--wc-glow-gold) 0%, rgba(212, 165, 116, 0.08) 40%, transparent 65%),
    radial-gradient(ellipse at 30% 20%, var(--wc-glow-rose) 0%, transparent 50%);
  filter: blur(48px);
  will-change: transform;
  z-index: 1;
  pointer-events: none;
}

/* ======= 顶部区域（统计 + 邀友 + 连胜） ======= */
.dashboard-top-stack {
  position: relative;
  z-index: 25;
  pointer-events: auto;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px 20px 0;
}

.stats-strip {
  position: relative;
  top: auto;
  left: auto;
  right: auto;
  z-index: 1;
  pointer-events: auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 14px;
  border-radius: 10px;
  background: rgba(10, 12, 20, 0.72);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(212, 165, 116, 0.12);
}

.dashboard-invite-wrap {
  position: relative;
  top: auto;
  left: auto;
  right: auto;
  z-index: 1;
  pointer-events: auto;
  max-width: 480px;
  width: 100%;
}

.dashboard-top-stack :deep(.invite-prompt-bar),
.dashboard-top-stack :deep(.qq-social-bar) {
  margin-bottom: 0;
}

.dashboard-top-stack :deep(.dashboard-streak-banner),
.dashboard-top-stack :deep(.streak-risk-banner),
.dashboard-top-stack :deep(.growth-primary),
.dashboard-top-stack :deep(.match-day-share-bar) {
  margin-bottom: 0;
}

.stats-group {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.stats-group--user {
  flex: 1;
  min-width: 0;
}

.stats-group--global {
  flex-shrink: 0;
  justify-content: flex-end;
}

.stat-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  font-size: 0.78rem;
  font-weight: 700;
  color: #e8e0d4;
  white-space: nowrap;
}

.stat-chip em {
  font-style: normal;
  font-size: 0.65rem;
  font-weight: 600;
  color: #8a8f98;
  letter-spacing: 0.5px;
}

.stat-chip--main {
  border-color: rgba(212, 165, 116, 0.35);
  background: rgba(212, 165, 116, 0.1);
  color: #f5e6d0;
}

.stat-chip--live {
  border-color: rgba(201, 120, 138, 0.45);
  color: #ffb8c9;
}

.stat-chip--link {
  cursor: pointer;
  font: inherit;
  transition: background 0.2s, border-color 0.2s;
}

.stat-chip--link:hover {
  background: rgba(212, 165, 116, 0.14);
  border-color: rgba(212, 165, 116, 0.35);
}

/* ================= 核心聚焦区 ================= */
.focus-section {
  flex: 1;
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  align-items: center;
  padding-top: 12px;
  width: 100%;
  min-height: 0;
  z-index: 10;
  transition: padding-top 0.3s ease;
}

.focus-section.lineup-open {
  padding-top: 12px;
}

.focus-section.schedule-open {
  padding-top: 12px;
}

.focus-title {
  position: relative;
  top: auto;
  left: auto;
  margin: 0 20px 10px;
  align-self: flex-start;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  font-weight: 700;
  color: #d2a76d;
  letter-spacing: 0.5px;
  background: rgba(10, 12, 18, 0.65);
  padding: 6px 12px;
  border-radius: 999px;
  border: 1px solid rgba(210, 167, 109, 0.2);
  backdrop-filter: blur(8px);
  pointer-events: auto;
  z-index: 12;
}

.focus-title-text {
  color: #f0e6d8;
}

.detail-toggle {
  margin-left: 4px;
  padding: 3px 10px;
  border-radius: 999px;
  border: 1px solid rgba(210, 167, 109, 0.35);
  background: rgba(210, 167, 109, 0.12);
  color: #f0d9b5;
  font-size: 11px;
  cursor: pointer;
  font-weight: 600;
}

.detail-toggle:hover {
  background: rgba(210, 167, 109, 0.18);
  color: #f0d9b5;
}

.live-dot {
  width: 8px;
  height: 8px;
  background-color: #D2A76D;
  border-radius: 50%;
  box-shadow: 0 0 10px #D2A76D;
}

.live-dot.is-live {
  background-color: var(--wc-accent-rose);
  box-shadow: 0 0 12px var(--wc-accent-rose);
  animation: pulseRose 1s infinite;
}

@media (prefers-reduced-motion: reduce) {
  .live-dot.is-live {
    animation: none;
  }
  .expand-btn:not(:hover) {
    animation: none;
  }
}

@keyframes pulseRose {
  0% { transform: scale(0.9); opacity: 0.7; }
  50% { transform: scale(1.5); opacity: 1; box-shadow: 0 0 20px var(--wc-accent-rose); }
  100% { transform: scale(0.9); opacity: 0.7; }
}

.live-score {
  font-size: 2.5rem;
  font-weight: 900;
  color: #D2A76D;
  text-shadow: 0 0 20px rgba(210, 167, 109, 0.6);
}

.t-score { color: #D2A76D; font-weight: bold; margin: 0 4px; }
.live-tag { margin-left: 6px; vertical-align: middle; }


@keyframes pulse {
  0% { transform: scale(0.9); opacity: 0.7; }
  50% { transform: scale(1.5); opacity: 1; box-shadow: 0 0 20px #D2A76D; }
  100% { transform: scale(0.9); opacity: 0.7; }
}

.focus-match-display {
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
  align-items: start;
  justify-content: center;
  width: 100%;
  max-width: 420px;
  padding: 0 16px;
  pointer-events: none;
  margin-top: 28px;
}

.focus-match-display.side-expanded {
  grid-template-columns: minmax(240px, 300px) minmax(260px, 340px) minmax(240px, 300px);
  max-width: 1280px;
  gap: 16px;
  margin-top: 36px;
}

.match-hub {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  margin-bottom: 8px;
  pointer-events: auto;
  background: rgba(10, 12, 18, 0.55) !important;
}

.hub-team {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.hub-team--away {
  align-items: flex-end;
  text-align: right;
}

.hub-tag {
  font-size: 0.62rem;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 999px;
  width: fit-content;
}

.hub-tag.home, .hub-tag.main {
  color: #d2a76d;
  background: rgba(210, 167, 109, 0.12);
  border: 1px solid rgba(210, 167, 109, 0.25);
}

.hub-tag.away {
  color: #c9d1d9;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.hub-name {
  font-size: 1.05rem;
  font-weight: 800;
  color: #fff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.hub-meta {
  font-size: 0.72rem;
  color: #9aa0a8;
}

.hub-center {
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 48px;
}

.hub-vs, .hub-score {
  font-size: 1.1rem;
  font-weight: 900;
  color: #d2a76d;
}

.match-teams-line {
  font-size: 1rem;
  font-weight: 800;
  color: #fff;
  text-align: center;
  letter-spacing: 0.5px;
}

.match-teams-line .vs-dot {
  color: #d2a76d;
  font-weight: 700;
  margin: 0 6px;
}

.focus-column {
  display: flex;
  flex-direction: column;
  gap: 10px;
  pointer-events: auto;
  max-height: calc(var(--app-height, 100dvh) - 220px);
}

.left-column { justify-self: end; }
.right-column { justify-self: start; }

.focus-center {
  justify-self: center;
  width: 100%;
  max-width: 400px;
  pointer-events: auto;
}

.focus-match-display.side-expanded .focus-center {
  max-width: 360px;
  padding-top: 4px;
}

.team-header {
  padding: 14px 16px;
  border-radius: 12px;
  background: rgba(18, 18, 18, 0.42) !important;
  backdrop-filter: blur(10px);
  cursor: pointer;
  transition: background 0.2s;
}

.team-header:hover {
  background: rgba(24, 24, 24, 0.58) !important;
}

.side-tag-inline {
  display: inline-block;
  font-size: 0.65rem;
  font-weight: 700;
  letter-spacing: 1px;
  padding: 2px 8px;
  border-radius: 999px;
  margin-bottom: 6px;
}

.side-tag-inline.home {
  color: #D2A76D;
  background: rgba(210, 167, 109, 0.12);
  border: 1px solid rgba(210, 167, 109, 0.3);
}

.side-tag-inline.away {
  color: #c9d1d9;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.12);
}

.side-tag-inline.main {
  color: #ffe8b8;
  background: rgba(212, 165, 116, 0.22);
  border: 1px solid rgba(212, 165, 116, 0.55);
  box-shadow: 0 0 12px rgba(212, 165, 116, 0.2);
}

.data-stack {
  display: flex;
  flex-direction: column;
  gap: 10px;
  overflow: hidden;
}

/* 废弃旧绝对定位侧栏 */
.side-data-panel,
.team-panel,
.vs-panel-wrapper,
.side-tag { display: none; }

.data-card {
  background: rgba(18, 18, 18, 0.48);
  border-radius: 10px;
  padding: 10px 12px;
  backdrop-filter: blur(8px);
}

.starting-xi {
  max-height: 200px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.card-header {
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  padding-bottom: 8px;
  margin-bottom: 10px;
  text-align: center;
  flex-shrink: 0;
}
.card-header h3 {
  margin: 0;
  font-size: 0.85rem;
  background: linear-gradient(135deg, #D2A76D 0%, #A67C41 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  letter-spacing: 1px;
}
.card-header p {
  margin: 2px 0 0;
  font-size: 0.72rem;
  color: rgba(255, 255, 255, 0.45);
}

/* 球队信息与首发球员样式 */
.empty-data {
  text-align: center;
  color: #A0A0A0;
  font-style: italic;
  padding: 20px 0;
}

.team-info {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px 15px;
}
.team-info .info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0;
  font-size: 0.85rem;
  border-bottom: 1px dashed rgba(210, 167, 109, 0.15); /* 香槟金弱虚线 */
  padding-bottom: 4px;
}
.team-info .info-row span:first-child {
  color: #A0A0A0;
}
.team-info .info-row .highlight {
  color: #D2A76D; /* 香槟金 */
  font-weight: bold;
}
.truncate-text {
  max-width: 90px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  text-align: right;
}

/* 核心球员 */
.kp-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.kp-name {
  font-weight: 900;
  font-size: 1.1rem;
  color: #fff;
  text-shadow: 0 0 10px rgba(255,255,255,0.3);
}
.kp-rating {
  font-size: 1.3rem;
  font-weight: 900;
  font-family: 'Courier New', Courier, monospace;
  color: #D2A76D;
}
.kp-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 5px;
  font-size: 0.75rem;
  color: #A0A0A0;
}
.kp-stats span {
  background: rgba(210, 167, 109, 0.05);
  padding: 4px;
  border-radius: 4px;
  text-align: center;
  border: 1px solid rgba(210, 167, 109, 0.15);
}

.player-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  overflow-y: auto;
  padding-right: 5px;
}
.player-list::-webkit-scrollbar {
  width: 4px;
}
.player-list::-webkit-scrollbar-thumb {
  background: rgba(210, 167, 109, 0.5); /* 香槟金滚动条 */
  border-radius: 4px;
}
.player-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding-bottom: 8px;
  border-bottom: 1px dashed rgba(210, 167, 109, 0.15);
}
.player-item:last-child {
  border-bottom: none;
  padding-bottom: 0;
}
.p-pos {
  font-size: 0.75rem;
  padding: 3px 6px;
  border-radius: 4px;
  min-width: 35px;
  text-align: center;
  font-weight: bold;
}
.pos-gk { color: #A0A0A0; border: 1px solid #A0A0A0; background: rgba(160, 160, 160, 0.1); } 
.pos-df { color: #D2A76D; border: 1px solid #D2A76D; background: rgba(210, 167, 109, 0.1); } 
.pos-mf { color: #D2A76D; border: 1px solid #D2A76D; background: rgba(210, 167, 109, 0.1); } 
.pos-fw { color: #D2A76D; border: 1px solid #D2A76D; background: rgba(210, 167, 109, 0.1); }

.p-info {
  display: flex;
  flex-direction: column;
  min-width: 0; /* 防止文本溢出 */
  line-height: 1.2;
}
.p-name {
  font-size: 1rem;
  font-weight: bold;
  color: #FFFFFF;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: flex;
  align-items: center;
}
.p-club {
  font-size: 0.75rem;
  font-weight: normal;
  color: #A0A0A0;
  margin-left: 4px;
}
.starter-badge {
  font-size: 0.6rem;
  background: rgba(210, 167, 109, 0.15);
  color: #D2A76D;
  border: 1px solid rgba(210, 167, 109, 0.4);
  padding: 1px 4px;
  border-radius: 3px;
  margin-left: 6px;
  font-weight: normal;
  letter-spacing: 1px;
}
.p-meta {
  font-size: 0.7rem;
  color: #A0A0A0;
  margin-top: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.p-rating {
  font-weight: 900;
  font-family: 'Courier New', Courier, monospace;
  font-size: 1.1rem;
  margin-left: auto;
}
.rating-gold { color: #D2A76D; text-shadow: 0 0 8px rgba(210, 167, 109, 0.6); } 
.rating-silver { color: #A67C41; text-shadow: 0 0 8px rgba(166, 124, 65, 0.6); } 
.rating-bronze { color: #8A6327; text-shadow: 0 0 8px rgba(138, 99, 39, 0.6); } 
.rating-gray { color: #A0A0A0; }

/* ======= 球队面板科技感排版 ======= */
.team-panel {
  display: flex;
  flex-direction: column;
  gap: 15px;
  flex: 1;
  position: relative;
  margin-top: -60px; /* 下移，避免贴近顶部状态栏 */
}

.left-team { align-items: flex-end; text-align: right; padding-right: 40px; }
.right-team { align-items: flex-start; text-align: left; padding-left: 40px; }

.team-card {
  background: rgba(18, 18, 18, 0.75);
  padding: 20px 30px;
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  align-items: center; /* 让内部的球队名和数据方块整体居中 */
  backdrop-filter: blur(12px);
  max-width: 600px; /* 增加宽度，防止小方块换行 */
}

.left-team .team-card { /* 移除覆盖 align-items */ }
.right-team .team-card { /* 移除覆盖 align-items */ }

/* 废弃旧的 team-tag */
.team-tag { display: none; }

.team-name {
  font-size: 1.65rem;
  font-weight: 800;
  margin: 0 0 8px;
  letter-spacing: 1px;
  text-align: left;
  color: #ffffff;
  text-shadow: 0 0 12px rgba(255, 255, 255, 0.25);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.right-column .team-name {
  text-align: right;
}

.right-column .team-header {
  text-align: right;
}

.right-column .team-info-blocks {
  justify-content: flex-end;
}

/* 队名下方横向排列的球队档案模块框 */
.team-info-blocks {
  display: flex;
  flex-wrap: nowrap; /* 强制不换行 */
  justify-content: center; /* 方块整体居中 */
  gap: 12px;
}

.left-team .team-info-blocks { /* 移除覆盖 justify-content */ }
.right-team .team-info-blocks { /* 移除覆盖 justify-content */ }

.info-block {
  background: rgba(30, 26, 23, 0.4); /* 弱化背景，融入大卡片 */
  border: 1px solid rgba(210, 167, 109, 0.15); /* 弱化边框 */
  padding: 6px 12px;
  border-radius: 6px;
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 70px;
}

.info-block .block-label {
  color: #A0A0A0;
  text-transform: uppercase;
  font-size: 0.65rem;
  letter-spacing: 1px;
  margin-bottom: 3px;
}

.info-block .block-value {
  color: #FFFFFF;
  font-size: 0.9rem;
  font-weight: bold;
}

.info-block .block-value.highlight {
  color: #D2A76D;
  text-shadow: 0 0 10px rgba(210, 167, 109, 0.4);
}

/* 彻底删除 team-glitch 特效类 */

/* ======= 中间 VS 面板及侧边标签 ======= */
.vs-panel-wrapper {
  display: flex;
  align-items: center;
  gap: 15px; /* 缩小标签和 VS 中心的距离 */
  transform: translateY(-20px);
}

.side-tag {
  font-size: 1rem;
  font-weight: bold;
  color: #D2A76D; /* 浅香槟金文本 */
  letter-spacing: 2px;
  background: rgba(30, 26, 23, 0.6); /* 古铜底色 */
  backdrop-filter: blur(10px);
  padding: 5px 15px;
  border-radius: 20px;
  border: 1px solid rgba(210, 167, 109, 0.2);
  text-shadow: none;
  opacity: 1;
  white-space: nowrap;
  margin-top: -30px;
}
.home-tag { 
  background: linear-gradient(90deg, rgba(210, 167, 109, 0.15), transparent);
  border-left: 3px solid #D2A76D;
  border-right: none;
  padding-left: 20px;
}
.away-tag { 
  background: linear-gradient(-90deg, rgba(210, 167, 109, 0.15), transparent);
  border-right: 3px solid #D2A76D;
  border-left: none;
  padding-right: 20px;
}

.vs-panel {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 14px 16px 12px;
  border-radius: 14px;
  background: rgba(10, 12, 18, 0.62) !important;
  backdrop-filter: blur(12px);
  border: 1px solid rgba(210, 167, 109, 0.18);
  cursor: pointer;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.28);
}

.vs-text {
  font-size: 1.5rem;
  font-weight: 900;
  color: #D2A76D;
  text-shadow: 0 0 12px rgba(210, 167, 109, 0.45);
  font-style: italic;
}

.match-info-pill {
  display: flex;
  gap: 12px;
  background: rgba(30, 26, 23, 0.8);
  border: 1px solid #D2A76D; /* 香槟金 */
  padding: 5px 12px;
  border-radius: 4px;
  font-size: 0.8rem;
  box-shadow: 0 0 15px rgba(210, 167, 109, 0.2);
}

.group { color: #D2A76D; font-weight: bold; }

.stadium {
  font-size: 0.85rem;
  color: #A0A0A0;
  letter-spacing: 1px;
  display: flex;
  align-items: center;
  gap: 5px;
  background: rgba(0,0,0,0.4);
  padding: 5px 12px;
  border-radius: 20px;
}

.focus-events {
  margin-top: 8px;
  padding: 8px 12px;
  max-width: 280px;
  pointer-events: auto;
  text-align: left;
}

/* 赛博朋克按钮 -> 奢华金属按钮 */
.cyber-btn {
  pointer-events: auto;
  margin-top: 5px;
  background: rgba(210, 167, 109, 0.1) !important;
  border: 1px solid #D2A76D !important; /* 香槟金按钮 */
  color: #D2A76D !important;
  border-radius: 4px;
  padding: 8px 20px;
  font-size: 0.9rem;
  font-weight: bold;
  letter-spacing: 2px;
  position: relative;
  overflow: hidden;
  transition: all 0.3s;
}

.ai-hint-badge {
  display: inline-block;
  margin-left: 6px;
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 0.65rem;
  font-weight: 600;
  letter-spacing: 0;
  background: rgba(230, 162, 60, 0.25);
  color: #e6a23c;
  vertical-align: middle;
}

.cyber-btn::before {
  content: '';
  position: absolute;
  top: 0; left: -100%; width: 100%; height: 100%;
  background: linear-gradient(90deg, transparent, rgba(210, 167, 109, 0.4), transparent);
  transition: all 0.5s;
}
.cyber-btn:hover {
  background: rgba(210, 167, 109, 0.2) !important;
  box-shadow: 0 0 20px rgba(210, 167, 109, 0.4);
}
.cyber-btn:hover::before {
  left: 100%;
}

.focus-actions {
  display: flex;
  gap: 8px;
  justify-content: center;
  flex-wrap: wrap;
  margin-top: 4px;
  width: 100%;
  pointer-events: auto;
}

.focus-actions .cyber-btn,
.focus-actions .cyber-btn-secondary {
  flex: 1 1 auto;
  min-width: 96px;
  margin-top: 0 !important;
}

.cyber-btn-secondary {
  pointer-events: auto;
  border-color: rgba(210, 167, 109, 0.4) !important;
  color: #A0A0A0 !important;
  background: transparent !important;
}

/* ================= 底部赛程区（全量展示 + 向上展开） ================= */
.schedule-section {
  flex: 0 0 auto;
  padding: 8px 24px 12px;
  background: linear-gradient(to top, rgba(10, 12, 24, 0.82) 0%, rgba(10, 12, 24, 0.28) 55%, transparent 100%);
  z-index: 10;
  pointer-events: auto;
  transition: background 0.35s ease, box-shadow 0.35s ease, padding 0.35s ease;
}

.schedule-section.is-expanded {
  padding-top: 12px;
  padding-bottom: 16px;
  background: linear-gradient(to top, rgba(10, 12, 24, 0.96) 0%, rgba(10, 12, 24, 0.88) 70%, rgba(10, 12, 24, 0.55) 100%);
  box-shadow: 0 -16px 48px rgba(0, 0, 0, 0.45);
}

.schedule-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  margin-bottom: 10px;
  gap: 12px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 0;
}

.section-title-cn {
  font-size: 0.92rem;
  font-weight: 800;
  color: #f0e6d8;
  letter-spacing: 1px;
}

.expand-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
  padding: 6px 14px;
  border-radius: 999px;
  border: 1px solid rgba(212, 165, 116, 0.35);
  background: rgba(212, 165, 116, 0.1);
  color: #f5e6d0;
  font-size: 0.78rem;
  font-weight: 700;
  cursor: pointer;
  transition: background 0.2s, border-color 0.2s;
}

.expand-btn:hover {
  background: rgba(212, 165, 116, 0.18);
  border-color: rgba(212, 165, 116, 0.5);
}

.expand-btn.is-expanded {
  border-color: rgba(201, 120, 138, 0.4);
  background: rgba(201, 120, 138, 0.12);
}

.expand-btn-text {
  white-space: nowrap;
}

.schedule-count {
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0;
  color: var(--wc-accent-gold);
  background: rgba(212, 165, 116, 0.1);
  border: 1px solid var(--wc-border-soft);
  padding: 2px 8px;
  border-radius: 999px;
}

.schedule-empty {
  font-size: 0.82rem;
  color: var(--wc-text-muted);
  padding: 8px 0 4px;
}

.match-grid-wrap {
  position: relative;
  max-height: 168px;
  overflow: hidden;
  transition: max-height 0.35s cubic-bezier(0.4, 0, 0.2, 1);
  border-radius: 10px;
}

.match-grid-wrap:not(.is-expanded) {
  padding-bottom: 8px;
}

.match-grid-wrap.is-expanded {
  max-height: min(72vh, 720px);
}

.match-grid-expanded {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  max-height: min(72vh, 720px);
  overflow-y: auto;
  overflow-x: hidden;
  padding-right: 4px;
  -webkit-overflow-scrolling: touch;
  overscroll-behavior: contain;
  scrollbar-width: thin;
  scrollbar-color: var(--wc-accent-gold) transparent;
}

.match-grid-expanded::-webkit-scrollbar {
  width: 4px;
}

.match-grid-expanded::-webkit-scrollbar-thumb {
  background: var(--wc-accent-gold);
  border-radius: 4px;
}

.schedule-virtual-list {
  max-height: min(72vh, 720px);
}

.match-grid-preview {
  max-height: 168px;
  overflow: hidden;
}

.grid-card .card-footer {
  font-size: 0.68rem;
  color: #a8adb5;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.scroll-fade {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: 36px;
  background: linear-gradient(to top, rgba(10, 12, 24, 0.98) 0%, rgba(10, 12, 24, 0.6) 55%, transparent 100%);
  pointer-events: none;
  z-index: 2;
}

.match-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  max-height: inherit;
  overflow-y: auto;
  overflow-x: hidden;
  padding-right: 4px;
  -webkit-overflow-scrolling: touch;
  overscroll-behavior: contain;
  scrollbar-width: thin;
  scrollbar-color: var(--wc-accent-gold) transparent;
}

.match-grid::-webkit-scrollbar {
  width: 4px;
}

.match-grid::-webkit-scrollbar-thumb {
  background: var(--wc-accent-gold);
  border-radius: 4px;
}

.match-grid .grid-card {
  min-height: 76px;
  padding: 8px 10px;
  gap: 4px;
}

.match-grid .card-teams {
  font-size: 0.82rem;
  gap: 3px;
  flex-wrap: wrap;
  line-height: 1.25;
}

.match-grid .t-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 42%;
}

.match-grid .card-footer {
  font-size: 0.58rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.grid-card {
  width: 100%;
  min-height: 88px;
  background: rgba(12, 14, 28, 0.55);
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 6px;
  cursor: pointer;
  transition: background 0.25s ease, transform 0.25s ease;
  backdrop-filter: blur(6px);
  border-radius: 8px;
}

.bracket { color: var(--wc-accent-gold); }

@media (max-width: 1200px) {
  .focus-match-display.side-expanded {
    grid-template-columns: minmax(180px, 220px) minmax(240px, 320px) minmax(180px, 220px);
    max-width: 960px;
  }
}

@media (max-width: 1100px) {
  .focus-match-display.side-expanded {
    grid-template-columns: 1fr;
    max-width: 100%;
    padding: 0 12px;
  }

  .focus-center {
    max-width: 100%;
    order: -1;
  }

  .detail-toggle {
    padding: 4px 12px;
    font-size: 12px;
  }
}

@media (max-width: 768px) {
  .dashboard-fullscreen {
    overflow: visible;
    min-height: 0;
  }

  .match-grid-wrap {
    max-height: none;
    overflow: visible;
  }

  .match-grid,
  .match-grid-preview {
    overflow: visible;
    max-height: none;
  }

  .scroll-fade {
    display: none;
  }

  .dashboard-top-stack {
    padding: 8px 8px 0;
    gap: 8px;
  }

  .dashboard-invite-wrap {
    max-width: none;
  }

  .stats-strip {
    flex-direction: row;
    flex-wrap: nowrap;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    scrollbar-width: none;
  }

  .stats-strip::-webkit-scrollbar {
    display: none;
  }

  .stats-group {
    flex-shrink: 0;
  }

  .focus-section {
    padding-top: 8px;
    overflow: visible;
    min-height: auto;
  }

  .focus-section.lineup-open {
    padding-top: 8px;
  }

  .focus-title {
    margin: 0 12px 8px;
    flex-wrap: wrap;
  }

  .focus-match-display {
    margin-top: 0;
    padding: 0 12px;
    max-width: 100%;
  }

  .focus-match-display.side-expanded {
    grid-template-columns: 1fr;
  }

  .focus-actions {
    flex-direction: column;
    width: 100%;
  }

  .focus-actions .cyber-btn,
  .focus-actions .cyber-btn-secondary {
    width: 100%;
    min-height: 44px;
    margin-left: 0 !important;
  }

  .schedule-section {
    padding: 8px 12px calc(var(--wc-bottom-nav-height) + 24px);
  }

  .match-grid-wrap {
    max-height: 200px;
  }

  .match-grid-preview {
    grid-template-columns: 1fr;
  }

  .match-grid-wrap.is-expanded,
  .match-grid-expanded {
    max-height: min(68vh, 640px);
  }

  .expand-btn-text {
    display: inline;
  }

  .mobile-schedule-list {
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding-bottom: env(safe-area-inset-bottom, 0px);
  }

  .ethereal-glow {
    width: 100%;
    height: 400px;
  }
}

@media (max-width: 480px) {
  .match-grid,
  .match-grid-expanded {
    grid-template-columns: 1fr;
  }

  .match-hub {
    grid-template-columns: 1fr;
    gap: 6px;
    text-align: center;
  }

  .hub-team,
  .hub-team--away {
    align-items: center;
    text-align: center;
  }

  .hub-center {
    order: -1;
  }

  .stat-chip {
    font-size: 0.72rem;
  }
}

.grid-card:hover {
  transform: translateY(-2px);
  background: rgba(30, 24, 36, 0.75);
  box-shadow: 0 12px 28px rgba(0, 0, 0, 0.55),
              inset 2px 0 8px rgba(201, 120, 138, 0.25) !important;
}

.card-header {
  display: flex;
  justify-content: space-between;
  font-size: 0.7rem;
  color: #A0A0A0;
}

.card-group { color: #D2A76D; font-weight: bold; }

.card-teams {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 5px;
  font-size: 1rem;
  font-weight: bold;
}

.t-vs { font-size: 0.75rem; color: #A67C41; font-style: italic; }

.card-footer {
  font-size: 0.65rem;
  color: #6e7681;
  text-align: center;
}

.daily-widget {
  cursor: pointer;
}
.daily-widget .w-sub {
  font-size: 0.65rem;
  color: #9a94a8;
  margin-top: 4px;
}
</style>