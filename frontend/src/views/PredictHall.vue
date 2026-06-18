<template>

  <div class="predict-hall mobile-page">

    <div class="header glass-panel">

      <header class="page-head">
        <div class="head-row">
          <div>
            <h1>竞猜大厅</h1>
            <p class="subtitle">猜中得累计积分冲榜 · 同时获得可用积分去兑换装扮 · 质押用球迷币</p>
          </div>
          <el-button class="guide-btn" plain size="small" @click="openGameplayGuide">玩法说明</el-button>
        </div>
      </header>

      <div v-if="authState.user" class="balance-grid">
        <div class="balance-chip" :class="{ 'coin-pulse': coinPulse }">
          <span class="chip-label">球迷币</span>
          <span class="chip-value gold">{{ authState.user.fan_coins }}</span>
          <button type="button" class="chip-action" @click="$router.push('/shop')">充值</button>
        </div>
        <div class="balance-chip">
          <span class="chip-label">累计积分</span>
          <span class="chip-value">{{ authState.user.season_points }}</span>
        </div>
        <div class="balance-chip highlight">
          <span class="chip-label">可用积分</span>
          <span class="chip-value rose">{{ authState.user.redeem_points ?? 0 }}</span>
          <button type="button" class="chip-action primary" @click="$router.push({ path: '/shop', query: { tab: 'redeem' } })">
            兑换
          </button>
        </div>
      </div>

      <DailyRitualPanel
        v-if="dailyStatus"
        :status="dailyStatus"
        show-signin
        :signing="signingIn"
        @signin="doSignin"
      />

      <CollectibleHookBanner v-if="authState.user" :signin-streak="dailyStatus?.signin_streak ?? 0" />

      <el-alert v-else-if="authState.user" title="加载每日任务…" type="info" show-icon :closable="false" />

      <GuestLoginBanner v-else />

    </div>



    <details class="predict-extras" :open="extrasExpanded">
      <summary class="predict-extras-summary">
        <span>每日任务 · 成长推荐</span>
        <span class="predict-extras-toggle">{{ extrasExpanded ? '收起' : '展开' }}</span>
      </summary>
      <div class="predict-extras-body">

    <StreakRiskBanner :status="dailyStatus" />

    <GrowthPrimaryCard :status="dailyStatus" />

    <MatchDayShareBar v-if="dailyStatus?.match_day && dailyStatus?.activation_segment === 'active'" :status="dailyStatus" />

    <OfficialQqGroupBar
      :match-day="!!dailyStatus?.match_day"
      :today-signin-count="dailyStatus?.today_signin_count ?? 0"
    />

    <InvitePromptBar
      v-if="authState.user && !showGrowthFocus"
      scene="predict"
      :match-day="!!dailyStatus?.match_day"
    />

    <PredictFirstCoach v-if="authState.user && activeMatches.length" />

    <el-alert
      v-if="showProfileBindHint"
      type="warning"
      show-icon
      closable
      class="profile-bind-hint"
      title="选主队解锁更多玩法"
      @close="dismissProfileBindHint"
    >
      完善档案后，主队比赛会高亮显示，还能解锁军团、比赛日签到 +10 币。
      <el-button link type="primary" @click="$router.push('/onboarding')">去建档</el-button>
    </el-alert>

    <PassDailyClaimBar :status="dailyStatus" @refresh="refreshDailyStatus" />

    <div v-if="passBenefitsLine" class="pass-value-bar glass-inner">
      {{ passBenefitsLine }}
      <button type="button" class="pass-link" @click="$router.push('/shop')">查看权益</button>
    </div>

    <FanRecommendationsBar v-if="!showGrowthFocus" :daily-status="dailyStatus" />

    <div
      v-if="dailyStatus?.pending_predictions && dailyStatus.next_pending_match"
      class="pending-banner glass-panel"
      role="button"
      tabindex="0"
      @click="$router.push('/me')"
      @keydown.enter="$router.push('/me')"
    >
      ⏳ {{ dailyStatus.pending_predictions }} 场待开奖
      <span> · 比赛结束后约 1–3 分钟内自动开奖</span>
      <span v-if="dailyStatus.next_pending_match?.label">
        · 最近「{{ dailyStatus.next_pending_match.label }}」
      </span>
      <span class="pending-link">去个人中心查看 →</span>
    </div>

      </div>
    </details>

    <section class="match-list" id="predict-matches">
      <div class="match-list-head">
        <h2 class="match-list-title">可竞猜比赛</h2>
        <span v-if="activeMatches.length" class="match-list-count">{{ activeMatches.length }} 场</span>
      </div>

      <div v-if="loading && !matches.length" class="match-skeletons">
        <div v-for="n in 4" :key="n" class="skeleton-card glass-panel">
          <div class="sk-line sk-title" />
          <div class="sk-line sk-meta" />
          <div class="sk-row">
            <div class="sk-pill" />
            <div class="sk-pill" />
            <div class="sk-pill" />
          </div>
          <div class="sk-line sk-action" />
        </div>
      </div>

      <div v-else-if="activeMatches.length" class="match-cards-stack">
        <div
          v-for="m in activeMatches"
          :key="m.id"
          class="match-card glass-panel"
          :data-match-id="m.id"
          :class="{
            highlight: m.is_main_team || m.id === highlightId,
            predicted: m.user_predicted,
            'raise-success-card': raiseSuccessId === m.id,
          }"
          @mouseenter="onCardFocus(m.id)"
        >

            <div class="badges">

              <span v-if="m.user_predicted" class="badge done">已参与</span>

              <span v-if="m.is_main_team" class="badge main">我的主队</span>

              <span v-else-if="m.is_sub_team" class="badge sub">副队</span>

              <span v-if="m.has_star_player" class="badge star">你的球星在阵</span>

            </div>

            <div class="teams">{{ m.team1 }} vs {{ m.team2 }}</div>

            <div class="meta">{{ m.group }} · {{ m.date }} {{ m.time }}</div>

            <template v-if="m.user_predicted">

              <div class="predicted-info">

                你已选择：<strong>{{ pickLabel(m, m.user_pick) }}</strong>

                <span v-if="m.user_prediction_status === 'pending'"> · 待开奖</span>

                <span v-else-if="m.user_prediction_status === 'won'" class="won-tag"> · 已猜中</span>

                <span v-else-if="m.user_prediction_status === 'lost'" class="lost-tag"> · 未猜中</span>

                <span v-else-if="m.user_prediction_status === 'void'" class="void-tag"> · 流局</span>

              </div>

              <div class="predicted-stake">
                <span v-if="m.user_is_free" class="stake-tag free">免费竞猜</span>
                <span
                  v-else
                  class="stake-tag paid"
                  :class="{ 'stake-flash': stakeFlashId === m.id }"
                >
                  已质押 {{ m.user_stake_coins ?? 0 }} 球迷币
                </span>
              </div>

              <div
                v-if="canRaiseStake(m)"
                class="raise-row"
                :class="{ 'raise-row-success': raiseSuccessId === m.id }"
              >
                <p class="raise-hint">可在截止前追加质押，提高猜中返币（总额上限 500 币）</p>
                <div class="raise-controls">
                  <el-input-number
                    v-model="raiseAmounts[m.id]"
                    :min="10"
                    :max="raiseMax(m)"
                    size="small"
                    class="raise-input"
                  />
                  <el-button
                    :type="raiseSuccessId === m.id ? 'success' : 'primary'"
                    size="small"
                    class="raise-btn"
                    :loading="raisingId === m.id"
                    :disabled="!authState.user || raisingId === m.id"
                    @click="raiseStake(m.id)"
                  >
                    {{ raiseSuccessId === m.id ? '追加成功 ✓' : '追加质押' }}
                  </el-button>
                </div>
                <p v-if="raiseSuccessText[m.id]" class="raise-success">{{ raiseSuccessText[m.id] }}</p>
                <p v-if="raiseErrors[m.id]" class="submit-error">{{ raiseErrors[m.id] }}</p>
              </div>

              <p v-else-if="m.user_prediction_status === 'pending' && m.user_is_free" class="hint muted">
                免费竞猜不可追加质押；下一场可质押球迷币参与
              </p>

            </template>

            <template v-else>

              <div class="pick-row" :data-coach="isFirstOpenMatch(m) ? 'pick' : undefined">

                <el-radio-group v-model="picks[m.id]" size="small" @change="updatePreview(m.id)">

                  <el-radio-button value="home">{{ m.team1 }} 胜</el-radio-button>

                  <el-radio-button value="draw">平局</el-radio-button>

                  <el-radio-button value="away">{{ m.team2 }} 胜</el-radio-button>

                </el-radio-group>

              </div>

              <div v-if="m.pick_stats?.total" class="pick-stats">
                大众选项 · 主 {{ m.pick_stats.distribution.home?.pct ?? 0 }}%
                · 平 {{ m.pick_stats.distribution.draw?.pct ?? 0 }}%
                · 客 {{ m.pick_stats.distribution.away?.pct ?? 0 }}%
              </div>

              <div v-if="previewText[m.id]" class="roi-preview">
                <span class="roi-icon">🎯</span>
                {{ previewText[m.id] }}
              </div>

              <div class="stake-row">

                <el-checkbox
                  v-model="useFree[m.id]"
                  :disabled="freeRemaining <= 0"
                  :data-coach="isFirstOpenMatch(m) ? 'free' : undefined"
                  @change="onStakeChange(m.id)"
                >
                  使用今日免费竞猜
                  <span v-if="freeRemaining <= 0" class="free-used-tag">（今日已用完）</span>
                  <span v-else class="free-left-tag">（剩余 {{ freeRemaining }} 次）</span>
                </el-checkbox>

                <el-input-number

                  v-if="!useFree[m.id]"

                  v-model="stakes[m.id]"

                  :min="10"

                  :max="500"

                  size="small"

                  style="width: 120px"

                  :disabled="!authState.user?.profile_completed"

                  @change="onStakeChange(m.id)"
                />

                <el-button

                  type="primary"

                  class="submit-btn"
                  :data-coach="isFirstOpenMatch(m) ? 'submit' : undefined"

                  :disabled="!authState.user || submittingId === m.id"

                  :loading="submittingId === m.id"

                  @click="submit(m.id)"

                >

                  提交竞猜

                </el-button>

              </div>

              <div
                v-if="!useFree[m.id] && isInsufficientCoins(m.id)"
                class="coin-hint"
              >
                <span class="coin-hint-text">
                  本局需质押 <strong>{{ stakes[m.id] }}</strong> 币，你目前有
                  <strong>{{ fanCoins }}</strong> 币，还差
                  <strong>{{ coinShortfall(m.id) }}</strong> 币
                </span>
                <button type="button" class="coin-hint-action" @click="goRecharge(coinShortfall(m.id))">
                  去充值
                </button>
                <span v-if="freeRemaining > 0" class="coin-hint-alt">或勾选上方免费竞猜</span>
                <span v-else class="coin-hint-alt">或调低质押金额</span>
              </div>

              <div v-else-if="submitErrors[m.id]" class="submit-error">
                <span>{{ submitErrors[m.id] }}</span>
                <button
                  v-if="isCoinRelatedError(submitErrors[m.id])"
                  type="button"
                  class="coin-hint-action inline"
                  @click="goRecharge(coinShortfall(m.id))"
                >
                  去充值球迷币
                </button>
              </div>

              <p v-if="!useFree[m.id] && !authState.user?.profile_completed" class="hint">

                完善球迷档案后可质押竞猜

              </p>

            </template>

            <div class="cheer-row">

              <button
                v-if="m.can_cheer && authState.user?.profile_completed"
                type="button"
                class="cheer-link"
                @click="$router.push(`/cheer/${m.id}`)"
              >
                📣 去助威
              </button>

              <button
                v-if="authState.user"
                type="button"
                class="share-match-link"
                @click="shareMatchInvite(m)"
              >
                邀友猜这场
              </button>

            </div>

          </div>
      </div>

      <details v-if="historyMatches.length" class="history-matches glass-panel">
        <summary>已结束 / 不可竞猜（{{ historyMatches.length }} 场）</summary>
        <div v-for="m in historyMatches" :key="m.id" class="history-match-row">
          <span class="history-label">{{ m.team1 }} vs {{ m.team2 }}</span>
          <span v-if="m.user_predicted" class="history-tag">已参与</span>
          <span class="history-meta">{{ m.date }} {{ m.time }}</span>
        </div>
      </details>

      <el-empty v-else-if="!loading && !activeMatches.length">
        <template #description>
          <p>暂无可竞猜比赛</p>
          <p class="empty-hint">{{ emptyStateHint }}</p>
        </template>
        <el-button v-if="nextMainMatchId" type="primary" @click="goMainMatch">
          猜主队 {{ nextMainMatchLabel }}
        </el-button>
        <el-button type="primary" plain @click="$router.push('/live')">看 Live 赛程</el-button>
        <el-button v-if="!dailyStatus?.signed_today && authState.user" plain @click="doSignin">签到领币</el-button>
        <el-button v-else plain @click="$router.push('/me')">球迷中心</el-button>
      </el-empty>

    </section>

    <WinFeedBar
      :items="winFeed"
      :recent-count="winFeedRecentCount"
      variant="compact"
      :highlight-match-id="profileState.recommendations?.next_main_match?.id ?? null"
    />

  </div>

