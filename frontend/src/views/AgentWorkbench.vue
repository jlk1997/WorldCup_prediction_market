<template>

  <div class="agent-page">

    <div class="layout">

      <aside class="history glass-panel" :class="{ 'history-expanded': historyExpanded || !isMobile }">

        <h3 class="history-title" @click="toggleHistory">
          历史分析
          <span v-if="isMobile" class="history-toggle">{{ historyExpanded ? '收起' : '展开' }}</span>
        </h3>

        <el-input
          v-model="historySearch"
          placeholder="搜索球队"
          clearable
          size="small"
          class="history-filter"
          @input="debouncedFetchHistory"
        />

        <el-select
          v-model="historyModeFilter"
          placeholder="全部模式"
          clearable
          size="small"
          class="history-filter"
          @change="fetchHistory"
        >
          <el-option label="赛前" value="pre_match" />
          <el-option label="赛中" value="live" />
          <el-option label="赛后" value="post_match" />
        </el-select>

        <div

          v-for="run in history"

          :key="run.id"

          class="history-item"
          :class="{ disabled: loadingAnalyze }"
          @click="!loadingAnalyze && loadRun(run.id)"

        >

          <div>{{ run.team1 }} vs {{ run.team2 }}</div>

          <div class="sub">{{ modeLabel(run.mode) }} · 置信 {{ run.confidence ? (run.confidence * 100).toFixed(0) + '%' : '-' }}</div>

        </div>

        <el-empty v-if="!history.length" description="暂无记录" />

      </aside>



      <div class="main">

        <div class="selector glass-panel">

          <header class="page-head">
            <h2>AI 多 Agent 分析工作台</h2>
            <p class="mode-desc">{{ modeDescription }}</p>
          </header>

          <el-alert v-if="!authState.accessToken" type="warning" :closable="false" show-icon title="登录后可触发完整 AI 分析">
            未登录仅可浏览历史缓存摘要。请先
            <router-link to="/login">登录</router-link>
          </el-alert>

          <div v-else-if="billingStatus" class="billing-chips">
            <div class="bill-chip">
              <span class="label">今日免费</span>
              <span class="value">{{ billingStatus.free_remaining }}/{{ billingStatus.daily_free_limit }}</span>
            </div>
            <div class="bill-chip">
              <span class="label">余额</span>
              <span class="value gold">{{ billingStatus.fan_coins }} 币</span>
            </div>
            <div class="bill-chip">
              <span class="label">超出后</span>
              <span class="value">赛前 {{ billingStatus.costs.pre_match }} · 赛中 {{ billingStatus.costs.live }}</span>
            </div>
          </div>

          <div v-if="billingPreview && authState.accessToken" class="cost-preview">
            <span class="cost-label">本次预计</span>
            <span v-if="billingPreview.cache_hit" class="cost-value cache">命中缓存 · 不扣币</span>
            <span v-else-if="billingPreview.data.charge_coins === 0" class="cost-value free">
              使用免费额度（剩 {{ billingPreview.data.free_remaining }} 次）
            </span>
            <span v-else class="cost-value paid">扣 {{ billingPreview.data.charge_coins }} 球迷币</span>
          </div>

          <el-alert
            v-if="billingStatus && billingStatus.free_remaining <= 0"
            type="warning"
            :closable="false"
            show-icon
            class="quota-alert"
            title="今日免费 AI 已用完"
          >
            超出后按次扣币；开通通行证每日多 3 次免费。
            <el-button link type="primary" @click="$router.push('/shop')">去商城</el-button>
          </el-alert>

          <AiBillingIntro :visible="showBillingIntro" @ack="ackBilling" />

          <div class="form-row" v-if="authState.accessToken">

            <el-select v-model="team1" filterable placeholder="主队" style="width:160px" :disabled="loadingAnalyze">

              <el-option v-for="t in teamList" :key="t.id" :label="t.name" :value="t.name" />

            </el-select>

            <span>VS</span>

            <el-select v-model="team2" filterable placeholder="客队" style="width:160px" :disabled="loadingAnalyze">

              <el-option v-for="t in teamList" :key="'b'+t.id" :label="t.name" :value="t.name" />

            </el-select>

            <el-select v-model="mode" style="width:120px" :disabled="loadingAnalyze">

              <el-option label="赛前" value="pre_match" />

              <el-option label="赛中" value="live" />

              <el-option label="赛后" value="post_match" />

            </el-select>

            <el-checkbox v-model="forceRefresh" :disabled="loadingAnalyze">强制刷新（额外扣币）</el-checkbox>

            <button type="button" class="run-btn" :disabled="loadingAnalyze || loadingHistory" @click="runAnalysis(false)">
              <span v-if="loadingAnalyze" class="run-loading">分析中…</span>
              <span v-else>启动多 Agent 分析</span>
            </button>

          </div>

          <p v-if="cached" class="cached-tip">本次结果来自缓存，未扣球迷币</p>
          <p v-else-if="lastBilling" class="cached-tip">
            本次消耗 {{ lastBilling.charge_coins ?? 0 }} 球迷币
            <span v-if="lastBilling.used_free_quota">（使用免费额度）</span>
          </p>

        </div>



        <el-alert

          v-if="liveBanner"

          type="info"

          :closable="false"

          show-icon

          class="live-banner"

          :title="liveBanner"

        />



        <div v-if="loadingAnalyze && progressMessage" class="progress-panel glass-panel">

          <div class="progress-head">

            <span class="phase-text">{{ progressLabel }}</span>

            <span class="progress-pct">{{ progressPercent }}%</span>

          </div>

          <el-progress :percentage="progressPercent" :stroke-width="10" :show-text="false" color="var(--wc-accent-gold)" />

          <div class="agent-pipeline">
            <span
              v-for="step in pipelineSteps"
              :key="step.key"
              class="pipe-step"
              :class="{ done: step.done, active: step.active }"
            >
              {{ step.label }}
            </span>
          </div>

          <p v-if="recentSteps.length" class="current-step">
            正在：{{ agentDisplayName(recentSteps[recentSteps.length - 1].agent) }} · {{ recentSteps[recentSteps.length - 1].action }}
          </p>

          <p v-if="waitingHint" class="waiting-hint">{{ waitingHint }}</p>
          <button v-if="loadingAnalyze" type="button" class="cancel-btn" @click="cancelAnalysis">
            停止等待（分析仍在后台进行，已扣费不会自动退还）
          </button>

        </div>



        <TeamCompareBar v-if="team1 && team2" :team1="team1" :team2="team2" />

        <p v-if="streamError" class="stream-error">{{ streamError }}</p>

        <div v-if="report" ref="reportSection" class="report-section">

          <el-alert

            v-if="validationWarnings.length"

            type="warning"

            :closable="false"

            title="准确性校准提示"

            :description="validationWarnings.join('；')"

            show-icon

            class="critic-alert"

          />



          <el-alert

            v-if="report.critic_issues?.length"

            type="warning"

            :closable="false"

            title="需留意的问题"

            :description="report.critic_issues.join('；')"

            show-icon

            class="critic-alert"

          />



          <BettingGuideCard
            v-if="report.betting_guide"
            :team1="team1"
            :team2="team2"
            :guide="report.betting_guide"
            :watch-points="report.watch_points"
            @predict="goPredictFromAi"
          />

          <div class="confidence-bar glass-panel">
            <span>分析可信度</span>
            <el-progress :percentage="Math.round(report.confidence * 100)" :stroke-width="12" />
            <p v-if="report.critic_notes" class="critic-note">{{ report.critic_notes }}</p>
          </div>

          <div class="summary-box glass-panel">
            <h3>比赛看点</h3>
            <p>{{ report.summary }}</p>
            <p v-if="report.scenario_analysis" class="scenario"><strong>若出现意外：</strong>{{ report.scenario_analysis }}</p>
            <KeyFactorsTags :items="report.key_factors" title="影响赛果的关键点" />
          </div>

          <div v-if="report.news_digest" class="news-digest glass-panel">
            <h3>场外舆情</h3>
            <p>{{ report.news_digest }}</p>
          </div>

          <div v-if="report.injury_impact" class="section glass-panel">
            <h3>伤病与阵容</h3>
            <p>{{ report.injury_impact }}</p>
          </div>

          <div v-if="report.tactical_edge || report.tactical_brief?.brief" class="section glass-panel">
            <h3>战术对位</h3>
            <p>{{ report.tactical_edge || report.tactical_brief?.brief }}</p>
            <div v-if="report.tactical_brief?.team1_edge || report.tactical_brief?.team2_edge" class="tactical-edges">
              <p v-if="report.tactical_brief?.team1_edge"><strong>{{ team1 }}：</strong>{{ report.tactical_brief.team1_edge }}</p>
              <p v-if="report.tactical_brief?.team2_edge"><strong>{{ team2 }}：</strong>{{ report.tactical_brief.team2_edge }}</p>
            </div>
            <ul v-if="report.tactical_brief?.key_matchups?.length">
              <li v-for="(m, i) in report.tactical_brief.key_matchups" :key="i">{{ m }}</li>
            </ul>
          </div>

          <el-collapse v-if="reasoningTrace.length" class="steps-collapse glass-panel">
            <el-collapse-item title="查看 AI 分析过程（可选）" name="trace">
              <el-timeline>
                <el-timeline-item
                  v-for="(step, i) in reasoningTrace"
                  :key="i"
                  :timestamp="agentDisplayName(step.agent)"
                  placement="top"
                  :type="agentColor(step.agent)"
                >
                  <strong>{{ step.action }}</strong>
                  <p class="step-summary">{{ step.summary }}</p>
                </el-timeline-item>
              </el-timeline>
            </el-collapse-item>
          </el-collapse>



          <div v-if="report.sources?.length" class="sources glass-panel">

            <h3>数据来源</h3>

            <ul>

              <li v-for="(s, i) in report.sources" :key="i">

                <a v-if="s.url" :href="s.url" target="_blank">{{ s.url }}</a>

                <span v-else>{{ s.type }}: {{ s.ref }}</span>

              </li>

            </ul>

          </div>

        </div>

      </div>

    </div>

  </div>