</template>



<script setup lang="ts">

import { computed, onMounted, onUnmounted, ref, shallowReactive, watch } from 'vue'

import { useRoute, useRouter } from 'vue-router'

import { ElMessage, ElNotification } from 'element-plus'

import { authState, fetchMe } from '../stores/authStore'

import { fetchRecommendations, profileState } from '../stores/profileStore'

import { getPredictableMatches, submitPrediction, raisePredictionStake, getWinFeed, signin, type GameMatch } from '../api/commerce'

import { calcPredictPreview, formatPredictPreviewText } from '../utils/predictPreview'

import { getErrorMessage, isRateLimitError } from '../api/client'
import { showApiError } from '../utils/errorHandler'

import FanRecommendationsBar from '../components/FanRecommendationsBar.vue'
import DailyRitualPanel from '../components/DailyRitualPanel.vue'
import InvitePromptBar from '../components/InvitePromptBar.vue'
import PredictFirstCoach from '../components/PredictFirstCoach.vue'
import GrowthPrimaryCard from '../components/GrowthPrimaryCard.vue'
import MatchDayShareBar from '../components/MatchDayShareBar.vue'
import { fetchDailyStatus, useDailyStatusRef } from '../stores/dailyStatusStore'
import { usePredictHighlightScroll } from '../composables/usePredictHighlightScroll'
import { isMatchPredictable } from '../utils/matchKickoff'
import PassDailyClaimBar from '../components/PassDailyClaimBar.vue'
import { useBreakpoint } from '../composables/useBreakpoint'
import { useInviteShare } from '../composables/useInviteShare'
import { openPredictShareSheet } from '../composables/usePredictShareSheet'
import { openGuideModalByKey, tryAutoOpenGuide } from '../composables/useGuideModal'
import { syncQqGroupClaimed } from '../composables/useOfficialQqGroup'
import { usePageMeta } from '../composables/usePageMeta'
import { trackEvent } from '../utils/analytics'
import { copyToClipboard } from '../utils/copyToClipboard'
import { passBenefitsSummary, offerStarterPack } from '../composables/useStarterPackOffer'
import OfficialQqGroupBar from '../components/OfficialQqGroupBar.vue'
import GuestLoginBanner from '../components/GuestLoginBanner.vue'
import StreakRiskBanner from '../components/StreakRiskBanner.vue'
import WinFeedBar from '../components/WinFeedBar.vue'
import CollectibleHookBanner from '../components/collectible/CollectibleHookBanner.vue'
import { openCollectibleReveal } from '../stores/collectibleRevealStore'
import type { CollectibleDropResult } from '../api/collectible'

usePageMeta({
  title: '竞猜大厅 — 最后一舞',
  description: '2026 世界杯娱乐竞猜，使用虚拟球迷币，不可提现。',
  path: '/predict',
  noIndex: true,
})


const route = useRoute()
const router = useRouter()
const { isMobile } = useBreakpoint()
const { openShareSheet, cachedMe, ensureMe } = useInviteShare()

const extrasExpanded = ref(true)
watch(
  isMobile,
  (mob) => {
    extrasExpanded.value = mob
  },
  { immediate: true },
)

const passBenefitsLine = computed(() => passBenefitsSummary(dailyStatus.value?.pass_benefits ?? null))

const PROFILE_BIND_HINT_KEY = 'wc_skip_profile_predict_hint'

const showProfileBindHint = computed(
  () =>
    !!authState.user &&
    !authState.user.profile_completed &&
    !localStorage.getItem(PROFILE_BIND_HINT_KEY),
)

function dismissProfileBindHint() {
  try {
    localStorage.setItem(PROFILE_BIND_HINT_KEY, '1')
  } catch {
    /* ignore */
  }
}

function siteBase() {
  return (import.meta.env.VITE_SITE_URL || window.location.origin).replace(/\/$/, '')
}

function pickLabelForShare(m: GameMatch, pick: string) {
  if (pick === 'home') return `${m.team1} 胜`
  if (pick === 'away') return `${m.team2} 胜`
  return '平局'
}

function openPredictShareForMatch(m: GameMatch, pick: string) {
  const label = pickLabelForShare(m, pick)
  openPredictShareSheet({
    team1: m.team1 || '?',
    team2: m.team2 || '?',
    pickLabel: label,
    shareUrl: buildPredictShareText(m, pick).split('\n').pop() || '',
    nickname: authState.user?.nickname,
  })
}
function buildPredictShareText(m: GameMatch, pick: string) {
  const label = pickLabelForShare(m, pick)
  const ref = cachedMe.value?.invite_code
  const url = ref
    ? `${siteBase()}/share/match/${m.id}?ref=${encodeURIComponent(ref)}`
    : `${siteBase()}/share/match/${m.id}`
  return `我押了 ${m.team1} vs ${m.team2} · ${label}\n${url}`
}

async function shareMatchInvite(m: GameMatch) {
  const pick = picks[m.id] || 'home'
  const text = buildPredictShareText(m, pick)
  const ok = await copyToClipboard(text)
  if (ok) ElMessage.success('已复制，去微信粘贴邀友猜这场')
  else ElMessage.info(text)
  trackEvent('share_match_invite', { match_id: m.id })
}

function openGameplayGuide() {
  void openGuideModalByKey('gameplay_guide')
}

function maybeOpenGameplayGuide() {
  void tryAutoOpenGuide('gameplay_guide', route.path, route.query as Record<string, unknown>)
}

const PREDICT_SHARE_NUDGE_KEY = 'wc2026_predict_share_nudge'

function shouldShowPredictShareNudge() {
  try {
    const raw = sessionStorage.getItem(PREDICT_SHARE_NUDGE_KEY)
    if (!raw) return true
    return Date.now() - Number(raw) > 86400_000
  } catch {
    return true
  }
}

function markPredictShareNudge() {
  try {
    sessionStorage.setItem(PREDICT_SHARE_NUDGE_KEY, String(Date.now()))
  } catch {
    /* ignore */
  }
}