</template>



<script setup lang="ts">

import { ref, watch, onMounted, onBeforeUnmount, computed, nextTick } from 'vue'
import { fetchRecommendations, profileState } from '@/stores/profileStore'
import { authState } from '@/stores/authStore'

import { useRoute, useRouter, onBeforeRouteLeave } from 'vue-router'

import { ElMessage, ElNotification, ElMessageBox } from 'element-plus'

import { apiClient, getErrorMessage, isRateLimitError } from '@/api/client'
import { showApiError } from '@/utils/errorHandler'
import { usePageMeta } from '@/composables/usePageMeta'
import {
  streamAgentAnalyze,
  getAiBillingStatus,
  getBillingPreview,
  type AgentStreamEvent,
  type AiBillingStatus,
  type BillingPreview,
} from '@/api/agentStream'

import type { AgentReport, LiveMatch, TeamBrief } from '@/types/api'

usePageMeta({
  title: '世界杯 AI 分析 — 赛前 / 赛中解读 | 最后一舞',
  description:
    'AI 多步分析世界杯对阵：战术、伤病、历史交锋与赛果参考。虚拟球迷币消费，仅供娱乐。',
  path: '/agent',
})

import {
  isAnalyzeLockedByOtherTab,
  releaseAnalyzeLock,
  startAnalyzeHeartbeat,
  stopAnalyzeHeartbeat,
  tryAcquireAnalyzeLock,
} from '@/stores/agentAnalyzeStore'

import KeyFactorsTags from '@/components/KeyFactorsTags.vue'

import TeamCompareBar from '@/components/TeamCompareBar.vue'

import BettingGuideCard from '@/components/BettingGuideCard.vue'
import AiBillingIntro from '@/components/AiBillingIntro.vue'
import { useStadiumScene } from '@/composables/useStadiumScene'
import { useBreakpoint } from '@/composables/useBreakpoint'
import { offerStarterPack } from '@/composables/useStarterPackOffer'
import { isWeChatBrowser, WECHAT_PAY_HINT } from '@/utils/payEnv'



interface RunBrief {

  id: number

  team1: string

  team2: string

  mode: string

  confidence: number | null

}



const PHASE_WEIGHT: Record<string, number> = {

  facts: 20,

  llm: 50,

  predict: 80,

  critic: 95,

  done: 100,

}



const route = useRoute()

const router = useRouter()

const { setAnalyzing, setHeatmap } = useStadiumScene()



const teamList = ref<TeamBrief[]>([])

const team1 = ref('')

const team2 = ref('')

const mode = ref('pre_match')

const forceRefresh = ref(false)

const loadingAnalyze = ref(false)
const loadingHistory = ref(false)
const { isMobile } = useBreakpoint()
const historyExpanded = ref(false)

function toggleHistory() {
  if (isMobile.value) historyExpanded.value = !historyExpanded.value
}

const cached = ref(false)

const report = ref<AgentReport | null>(null)
const streamError = ref('')
const waitingHint = ref('')

const history = ref<RunBrief[]>([])
const historySearch = ref('')
const historyModeFilter = ref('')

const validationWarnings = ref<string[]>([])

const analyzeAbort = ref<AbortController | null>(null)

const progressMessage = ref('')

const progressPercent = ref(0)