const matches = ref<GameMatch[]>([])

const loading = ref(false)

const picks = shallowReactive<Record<number, string>>({})

const stakes = shallowReactive<Record<number, number>>({})

const useFree = shallowReactive<Record<number, boolean>>({})

const submitErrors = shallowReactive<Record<number, string>>({})
const raiseErrors = shallowReactive<Record<number, string>>({})
const raiseSuccessText = shallowReactive<Record<number, string>>({})
const raiseAmounts = shallowReactive<Record<number, number>>({})

const submittingId = ref<number | null>(null)
const raisingId = ref<number | null>(null)
const stakeFlashId = ref<number | null>(null)
const raiseSuccessId = ref<number | null>(null)
const coinPulse = ref(false)
let raiseFeedbackTimer: ReturnType<typeof setTimeout> | null = null

const dailyStatus = useDailyStatusRef()

const showGrowthFocus = computed(() => {
  const seg = dailyStatus.value?.activation_segment
  return seg === 'never_predicted' || seg === 'profile_only' || seg === 'one_and_done'
})

async function refreshDailyStatus() {
  await fetchDailyStatus(true)
  window.dispatchEvent(new CustomEvent('daily-status-refresh'))
}

const signingIn = ref(false)
const previewText = shallowReactive<Record<number, string>>({})
const winFeed = ref<{ nickname: string; team1: string; team2: string; points_awarded: number }[]>([])
const winFeedRecentCount = ref(0)
const activePreviewId = ref<number | null>(null)

const highlightId = computed(

  () =>

    Number(route.query.highlight) ||

    profileState.recommendations?.next_main_match?.id ||

    null

)

const nextMainMatch = computed(() => profileState.recommendations?.next_main_match ?? null)

const nextMainMatchId = computed(() => nextMainMatch.value?.id ?? null)

const nextMainMatchLabel = computed(() => {
  const m = nextMainMatch.value
  if (!m?.team1 || !m?.team2) return '下一场'
  return `${m.team1} vs ${m.team2}`
})

const emptyStateHint = computed(() => {
  if (nextMainMatch.value && !dailyStatus.value?.signed_today) {
    return '今日可先签到领币；主队比赛开猜后会出现在这里'
  }
  if (nextMainMatch.value) {
    return '主队比赛尚未开猜，可先完成签到问答或去 Live 看赛程'
  }
  return '可以先去 Live 看赛程，或完成今日签到问答'
})

function goMainMatch() {
  const id = nextMainMatchId.value
  if (id) router.push({ path: '/predict', query: { highlight: String(id) } })
  else router.push('/live')
}



const sortedMatches = computed(() => {

  const list = [...matches.value]

  list.sort((a, b) => {

    const score = (m: GameMatch) =>

      (m.is_main_team ? 100 : 0) + (m.is_sub_team ? 50 : 0) + (m.has_star_player ? 25 : 0)

    return score(b) - score(a)

  })

  return list

})

const activeMatches = computed(() =>
  sortedMatches.value.filter((m) => {
    if (m.can_predict === false) return false
    return isMatchPredictable({ date: m.date, time: m.time })
  }),
)

const historyMatches = computed(() =>
  sortedMatches.value.filter((m) => !activeMatches.value.some((a) => a.id === m.id)),
)

function isFirstOpenMatch(m: GameMatch) {
  const first = activeMatches.value.find((x) => !x.user_predicted)
  return first?.id === m.id
}



const highlightScrollIndex = computed(() => {
  const id = highlightId.value
  if (!id) return null
  const idx = activeMatches.value.findIndex((m) => m.id === id)
  return idx >= 0 ? idx : null
})

const { scrollToHighlight } = usePredictHighlightScroll(highlightId, highlightScrollIndex)

function onPredictScrollHighlight() {
  void scrollToHighlight()
}

const freeRemaining = computed(() => dailyStatus.value?.free_predict.remaining ?? 0)
const fanCoins = computed(() => authState.user?.fan_coins ?? 0)

function isInsufficientCoins(matchId: number): boolean {
  if (useFree[matchId]) return false
  const stake = stakes[matchId] ?? 0
  return stake > fanCoins.value
}

function coinShortfall(matchId: number): number {
  return Math.max(0, (stakes[matchId] ?? 0) - fanCoins.value)
}

function isCoinRelatedError(message: string): boolean {
  return /球迷币不足|余额不足|币不够/.test(message)
}

function goRecharge(shortfall?: number) {
  void offerStarterPack({
    reason: 'predict_stake',
    shortfall,
    onNavigate: (path, query) => router.push({ path, query }),
  })
}

function onStakeChange(matchId: number) {
  if (isInsufficientCoins(matchId)) {
    delete submitErrors[matchId]
  }
  updatePreview(matchId)
}

function syncFreeCheckboxDefaults() {
  const left = freeRemaining.value
  for (const m of matches.value) {
    if (m.user_predicted) continue
    if (left <= 0) useFree[m.id] = false
    else if (useFree[m.id] === undefined) useFree[m.id] = true
  }
}

watch(freeRemaining, (left) => {
  if (left <= 0) {
    for (const m of matches.value) {
      if (!m.user_predicted) useFree[m.id] = false
    }
  }
})



function pickLabel(m: GameMatch, pick: string | null | undefined) {

  if (pick === 'home') return `${m.team1} 胜`

  if (pick === 'away') return `${m.team2} 胜`

  if (pick === 'draw') return '平局'

  return pick || '—'

}

const STAKE_MAX = 500

function canRaiseStake(m: GameMatch): boolean {
  return (
    !!m.user_predicted &&
    m.user_prediction_status === 'pending' &&
    !m.user_is_free &&
    !!authState.user?.profile_completed
  )
}

function raiseMax(m: GameMatch): number {
  const current = m.user_stake_coins ?? 0
  return Math.max(10, STAKE_MAX - current)
}

function showRaiseFeedback(matchId: number, amount: number, newTotal: number) {
  if (raiseFeedbackTimer) clearTimeout(raiseFeedbackTimer)
  stakeFlashId.value = matchId
  raiseSuccessId.value = matchId
  raiseSuccessText[matchId] = `+${amount} 球迷币 · 当前共 ${newTotal} 币`
  coinPulse.value = true
  raiseFeedbackTimer = setTimeout(() => {
    stakeFlashId.value = null
    raiseSuccessId.value = null
    delete raiseSuccessText[matchId]
    coinPulse.value = false
    raiseFeedbackTimer = null
  }, 3200)
}

async function raiseStake(matchId: number) {
  delete raiseErrors[matchId]
  delete raiseSuccessText[matchId]
  const amount = raiseAmounts[matchId] ?? 10
  const m = matches.value.find((x) => x.id === matchId)
  if (!m || !canRaiseStake(m)) return
  if (amount > raiseMax(m)) {
    raiseErrors[matchId] = `最多还可追加 ${raiseMax(m)} 币`
    return
  }
  if (amount > fanCoins.value) {
    raiseErrors[matchId] = `球迷币不足，还差 ${amount - fanCoins.value} 币`
    return
  }
  raisingId.value = matchId
  try {
    await raisePredictionStake(matchId, amount)
    const newTotal = (m.user_stake_coins ?? 0) + amount
    m.user_stake_coins = newTotal
    await fetchMe()
    showRaiseFeedback(matchId, amount, newTotal)
    ElMessage.success({
      message: `追加成功 · 已质押 ${newTotal} 球迷币`,
      duration: 2800,
      showClose: true,
    })
    await load({ silent: true })
  } catch (e) {
    showApiError(e)
    if (isRateLimitError(e) && e.notified) return
    const msg = getErrorMessage(e)
    raiseErrors[matchId] = msg
    if (isCoinRelatedError(msg)) {
      notifyPredictError(`${msg}，可去充值`, { soft: true })
    } else {
      notifyPredictError(msg, { soft: true })
    }
  } finally {
    raisingId.value = null
  }
}

async function doSignin() {
  if (signingIn.value) return
  signingIn.value = true
  try {
    const res = await signin()
    await fetchMe()
    await fetchDailyStatus(true)
    syncQqGroupClaimed(dailyStatus.value?.qq_group_claimed)
    ElMessage.success(`签到成功 +${res.added} 币${res.streak_bonus ? ` · 连签奖励 +${res.streak_bonus}` : ''}`)
    const drop = res.collectible_drop as CollectibleDropResult | null | undefined
    if (drop?.dropped) {
      openCollectibleReveal(drop, {
        subtitle: res.signin_streak && [3, 7, 14].includes(res.signin_streak)
          ? `连签 ${res.signin_streak} 天里程碑奖励`
          : '签到掉落',
      })
    }
  } catch (e) {
    showApiError(e)
  } finally {
    signingIn.value = false
  }
}

function updatePreview(matchId: number) {
  if (!authState.user) return
  const pick = picks[matchId]
  if (!pick) return
  const w = calcPredictPreview(authState.user, pick, useFree[matchId] ? 0 : stakes[matchId], useFree[matchId], {
    lossStreak: dailyStatus.value?.loss_streak,
    lossProtectAfter: dailyStatus.value?.loss_streak_protect_after,
    lossMultiplier: dailyStatus.value?.loss_streak_multiplier,
  })
  previewText[matchId] = formatPredictPreviewText(w)
}

async function load(options: { silent?: boolean } = {}) {
  if (!options.silent) loading.value = true

  try {

    if (authState.accessToken) {

      await fetchMe()

      await fetchRecommendations()

      await fetchDailyStatus(true)
      syncQqGroupClaimed(dailyStatus.value?.qq_group_claimed)

    }

    matches.value = await getPredictableMatches()
    const res = await getWinFeed().catch(() => ({ items: [], recent_count: 0 }))
    winFeed.value = res.items
    winFeedRecentCount.value = res.recent_count

    for (const m of matches.value) {
      if (!m.user_predicted) {
        picks[m.id] = picks[m.id] ?? 'home'
        stakes[m.id] = stakes[m.id] ?? 10
      } else if (canRaiseStake(m)) {
        raiseAmounts[m.id] = raiseAmounts[m.id] ?? 10
      }
    }
    syncFreeCheckboxDefaults()
    for (const m of matches.value) {
      if (!m.user_predicted) updatePreview(m.id)
    }
  } catch (e) {
    showApiError(e)

  } finally {

    if (!options.silent) loading.value = false

  }

}

watch(
  () => {
    const id = activePreviewId.value
    if (id == null) return null
    return `${picks[id]}|${stakes[id]}|${useFree[id]}|${authState.user?.win_streak}`
  },
  () => {
    if (activePreviewId.value != null) updatePreview(activePreviewId.value)
  }
)

function onCardFocus(matchId: number) {
  activePreviewId.value = matchId
  updatePreview(matchId)
}



function notifyPredictError(message: string, options: { soft?: boolean } = {}) {
  if (options.soft) {
    ElMessage.warning({ message, duration: 4500, showClose: true })
    return
  }
  ElMessage.error({ message, duration: 5000, showClose: true })
  ElNotification.error({
    title: '竞猜提交失败',
    message,
    duration: 6000,
    position: 'top-right',
  })
}