const recentSteps = ref<{ agent: string; action: string }[]>([])

const liveBanner = ref('')

const reportSection = ref<HTMLElement | null>(null)
const billingStatus = ref<AiBillingStatus | null>(null)
const billingPreview = ref<BillingPreview | null>(null)
const lastBilling = ref<{ charge_coins?: number; used_free_quota?: boolean } | null>(null)

const AI_BILLING_ACK = 'ai_billing_ack'
const showBillingIntro = ref(localStorage.getItem(AI_BILLING_ACK) !== '1')
const currentPhase = ref('facts')



const modeDescription = computed(() => {

  const map: Record<string, string> = {

    pre_match: '赛前分析：综合球队数据、新闻与战术，给出胜平负参考与观赛要点',

    live: '赛中分析：结合实时比分动态调整判断，适合临场竞猜参考',

    post_match: '赛后复盘：回顾关键转折，对照赛前预测做验证',

  }

  return map[mode.value] || map.pre_match

})

const reasoningTrace = computed(() => {
  if (!report.value) return []
  if (report.value.reasoning_trace?.length) return report.value.reasoning_trace
  return (report.value.agent_steps || []).map((s) => ({
    agent: s.agent,
    action: s.action,
    summary: typeof s.output === 'string' ? s.output.slice(0, 200) : '已完成该步骤',
  }))
})

const PHASE_LABELS: Record<string, string> = {
  facts: '收集球队与赛程数据',
  llm: '多 Agent 联合研判',
  predict: '生成胜平负与比分参考',
  critic: '交叉核查与校准',
  done: '分析完成',
}

const progressLabel = computed(() => PHASE_LABELS[currentPhase.value] || progressMessage.value || '正在分析…')

const PIPELINE_ORDER = ['facts', 'llm', 'predict', 'critic', 'done'] as const

const pipelineSteps = computed(() =>
  PIPELINE_ORDER.map((key) => ({
    key,
    label: { facts: '数据', llm: '研判', predict: '结论', critic: '核查', done: '完成' }[key],
    done: PIPELINE_ORDER.indexOf(currentPhase.value as typeof PIPELINE_ORDER[number]) > PIPELINE_ORDER.indexOf(key),
    active: currentPhase.value === key,
  })),
)



function decodeParam(v: string | string[] | null | undefined) {

  if (v == null) return ''

  return decodeURIComponent(String(v))

}



team1.value = decodeParam(route.params.team1 as string) || decodeParam(route.query.team1 as string | undefined)

team2.value = decodeParam(route.params.team2 as string) || decodeParam(route.query.team2 as string | undefined)

const qMode = String(route.query.mode || '')
if (qMode === 'live' || qMode === 'post_match' || qMode === 'pre_match') mode.value = qMode
if (route.query.refresh === '1') forceRefresh.value = true



function modeLabel(m: string) {

  return { pre_match: '赛前', live: '赛中', post_match: '赛后' }[m] || m

}



function agentDisplayName(agent: string) {
  const map: Record<string, string> = {
    DataAgent: '数据',
    NewsAgent: '新闻',
    TacticalAgent: '战术',
    PredictAgent: '综合',
    CriticAgent: '核查',
  }
  return map[agent] || agent
}

function agentColor(agent: string) {

  if (agent === 'CriticAgent') return 'warning'

  if (agent === 'PredictAgent') return 'success'

  if (agent === 'NewsAgent') return 'primary'

  return undefined

}

function applyHeatmap(data: AgentReport) {

  const wp = data.win_probability

  setHeatmap([

    [wp.team1, wp.draw, wp.team2, wp.team1, wp.draw, wp.team2],

    [wp.team1, wp.team1, wp.draw, wp.team2, wp.team2, wp.draw],

    [wp.draw, wp.team1, wp.team2, wp.team1, wp.draw, wp.team2],

    [wp.team2, wp.draw, wp.team1, wp.team2, wp.team1, wp.draw],

  ])

}



function scrollToReport() {
  nextTick(() => {
    reportSection.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  })
}

function goPredictFromAi() {
  void resolvePredictHighlight().then((highlight) => {
    router.push({
      path: '/predict',
      query: highlight ? { highlight } : {},
    })
  })
}

async function resolvePredictHighlight(): Promise<string | undefined> {
  const nm = profileState.recommendations?.next_main_match
  if (nm && nm.team1 === team1.value && nm.team2 === team2.value && nm.id) {
    return String(nm.id)
  }
  if (!team1.value || !team2.value) return undefined
  try {
    const res = await apiClient.get<{ data: LiveMatch[] }>('/api/live/matches')
    const match = res.data.data.find(
      (m) =>
        (m.team1 === team1.value && m.team2 === team2.value) ||
        (m.team1 === team2.value && m.team2 === team1.value),
    )
    return match?.id ? String(match.id) : undefined
  } catch {
    return undefined
  }
}

function notifyDone(wasCached: boolean) {
  ElNotification({
    title: wasCached ? '已加载缓存分析' : 'AI 分析完成',
    message: wasCached ? '结果来自近期缓存，如需最新可勾选强制刷新' : '报告已生成，已自动滚动到结果区',
    type: 'success',
    duration: 3500,
  })
}

function resetProgress() {

  progressMessage.value = '准备启动分析…'

  progressPercent.value = 5

  recentSteps.value = []

  currentPhase.value = 'facts'

}



function handleStreamEvent(event: AgentStreamEvent) {

  if (event.type === 'phase' && event.phase) {

    currentPhase.value = event.phase

    progressMessage.value = event.message || event.phase

    progressPercent.value = PHASE_WEIGHT[event.phase] ?? progressPercent.value

    waitingHint.value = ''

  }

  if (event.type === 'waiting') {

    currentPhase.value = 'llm'

    progressMessage.value = event.message || '排队等待共享分析结果…'

    progressPercent.value = Math.max(progressPercent.value, 15)

    const sec = event.elapsed_sec ?? 0

    const q = event.queue as { active?: number; limit?: number } | undefined

    const queueNote = q && q.active != null && q.limit != null && q.active >= q.limit
      ? ` · 当前 ${q.active}/${q.limit} 路 AI 已满，请稍候`
      : ''

    waitingHint.value = sec > 0
      ? `已等待 ${sec} 秒，请耐心等候…${queueNote}`
      : `其他球迷正在分析同一场，完成后将自动加载${queueNote}`

  }

  if (event.type === 'cached') {

    currentPhase.value = 'done'

    progressMessage.value = event.message || '命中缓存，秒级返回'

    progressPercent.value = 100

    waitingHint.value = ''

  }

  if (event.type === 'step' && event.step) {

    recentSteps.value = [...recentSteps.value.slice(-4), event.step]

    progressPercent.value = Math.min(95, progressPercent.value + 3)

  }

  if (event.type === 'done') {

    currentPhase.value = 'done'

    progressPercent.value = 100

    progressMessage.value = '分析完成'

  }

}

function ackBilling() {
  localStorage.setItem(AI_BILLING_ACK, '1')
  showBillingIntro.value = false
}



async function fetchTeams() {

  try {

    const res = await apiClient.get<TeamBrief[]>('/api/teams')

    teamList.value = res.data

  } catch {

    teamList.value = []

  }

}



async function fetchHistory() {
  try {
    const params = new URLSearchParams({ limit: '20' })
    if (historySearch.value.trim()) params.set('q', historySearch.value.trim())
    if (historyModeFilter.value) params.set('mode', historyModeFilter.value)
    const res = await apiClient.get<{ data: RunBrief[] }>(`/api/agent/runs?${params}`)
    history.value = res.data.data
  } catch {
    history.value = []
  }
}

let historyDebounce: ReturnType<typeof setTimeout> | null = null
function debouncedFetchHistory() {
  if (historyDebounce) clearTimeout(historyDebounce)
  historyDebounce = setTimeout(fetchHistory, 300)
}



async function fetchLiveContext() {

  liveBanner.value = ''

  if (mode.value !== 'live' || !team1.value || !team2.value) return

  try {

    const res = await apiClient.get<{ data: LiveMatch[] }>('/api/live/matches')

    const match = res.data.data.find(

      (m) =>

        (m.team1 === team1.value && m.team2 === team2.value) ||

        (m.team1 === team2.value && m.team2 === team1.value),

    )

    if (match?.is_live || match?.status === 'live') {

      liveBanner.value = `实时上下文：${match.team1} ${match.home_score ?? 0}:${match.away_score ?? 0} ${match.team2} · ${match.minute ?? '-'}' · AI 将据此校准胜率`

    } else if (match) {

      liveBanner.value = `已找到赛程（${match.status}），非进行中比赛时赛中分析仍可用历史态数据`

    } else {

      liveBanner.value = '未找到 live 数据，赛中分析将主要依据球队档案（比分由后台自动同步）'

    }

  } catch {

    liveBanner.value = ''

  }

}