async function submit(matchId: number) {
  delete submitErrors[matchId]
  const free = !!useFree[matchId]
  if (free && freeRemaining.value <= 0) {
    useFree[matchId] = false
    const msg = '今日免费竞猜次数已用完，请取消勾选或改用球迷币质押'
    submitErrors[matchId] = msg
    notifyPredictError(msg)
    return
  }
  if (!picks[matchId]) {
    const msg = '请先选择胜/平/负'
    submitErrors[matchId] = msg
    ElMessage.warning(msg)
    return
  }
  if (!free && isInsufficientCoins(matchId)) {
    const need = stakes[matchId] ?? 0
    const shortfall = coinShortfall(matchId)
    notifyPredictError(
      `球迷币还差 ${shortfall} 币（本局 ${need} 币 · 当前 ${fanCoins.value} 币），可去充值或调低质押`,
      { soft: true },
    )
    trackEvent('starter_pack_trigger', { match_id: matchId, shortfall })
    void offerStarterPack({
      reason: 'predict_stake',
      shortfall,
      onNavigate: (path, query) => router.push({ path, query }),
    })
    return
  }
  submittingId.value = matchId
  const submittedPick = picks[matchId]
  const matchRow = matches.value.find((x) => x.id === matchId)
  try {
    await submitPrediction({
      match_id: matchId,
      pick: submittedPick,
      stake_coins: free ? 0 : stakes[matchId],
      use_free: free,
    })
    await fetchMe()
    trackEvent('first_predict_submit', {
      match_id: matchId,
      use_free: free,
      has_profile: !!authState.user?.profile_completed,
    })
    const msg = free ? '免费竞猜已提交，猜中得积分！' : `已质押 ${stakes[matchId]} 币，祝你好运！`
    ElMessage.success(msg)
    if (matchRow && submittedPick) {
      openPredictShareForMatch(matchRow, submittedPick)
    }
    delete submitErrors[matchId]
    await fetchDailyStatus(true)
    const total = dailyStatus.value?.predict_count_total ?? 0
    if (total === 1) {
      window.dispatchEvent(new CustomEvent('second-predict-coach'))
      const nextPath =
        dailyStatus.value?.activation_nudge?.path ||
        dailyStatus.value?.next_action?.path ||
        '/predict'
      ElNotification({
        title: '首猜完成',
        message: '再猜一场 · 养成习惯 · 离兑换更近',
        type: 'success',
        duration: 8000,
        onClick: () => router.push(nextPath.startsWith('/') ? nextPath : '/predict'),
      })
    } else if (authState.user && shouldShowPredictShareNudge()) {
      markPredictShareNudge()
      ElNotification({
        title: '竞猜已提交',
        message: '点此通知 · 邀球友一起猜，双方都能得球迷币',
        type: 'success',
        duration: 6000,
        onClick: () => openShareSheet(),
      })
    }
    await load({ silent: true })
  } catch (e) {
    showApiError(e)
    if (isRateLimitError(e) && e.notified) return
    const msg = getErrorMessage(e)
    submitErrors[matchId] = msg
    if (msg.includes('已竞猜过')) {
      notifyPredictError('您已参与本场竞猜，卡片已更新为「已参与」状态', { soft: true })
      await load({ silent: true })
      return
    }
    if (isCoinRelatedError(msg)) {
      notifyPredictError(`${msg}，可去充值或调低质押`, { soft: true })
    } else {
      notifyPredictError(msg)
    }
    if (msg.includes('免费竞猜')) {
      useFree[matchId] = false
      await fetchDailyStatus(true)
      syncFreeCheckboxDefaults()
    }
  } finally {
    submittingId.value = null
  }
}



onMounted(() => {
  void load().then(() => scrollToHighlight())
  void ensureMe()
  maybeOpenGameplayGuide()
  window.addEventListener('predict-scroll-highlight', onPredictScrollHighlight)
})

onUnmounted(() => {
  window.removeEventListener('predict-scroll-highlight', onPredictScrollHighlight)
  if (raiseFeedbackTimer) clearTimeout(raiseFeedbackTimer)
})

watch(highlightId, () => {
  void scrollToHighlight()
})

watch(
  () => activeMatches.value.length,
  () => {
    void scrollToHighlight()
  },
)

watch(
  () => [route.path, route.query.guide] as const,
  () => {
    maybeOpenGameplayGuide()
  },
)

</script>



<style scoped>

.profile-bind-hint {
  margin-bottom: 12px;
}

.pass-value-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  margin-bottom: 12px;
  border-radius: 10px;
  font-size: 0.85rem;
  color: var(--wc-accent-gold, #d4a574);
}

.pass-link {
  background: none;
  border: none;
  color: var(--wc-accent-rose, #e8a0bf);
  cursor: pointer;
  font-size: inherit;
  text-decoration: underline;
  padding: 0;
}

.share-match-link {
  background: none;
  border: none;
  color: var(--wc-accent-gold, #d4a574);
  cursor: pointer;
  font-size: 0.82rem;
  padding: 0;
  margin-left: 12px;
}

.win-feed .feed-item {
  background: none;
  border: none;
  color: inherit;
  cursor: pointer;
  padding: 0;
  font-family: inherit;
  font-size: inherit;
}

.win-feed .feed-label {
  display: block;
  font-size: 0.78rem;
  font-weight: 700;
  color: var(--wc-accent-gold, #d4a574);
  margin-bottom: 6px;
}

.predict-hall {

  max-width: 960px;

  margin: 0 auto;

  background: transparent;

  width: 100%;

  height: auto;

  min-height: unset;

  overflow: visible;

}

@media (min-width: 769px) {
  .predict-hall {
    padding: 16px 20px 32px;
    max-width: 1080px;
  }
}

.predict-extras {
  margin-bottom: 16px;
  border-radius: 12px;
  border: 1px solid rgba(212, 165, 116, 0.18);
  background: rgba(255, 255, 255, 0.02);
}

.predict-extras-summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 16px;
  cursor: pointer;
  font-size: 0.85rem;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.82);
  list-style: none;
  user-select: none;
}

.predict-extras-summary::-webkit-details-marker {
  display: none;
}

.predict-extras-toggle {
  font-size: 0.75rem;
  color: var(--wc-accent-gold, #d4a574);
}

.predict-extras-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 0 12px 12px;
}

.match-list {
  position: relative;
  width: 100%;
  overflow: visible;
  scroll-margin-top: 88px;
}

.match-list-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
  padding: 0 4px;
}

.match-list-title {
  margin: 0;
  font-size: 1.05rem;
  font-weight: 700;
  color: var(--wc-gold, #d4a574);
}

.match-list-count {
  font-size: 0.78rem;
  color: var(--wc-text-muted);
  padding: 3px 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.06);
}

.page-head h1 {
  margin: 0 0 6px;
  font-size: 1.75rem;
  font-weight: 800;
  font-family: var(--wc-font-serif);
  background: linear-gradient(135deg, #f0d9b5 0%, var(--wc-accent-gold) 50%, var(--wc-accent-rose) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.head-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.guide-btn {
  flex-shrink: 0;
  margin-top: 4px;
}

.subtitle {
  margin: 0;
  font-size: 0.88rem;
  color: rgba(255, 255, 255, 0.68);
  line-height: 1.5;
}

.header {

  padding: 20px 22px;

  margin-bottom: 16px;

  flex-shrink: 0;

}

.next-match-card {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 14px 16px;
  margin-bottom: 12px;
  cursor: pointer;
  border: 1px solid rgba(212, 165, 116, 0.35);
  transition: border-color 0.15s ease;
}

.next-match-card:hover {
  border-color: rgba(212, 165, 116, 0.55);
}

.next-match-tag {
  font-size: 0.72rem;
  color: var(--wc-accent-gold, #d4a574);
}

.next-match-card strong {
  font-size: 0.95rem;
  color: #f5f0e8;
}

.next-match-hint {
  font-size: 0.78rem;
  color: var(--wc-text-muted);
}

.history-matches {
  margin-top: 12px;
  padding: 12px 16px;
}

.history-matches summary {
  cursor: pointer;
  font-size: 0.85rem;
  color: var(--wc-text-muted);
  user-select: none;
}

.history-match-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  padding: 10px 0;
  border-bottom: 1px dashed rgba(255, 255, 255, 0.08);
  font-size: 0.82rem;
}

.history-match-row:last-child {
  border-bottom: none;
}

.history-label {
  flex: 1;
  min-width: 0;
  color: rgba(255, 255, 255, 0.55);
}

.history-tag {
  font-size: 0.7rem;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  color: var(--wc-text-muted);
}

.history-meta {
  font-size: 0.72rem;
  color: rgba(255, 255, 255, 0.35);
}

.balance-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  margin-top: 16px;
}