async function loadRun(id: number) {
  if (loadingAnalyze.value) return

  loadingHistory.value = true

  try {

    const res = await apiClient.get<{ data: AgentReport; validation_warnings?: string[] }>(`/api/agent/runs/${id}`)

    report.value = res.data.data

    validationWarnings.value = res.data.validation_warnings || res.data.data.validation_warnings || []

    applyHeatmap(report.value)

    cached.value = true

    scrollToReport()

  } catch (e) {

    showApiError(e)

  } finally {

    loadingHistory.value = false

  }

}



async function loadBillingStatus() {
  if (!authState.accessToken) return
  try {
    billingStatus.value = await getAiBillingStatus()
  } catch {
    billingStatus.value = null
  }
}

async function refreshBillingPreview() {
  if (!authState.accessToken || !team1.value || !team2.value) {
    billingPreview.value = null
    return
  }
  try {
    billingPreview.value = await getBillingPreview({
      team1_name: team1.value,
      team2_name: team2.value,
      mode: mode.value,
      force_refresh: forceRefresh.value,
    })
  } catch {
    billingPreview.value = null
  }
}

function formatAnalyzeError(message: string): string {
  if (/429|过于频繁|Too Many Requests|rate limit/i.test(message)) {
    return 'MiniMax 请求过于频繁，请等待 1～2 分钟后再试'
  }
  if (/相同对阵|正在进行中|排队/i.test(message)) {
    return `${message}（可稍后再试，或换一场对阵）`
  }
  return message
}

function cancelAnalysis() {
  analyzeAbort.value?.abort()
  loadingAnalyze.value = false
  setAnalyzing(false)
  stopAnalyzeHeartbeat()
  releaseAnalyzeLock()
  progressMessage.value = ''
  waitingHint.value = ''
  streamError.value = '已取消等待；若分析已在后台完成，可在左侧历史记录中查看'
}

async function runAnalysis(fromAuto = false) {
  if (loadingAnalyze.value) return
  if (!authState.accessToken) {
    ElMessage.warning('请先登录后再使用 AI 分析')
    router.push('/login')
    return
  }
  if (showBillingIntro.value) {
    ElMessage.warning('请先阅读上方说明并点击「我知道了，继续分析」')
    document.querySelector('.billing-intro')?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    return
  }

  if (!team1.value || !team2.value) {

    ElMessage.warning('请选择两支球队')

    return

  }

  if (isAnalyzeLockedByOtherTab()) {
    ElMessage.warning('其他浏览器标签页正在分析，请等待完成后再试')
    return
  }
  if (!tryAcquireAnalyzeLock()) {
    ElMessage.warning('已有分析任务进行中，请勿重复提交')
    return
  }

  loadingAnalyze.value = true

  setAnalyzing(true)
  startAnalyzeHeartbeat()

  streamError.value = ''
  waitingHint.value = ''

  const previousReport = report.value
  if (!fromAuto) report.value = null

  cached.value = false

  validationWarnings.value = []

  resetProgress()

  analyzeAbort.value = new AbortController()

  try {

    const res = await streamAgentAnalyze(

      {

        team1_name: team1.value,

        team2_name: team2.value,

        mode: mode.value,

        force_refresh: forceRefresh.value,

      },

      handleStreamEvent,

      analyzeAbort.value.signal,

    )

    report.value = res.data

    cached.value = res.cached

    lastBilling.value = (res as { billing?: { charge_coins?: number; used_free_quota?: boolean } }).billing || null

    validationWarnings.value = res.validation_warnings || res.data.validation_warnings || []

    applyHeatmap(report.value)

    await fetchHistory()

    await loadBillingStatus()

    scrollToReport()

    notifyDone(res.cached)

    router.replace({

      path: `/agent/${encodeURIComponent(team1.value)}/${encodeURIComponent(team2.value)}`,

      query: mode.value === 'live' ? { mode: 'live' } : undefined,

    })

  } catch (e) {
    if (e instanceof DOMException && e.name === 'AbortError') {
      return
    }
    if (isRateLimitError(e) && e.notified) {
      streamError.value = getErrorMessage(e)
      return
    }
    const msg = formatAnalyzeError(getErrorMessage(e))
    streamError.value = msg
    if (!report.value && previousReport) {
      report.value = previousReport
    }
    ElMessage.error(msg)
    if (/免费 AI|余额不足|球迷币不足|次数已用完/.test(msg)) {
      if (isWeChatBrowser()) {
        void ElMessageBox.alert(WECHAT_PAY_HINT, '请用浏览器打开', { confirmButtonText: '我知道了', type: 'warning' })
      }
      void offerStarterPack({
        reason: 'ai_billing',
        onNavigate: (path, query) => router.push({ path, query }),
      })
    }

  } finally {

    loadingAnalyze.value = false
    analyzeAbort.value = null

    setAnalyzing(false)
    stopAnalyzeHeartbeat()
    releaseAnalyzeLock()

    progressMessage.value = ''
    waitingHint.value = ''

  }

}



watch([team1, team2, mode], fetchLiveContext)

watch([team1, team2, mode, forceRefresh], refreshBillingPreview)



watch(() => route.params, (p) => {

  if (p.team1) team1.value = decodeParam(p.team1)

  if (p.team2) team2.value = decodeParam(p.team2)

})



onBeforeRouteLeave((_to, _from, next) => {
  if (!loadingAnalyze.value) {
    next()
    return
  }
  const leave = window.confirm('AI 分析仍在进行，离开页面不会取消分析，已扣费也不会自动退还。确定离开？')
  if (leave) {
    analyzeAbort.value?.abort()
    next()
  } else {
    next(false)
  }
})

onBeforeUnmount(() => {
  analyzeAbort.value?.abort()
  stopAnalyzeHeartbeat()
  releaseAnalyzeLock()
})

onMounted(async () => {

  await Promise.all([fetchTeams(), fetchHistory(), fetchLiveContext(), loadBillingStatus()])
  await refreshBillingPreview()

  if (authState.accessToken && !team1.value && !team2.value) {
    try {
      await fetchRecommendations()
      const nm = profileState.recommendations?.next_main_match
      if (nm?.team1 && nm?.team2) {
        team1.value = nm.team1
        team2.value = nm.team2
      }
    } catch {
      /* ignore */
    }
  }

  if (team1.value && team2.value && route.query.auto === '1') {

    await runAnalysis(true)

  }

})

</script>