@media (max-width: 640px) {
  .balance-grid {
    grid-template-columns: 1fr;
  }
}

.balance-chip {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 12px 14px;
  border-radius: 12px;
  background: rgba(12, 14, 28, 0.55);
  border: 1px solid rgba(255, 255, 255, 0.08);
  min-height: 88px;
}

.balance-chip.highlight {
  border-color: rgba(201, 120, 138, 0.35);
  background: rgba(201, 120, 138, 0.08);
}

.chip-label {
  font-size: 0.72rem;
  color: rgba(255, 255, 255, 0.55);
}

.chip-value {
  font-size: 1.35rem;
  font-weight: 800;
  color: #f5f0e8;
  line-height: 1.2;
}

.chip-value.gold {
  color: var(--wc-accent-gold);
}

.chip-value.rose {
  color: var(--wc-accent-rose);
}

.chip-action {
  align-self: flex-start;
  margin-top: 4px;
  padding: 4px 12px;
  border-radius: 8px;
  border: 1px solid rgba(212, 165, 116, 0.35);
  background: rgba(212, 165, 116, 0.1);
  color: var(--wc-accent-gold);
  font-size: 0.78rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s, border-color 0.2s;
}

.chip-action:hover {
  background: rgba(212, 165, 116, 0.2);
  border-color: var(--wc-accent-gold);
}

.chip-action.primary {
  border-color: rgba(201, 120, 138, 0.45);
  background: rgba(201, 120, 138, 0.12);
  color: #f0a0b0;
}

.chip-action.primary:hover {
  background: rgba(201, 120, 138, 0.22);
}

.daily-hud {
  display: none;
}

.pending-banner {
  padding: 10px 16px;
  margin-bottom: 12px;
  font-size: 13px;
  cursor: pointer;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  transition: background 0.2s;
}

.pending-banner:hover {
  background: rgba(212, 165, 116, 0.08);
}

.pending-link {
  margin-left: auto;
  color: var(--wc-accent-gold, #d4a574);
  font-size: 12px;
}

.empty-hint {
  font-size: 13px;
  color: var(--wc-text-muted, #9a94a8);
  margin-top: 4px;
}

.pick-stats {
  font-size: 12px;
  color: var(--wc-text-muted, #9a94a8);
  margin: 6px 0;
}

.roi-preview {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 10px 0 8px;
  padding: 8px 12px;
  border-radius: 10px;
  font-size: 0.82rem;
  font-weight: 600;
  color: #8fd48a;
  background: rgba(103, 194, 58, 0.1);
  border: 1px solid rgba(103, 194, 58, 0.28);
  line-height: 1.45;
}

.roi-icon {
  flex-shrink: 0;
  font-size: 0.95rem;
}

.match-cards-stack {
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow: visible;
}

.win-feed {
  margin-top: 16px;
  padding: 10px;
  overflow: hidden;
  flex-shrink: 0;
}

.feed-track {
  display: flex;
  gap: 24px;
  animation: scroll-feed 40s linear infinite;
  white-space: nowrap;
}

.feed-item {
  font-size: 13px;
  color: var(--wc-text-muted, #9a94a8);
}

@keyframes scroll-feed {
  from { transform: translateX(0); }
  to { transform: translateX(-50%); }
}

.match-skeletons {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 0 4px;
  animation: skeleton-fade 0.3s ease;
}

.skeleton-card {
  padding: 16px 20px;
  margin: 0 4px 8px;
  box-sizing: border-box;
}

.sk-line,
.sk-pill {
  border-radius: 8px;
  background: linear-gradient(
    90deg,
    rgba(255, 255, 255, 0.04) 0%,
    rgba(212, 165, 116, 0.12) 50%,
    rgba(255, 255, 255, 0.04) 100%
  );
  background-size: 200% 100%;
  animation: skeleton-shimmer 1.4s ease-in-out infinite;
}

.sk-title {
  height: 18px;
  width: 55%;
  margin-bottom: 10px;
}

.sk-meta {
  height: 12px;
  width: 38%;
  margin-bottom: 14px;
}

.sk-row {
  display: flex;
  gap: 8px;
  margin-bottom: 14px;
}

.sk-pill {
  height: 28px;
  flex: 1;
  border-radius: 14px;
}

.sk-action {
  height: 32px;
  width: 42%;
}

@keyframes skeleton-shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

@keyframes skeleton-fade {
  from { opacity: 0.4; }
  to { opacity: 1; }
}

.match-card {

  padding: 16px 18px 14px;

  margin: 0 4px 10px;

  position: relative;

  box-sizing: border-box;

  min-height: 268px;

}

.match-card.highlight {

  border: 1px solid rgba(212, 165, 116, 0.45);

  box-shadow: 0 0 20px rgba(212, 165, 116, 0.12);

  animation: highlightGlow 2.2s ease-in-out 2;

}

@keyframes highlightGlow {
  0%, 100% { box-shadow: 0 0 12px rgba(212, 165, 116, 0.1); }
  50% { box-shadow: 0 0 24px rgba(212, 165, 116, 0.28); }
}

.match-card.predicted {

  opacity: 0.92;

  border: 1px solid rgba(100, 180, 120, 0.35);

}

.badges {

  display: flex;

  flex-wrap: wrap;

  gap: 6px;

  margin-bottom: 8px;

}

.badge {

  font-size: 0.72rem;

  padding: 2px 8px;

  border-radius: 10px;

  font-weight: 600;

}

.badge.main { color: var(--wc-accent-gold); background: rgba(212,165,116,0.15); }

.badge.sub { color: var(--wc-text-muted); background: rgba(255,255,255,0.06); }

.badge.star { color: #c9788a; background: rgba(201,120,138,0.15); }

.badge.done { color: #6ec99a; background: rgba(110,201,154,0.15); }

.teams {

  font-size: 1.1rem;

  font-weight: 600;

}

.meta {

  color: var(--wc-text-muted);

  font-size: 0.85rem;

  margin: 6px 0 12px;

}

.predicted-info {

  margin-top: 8px;

  font-size: 0.95rem;

  color: var(--wc-text-muted);

}

.predicted-stake {
  margin-top: 6px;
}

.stake-tag {
  display: inline-block;
  font-size: 0.78rem;
  padding: 3px 10px;
  border-radius: 8px;
  font-weight: 600;
}

.stake-tag.free {
  color: #8fd48a;
  background: rgba(103, 194, 58, 0.12);
}

.stake-tag.paid {
  color: var(--wc-accent-gold);
  background: rgba(212, 165, 116, 0.12);
  transition: transform 0.25s ease, box-shadow 0.25s ease, background 0.25s ease;
}

.stake-tag.stake-flash {
  animation: stakePulse 0.65s ease 2;
  background: rgba(103, 194, 58, 0.22);
  color: #8fd48a;
  box-shadow: 0 0 0 2px rgba(103, 194, 58, 0.35);
}

@keyframes stakePulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.06); }
}

.balance-chip.coin-pulse .chip-value.gold {
  animation: coinPulse 0.55s ease 2;
}

@keyframes coinPulse {
  0%, 100% { transform: scale(1); color: var(--wc-accent-gold); }
  50% { transform: scale(1.12); color: #8fd48a; }
}

.won-tag { color: #8fd48a; }
.lost-tag { color: #f89898; }
.void-tag { color: #79bbff; }
.lost-tag { color: #f89898; }

.raise-row {
  margin-top: 12px;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px dashed rgba(212, 165, 116, 0.35);
  background: rgba(212, 165, 116, 0.06);
  transition: border-color 0.3s ease, background 0.3s ease;
}

.raise-row-success {
  border-color: rgba(103, 194, 58, 0.55);
  background: rgba(103, 194, 58, 0.1);
}

.raise-success {
  margin: 8px 0 0;
  padding: 6px 10px;
  border-radius: 8px;
  font-size: 0.8rem;
  font-weight: 600;
  color: #8fd48a;
  background: rgba(103, 194, 58, 0.12);
  animation: raiseFadeIn 0.35s ease;
}

@keyframes raiseFadeIn {
  from { opacity: 0; transform: translateY(-4px); }
  to { opacity: 1; transform: translateY(0); }
}

.raise-input {
  width: 120px;
}

.raise-btn {
  min-width: 96px;
  font-weight: 700;
}

.match-card.raise-success-card {
  border-color: rgba(103, 194, 58, 0.4);
  box-shadow: 0 0 18px rgba(103, 194, 58, 0.12);
}

.raise-hint {
  margin: 0 0 8px;
  font-size: 0.78rem;
  color: var(--wc-text-muted);
  line-height: 1.45;
}

.raise-controls {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}

.hint.muted {
  font-size: 0.78rem;
  color: var(--wc-text-muted);
  margin-top: 8px;
}

.pick-row, .stake-row, .cheer-row {

  display: flex;

  flex-wrap: wrap;

  align-items: center;

  gap: 10px;

  margin-top: 8px;

}

.stake-row {
  margin-top: 10px;
}

.submit-btn {
  min-width: 108px;
  font-weight: 700;
}

.cheer-row {
  margin-top: 6px;
  min-height: 24px;
}

.cheer-link {
  padding: 0;
  border: none;
  background: none;
  color: var(--wc-accent-gold);
  font-size: 0.82rem;
  font-weight: 600;
  cursor: pointer;
}

.cheer-link:hover {
  text-decoration: underline;
}

.hint {

  font-size: 0.8rem;

  color: var(--wc-text-muted);

  margin-top: 8px;

}

.free-used-tag {
  color: #f89898;
  font-size: 0.75rem;
}

.free-left-tag {
  color: var(--wc-accent-gold);
  font-size: 0.75rem;
}

.submit-error {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 12px;
  margin: 8px 0 0;
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 0.82rem;
  color: #f89898;
  background: rgba(245, 108, 108, 0.12);
  border: 1px solid rgba(245, 108, 108, 0.35);
}

.coin-hint {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 10px;
  margin: 8px 0 0;
  padding: 9px 12px;
  border-radius: 10px;
  font-size: 0.82rem;
  color: rgba(255, 240, 210, 0.88);
  background: rgba(212, 165, 116, 0.1);
  border: 1px solid rgba(212, 165, 116, 0.28);
  line-height: 1.45;
}

.coin-hint-text strong {
  color: var(--wc-accent-gold);
  font-weight: 700;
}

.coin-hint-alt {
  font-size: 0.78rem;
  color: rgba(255, 255, 255, 0.5);
}

.coin-hint-action {
  padding: 4px 12px;
  border-radius: 8px;
  border: 1px solid rgba(212, 165, 116, 0.45);
  background: rgba(212, 165, 116, 0.16);
  color: var(--wc-accent-gold);
  font-size: 0.78rem;
  font-weight: 700;
  cursor: pointer;
  transition: background 0.2s, border-color 0.2s;
}

.coin-hint-action:hover {
  background: rgba(212, 165, 116, 0.28);
  border-color: var(--wc-accent-gold);
}

.coin-hint-action.inline {
  margin-left: auto;
}

@media (min-width: 960px) {
  .predict-extras:not([open]) .predict-extras-body {
    display: none;
  }

  .match-card {
    min-height: 0;
  }
}

@media (max-width: 768px) {
  .predict-hall {
    max-width: 100%;
    min-height: auto;
  }

  .header {
    padding: 14px 16px;
  }

  .page-head h1 {
    font-size: 1.35rem;
  }

  .balance-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .pick-row :deep(.el-radio-group) {
    display: flex;
    flex-direction: column;
    width: 100%;
  }

  .pick-row :deep(.el-radio-button) {
    width: 100%;
  }

  .pick-row :deep(.el-radio-button__inner) {
    width: 100%;
    min-height: 44px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 8px !important;
    margin-bottom: 6px;
  }

  .stake-row {
    flex-direction: column;
    align-items: stretch;
  }

  .stake-row .el-input-number {
    width: 100% !important;
  }

  .submit-btn {
    width: 100%;
    min-height: 44px;
    min-width: 0;
  }

  .raise-controls {
    flex-direction: column;
    align-items: stretch;
  }

  .raise-input {
    width: 100% !important;
  }

  .raise-btn {
    width: 100%;
    min-height: 44px;
  }

  .match-card {
    min-height: 0;
  }
}

@media (max-width: 480px) {
  .balance-grid {
    grid-template-columns: 1fr;
  }
}

</style>