<style scoped>
.agent-page { padding: 16px 20px 24px; max-width: 1200px; margin: 0 auto; min-height: min-content; background: transparent; }
.page-head h2 {
  margin: 0 0 6px;
  font-size: 1.75rem;
  font-weight: 800;
  font-family: var(--wc-font-serif);
  background: linear-gradient(135deg, #f0d9b5 0%, var(--wc-accent-gold) 50%, var(--wc-accent-rose) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
.mode-desc { color: rgba(255, 255, 255, 0.68); font-size: 0.88rem; margin: 0; line-height: 1.5; }
.billing-chips {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  margin-top: 14px;
}
@media (max-width: 640px) {
  .billing-chips { grid-template-columns: 1fr; }
}
.bill-chip {
  padding: 10px 12px;
  border-radius: 10px;
  background: rgba(12, 14, 28, 0.55);
  border: 1px solid rgba(255, 255, 255, 0.08);
}
.bill-chip .label {
  display: block;
  font-size: 0.72rem;
  color: rgba(255, 255, 255, 0.55);
  margin-bottom: 2px;
}
.bill-chip .value {
  font-size: 0.92rem;
  font-weight: 700;
  color: #f5f0e8;
}
.bill-chip .value.gold { color: var(--wc-accent-gold); }
.cost-preview {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 12px;
  padding: 10px 14px;
  border-radius: 10px;
  background: rgba(212, 165, 116, 0.08);
  border: 1px solid rgba(212, 165, 116, 0.22);
}
.cost-label { font-size: 0.82rem; color: rgba(255, 255, 255, 0.6); }
.cost-value { font-size: 0.88rem; font-weight: 700; }
.cost-value.cache { color: #8fd48a; }
.cost-value.free { color: var(--wc-accent-gold); }
.cost-value.paid { color: #f0a0b0; }
.run-btn {
  min-width: 168px;
  padding: 10px 20px;
  border: none;
  border-radius: 10px;
  font-size: 0.92rem;
  font-weight: 800;
  color: #1a1208;
  cursor: pointer;
  background: linear-gradient(135deg, #f0d9b5 0%, var(--wc-accent-gold) 100%);
  box-shadow: 0 2px 14px rgba(212, 165, 116, 0.4);
}
.run-btn:disabled { opacity: 0.65; cursor: not-allowed; }
.run-btn:not(:disabled):hover { filter: brightness(1.06); transform: translateY(-1px); }
.layout { display: grid; grid-template-columns: 240px 1fr; gap: 20px; }
.history { padding: 12px; max-height: 80vh; overflow-y: auto; }
.history-filter { width: 100%; margin-bottom: 8px; }
.history-item { padding: 10px; border-bottom: 1px dashed rgba(139, 41, 66, 0.35); cursor: pointer; font-size: 0.85rem; }
.history-item:hover { background: rgba(212, 165, 116, 0.08); }
.history-item .sub { color: #6e7681; font-size: 0.75rem; margin-top: 4px; }
.selector { padding: 20px 22px; margin-bottom: 16px; }
.form-row { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; margin-top: 14px; }
.cached-tip { color: rgba(255, 255, 255, 0.55); font-size: 0.8rem; margin-top: 8px; }
.live-banner { margin-bottom: 12px; }
.progress-panel { padding: 16px 20px; margin-bottom: 16px; }
.progress-head { display: flex; justify-content: space-between; margin-bottom: 10px; font-size: 0.92rem; }
.phase-text { color: #f0d9b5; font-weight: 600; }
.progress-pct { color: var(--wc-accent-gold); font-weight: 700; }
.agent-pipeline {
  display: flex;
  gap: 8px;
  margin-top: 14px;
  flex-wrap: wrap;
}
.pipe-step {
  padding: 4px 12px;
  border-radius: 999px;
  font-size: 0.78rem;
  color: rgba(255, 255, 255, 0.45);
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.1);
}
.pipe-step.done {
  color: #8fd48a;
  border-color: rgba(103, 194, 58, 0.35);
  background: rgba(103, 194, 58, 0.1);
}
.pipe-step.active {
  color: #1a1208;
  font-weight: 700;
  border-color: var(--wc-accent-gold);
  background: linear-gradient(135deg, #f0d9b5, var(--wc-accent-gold));
}
.current-step {
  margin: 12px 0 0;
  font-size: 0.82rem;
  color: rgba(255, 255, 255, 0.65);
}
.critic-alert { margin-bottom: 16px; }
.confidence-bar { padding: 16px; margin-bottom: 16px; }
.critic-note { font-size: 0.8rem; color: #909399; margin-top: 8px; }
.summary-box, .steps-collapse, .sources, .news-digest, .section { padding: 16px 20px; margin-bottom: 16px; }
.scenario { margin-top: 10px; color: #b1bac4; font-size: 0.9rem; }
.tactical-edges p { font-size: 0.88rem; color: #c9d1d9; margin: 6px 0; }
.step-summary { font-size: 0.85rem; color: #8b949e; margin: 6px 0 0; line-height: 1.5; }
.news-digest p { line-height: 1.6; color: #c9d1d9; }
.steps-collapse :deep(.el-collapse-item__header) { color: #8b949e; font-size: 0.88rem; }
.history-item.disabled { opacity: 0.45; pointer-events: none; cursor: not-allowed; }
.waiting-hint {
  margin: 10px 0 0;
  font-size: 0.82rem;
  color: var(--wc-accent-gold);
}
.stream-error {
  margin: 0 0 12px;
  padding: 10px 14px;
  border-radius: 10px;
  font-size: 0.85rem;
  color: #f89898;
  background: rgba(245, 108, 108, 0.12);
  border: 1px solid rgba(245, 108, 108, 0.35);
}
.cancel-btn {
  margin-top: 10px;
  padding: 6px 12px;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  background: transparent;
  color: rgba(255, 255, 255, 0.65);
  font-size: 0.78rem;
  cursor: pointer;
}
.cancel-btn:hover { border-color: rgba(255, 255, 255, 0.35); color: #fff; }

@media (max-width: 900px) {
  .layout { grid-template-columns: 1fr; }
  .agent-page { padding: 16px; }
  .history { max-height: 220px; }
  .form-row { flex-direction: column; align-items: stretch; }
  .form-row .el-select { width: 100%; min-height: 44px; }
  .run-btn { width: 100%; min-height: 44px; }
  .summary-box, .steps-collapse, .sources, .news-digest, .section { padding: 12px 14px; }
  .section :deep(pre), .section :deep(code) { overflow-x: auto; max-width: 100%; }
}

@media (max-width: 768px) {
  .history:not(.history-expanded) {
    max-height: 52px;
    overflow: hidden;
  }
  .history.history-expanded {
    max-height: 280px;
    overflow-y: auto;
  }
  .history-title {
    cursor: pointer;
    display: flex;
    justify-content: space-between;
    align-items: center;
    user-select: none;
  }
  .history-toggle {
    font-size: 0.75rem;
    color: var(--wc-accent-gold);
    font-weight: 600;
  }
}

@media (max-width: 480px) {
  .agent-page { padding: 12px; }
}
</style>


