<template>
  <div class="user-center mobile-page" v-loading="authState.loading">
    <header class="page-header">
      <h1>球迷中心</h1>
      <p v-if="profileStatus?.main_team">⚽ {{ profileStatus.main_team.name }} 球迷 · 2026 世界杯</p>
    </header>

    <el-tabs
      v-model="activeTab"
      class="uc-tabs"
      :stretch="isMobile"
      @tab-change="onTabChange"
    >
      <el-tab-pane label="概览" name="overview">
        <UserCenterOverview
          v-if="authState.user"
          :user="authState.user"
          :profile-status="profileStatus"
          :daily-status="dailyStatus"
          :quiz="quiz"
          :quiz-load-failed="quizLoadFailed"
          :focus-key="routeFocus"
          :signing="signing"
          :pass-active="passActive"
          :pass-expired="passExpired"
          :referral-unread="referralUnread"
          :invite-summary="inviteSummary"
          @signin="doSignin"
          @answer-quiz="answerQuiz"
          @reload-quiz="reloadQuiz"
          @go-tab="switchTab"
        />
      </el-tab-pane>

      <el-tab-pane label="记录" name="records" lazy>
        <UserCenterRecords
          v-if="recordsLoaded"
          :predictions="predictions"
          :coin-ledger="ledger"
          :season-point-ledger="seasonPointLedger"
          :redeem-point-ledger="redeemPointLedger"
          :redeem-orders="redeemOrders"
          :focus-key="routeFocus"
        />
        <div v-else class="tab-loading" v-loading="recordsLoading" />
      </el-tab-pane>

      <el-tab-pane label="权益" name="entitlements">
        <UserEntitlementsPanel
          v-if="authState.user"
          id="entitlements"
          :user="authState.user"
        />
      </el-tab-pane>

      <el-tab-pane label="设置" name="settings">
        <UserCenterSettings
          :loading="nickLoading"
          @change-nickname="changeNickname"
          @logout="handleLogout"
        />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import UserCenterOverview from '../components/user-center/UserCenterOverview.vue'
import UserCenterRecords from '../components/user-center/UserCenterRecords.vue'
import UserCenterSettings from '../components/user-center/UserCenterSettings.vue'
import UserEntitlementsPanel from '../components/UserEntitlementsPanel.vue'
import { authState, fetchMe, logout } from '../stores/authStore'
import { fetchProfileStatus, profileState } from '../stores/profileStore'
import {
  updateProfile,
  getMyPredictions,
  signin,
  getWalletLedger,
  getPointLedger,
  getRedeemOrders,
  getDailyStatus,
  type GamePrediction,
  type CoinLedgerEntry,
  type PointLedgerEntry,
  type RedeemOrder,
  type DailyStatus,
} from '../api/commerce'
import { getQuizToday, answerQuiz as submitQuizAnswer } from '../api/profile'
import { usePageMeta } from '../composables/usePageMeta'

usePageMeta({
  title: '球迷中心 — 最后一舞',
  description: '个人档案、签到、竞猜记录与球迷币流水。',
  path: '/me',
  noIndex: true,
})

import { getUnreadNotificationCount } from '../api/notifications'
import { getReferralMe, type ReferralMe } from '../api/referral'
import { showApiError } from '../utils/errorHandler'
import { scrollMeFocus } from '../utils/dailyActionNav'
import { openCollectibleReveal } from '../stores/collectibleRevealStore'
import type { CollectibleDropResult } from '../api/collectible'
import { useBreakpoint } from '../composables/useBreakpoint'
import { hasActiveSeasonPass } from '../utils/entitlements'

const VALID_TABS = ['overview', 'records', 'entitlements', 'settings'] as const
type TabName = (typeof VALID_TABS)[number]

const { isMobile } = useBreakpoint()
const route = useRoute()
const router = useRouter()

const activeTab = ref<TabName>('overview')
const predictions = ref<GamePrediction[]>([])
const ledger = ref<CoinLedgerEntry[]>([])
const seasonPointLedger = ref<PointLedgerEntry[]>([])
const redeemPointLedger = ref<PointLedgerEntry[]>([])
const redeemOrders = ref<RedeemOrder[]>([])
const nickLoading = ref(false)
const signing = ref(false)
const dailyStatus = ref<DailyStatus | null>(null)
const quiz = ref<Record<string, unknown> | null>(null)
const quizLoadFailed = ref(false)
const referralUnread = ref(0)
const inviteSummary = ref<Pick<ReferralMe, 'effective_invites' | 'season_coins_earned' | 'next_tier'> | null>(null)
const recordsLoaded = ref(false)
const recordsLoading = ref(false)

const profileStatus = computed(() => profileState.status)
const passActive = computed(() => hasActiveSeasonPass(authState.user))
const passExpired = computed(() => !!authState.user?.has_season_pass && !passActive.value)

const routeFocus = computed(() => {
  const focus = route.query.focus
  return typeof focus === 'string' ? focus : null
})

function resolveTabFromRoute(): TabName {
  if (route.hash === '#entitlements') return 'entitlements'
  const tab = route.query.tab
  if (typeof tab === 'string' && VALID_TABS.includes(tab as TabName)) {
    return tab as TabName
  }
  if (routeFocus.value) return 'overview'
  return 'overview'
}

function syncRouteTab(tab: TabName) {
  const query = { ...route.query }
  if (tab === 'overview' && !routeFocus.value) {
    delete query.tab
  } else if (tab !== 'overview') {
    query.tab = tab
  }
  router.replace({ path: '/me', query, hash: route.hash || undefined })
}

function switchTab(tab: string) {
  if (VALID_TABS.includes(tab as TabName)) {
    activeTab.value = tab as TabName
  }
}

function onTabChange(name: string | number) {
  const tab = String(name) as TabName
  syncRouteTab(tab)
  if (tab === 'records') void ensureRecordsLoaded()
  if (tab === 'records') startPredictPollIfNeeded()
  else stopPredictPoll()
}

async function loadCore() {
  const [, , dailyRes, quizRes] = await Promise.all([
    fetchMe(),
    fetchProfileStatus(true),
    getDailyStatus().catch(() => null),
    getQuizToday().catch(() => null),
  ])
  dailyStatus.value = dailyRes
  if (quizRes) {
    quiz.value = quizRes as Record<string, unknown>
    quizLoadFailed.value = false
  } else {
    quiz.value = null
    quizLoadFailed.value = true
  }
}

async function loadRecords() {
  recordsLoading.value = true
  try {
    const [preds, wallet, seasonPts, redeemPts, orders] = await Promise.all([
      getMyPredictions(),
      getWalletLedger(30),
      getPointLedger('season', 30),
      getPointLedger('redeem', 30),
      getRedeemOrders(),
    ])
    predictions.value = preds
    ledger.value = wallet
    seasonPointLedger.value = seasonPts
    redeemPointLedger.value = redeemPts
    redeemOrders.value = orders
    recordsLoaded.value = true
  } catch {
    predictions.value = []
    ledger.value = []
    seasonPointLedger.value = []
    redeemPointLedger.value = []
    redeemOrders.value = []
    recordsLoaded.value = true
  } finally {
    recordsLoading.value = false
  }
}

async function ensureRecordsLoaded() {
  if (recordsLoaded.value || recordsLoading.value) return
  await loadRecords()
}

async function refreshPredictions() {
  try {
    predictions.value = await getMyPredictions()
  } catch {
    /* ignore */
  }
}

async function reloadRecordsLedgers() {
  if (!recordsLoaded.value) return
  try {
    const [wallet, seasonPts, redeemPts, orders] = await Promise.all([
      getWalletLedger(30),
      getPointLedger('season', 30),
      getPointLedger('redeem', 30),
      getRedeemOrders(),
    ])
    ledger.value = wallet
    seasonPointLedger.value = seasonPts
    redeemPointLedger.value = redeemPts
    redeemOrders.value = orders
  } catch {
    /* ignore */
  }
}

async function changeNickname(name: string) {
  if (!name) {
    ElMessage.warning('请输入新昵称')
    return
  }
  nickLoading.value = true
  try {
    await updateProfile({ nickname: name })
    await fetchMe()
    ElMessage.success('昵称已更新，已扣除 20 球迷币')
  } catch (e) {
    showApiError(e)
  } finally {
    nickLoading.value = false
  }
}

async function reloadQuiz() {
  try {
    quiz.value = (await getQuizToday()) as Record<string, unknown>
    quizLoadFailed.value = false
  } catch (e) {
    showApiError(e)
  }
}

async function doSignin() {
  if (signing.value || dailyStatus.value?.signed_today) return
  signing.value = true
  try {
    const res = await signin()
    await fetchMe()
    dailyStatus.value = await getDailyStatus().catch(() => dailyStatus.value)
    const bonus = res.match_day_bonus ? '（含比赛日加成）' : ''
    const streakMsg = res.signin_streak ? ` · 连续 ${res.signin_streak} 天` : ''
    const chestMsg = res.streak_bonus ? ` · 里程碑 +${res.streak_bonus} 币` : ''
    const battalion = (res as { battalion_added?: number }).battalion_added
    const battalionMsg = battalion ? ` · +${battalion} 军团贡献` : ''
    ElMessage.success(`签到成功，+${res.added} 球迷币${bonus}${streakMsg}${chestMsg}${battalionMsg}`)
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
    signing.value = false
  }
}

async function answerQuiz(idx: number) {
  try {
    const res = await submitQuizAnswer(idx)
    await fetchMe()
    quiz.value = (await getQuizToday()) as Record<string, unknown>
    dailyStatus.value = await getDailyStatus().catch(() => dailyStatus.value)
    ElMessage.success(
      res.correct
        ? `答对了！+${res.coins_awarded} 币${res.battalion_added ? ` · +${res.battalion_added} 军团贡献` : ''}`
        : '答错了，明天再来',
    )
  } catch (e) {
    showApiError(e)
  }
}

function handleLogout() {
  logout()
  router.push('/')
}

function applyRouteFocus() {
  const focus = routeFocus.value
  if (!focus || route.path !== '/me') return
  nextTick(() => scrollMeFocus(focus))
}

let predictPollTimer: ReturnType<typeof setInterval> | null = null

function stopPredictPoll() {
  if (predictPollTimer) {
    clearInterval(predictPollTimer)
    predictPollTimer = null
  }
}

function startPredictPollIfNeeded() {
  stopPredictPoll()
  if (activeTab.value !== 'records') return
  const hasPending = predictions.value.some((p) => p.status === 'pending')
  if (!hasPending) return
  predictPollTimer = setInterval(async () => {
    await refreshPredictions()
    if (!predictions.value.some((p) => p.status === 'pending')) {
      stopPredictPoll()
    }
  }, 30000)
}

function onPredictRefresh() {
  void refreshPredictions()
  void fetchMe()
  void reloadRecordsLedgers()
  if (activeTab.value === 'records') startPredictPollIfNeeded()
}

watch(
  () => [route.query.tab, route.query.focus, route.hash] as const,
  () => {
    activeTab.value = resolveTabFromRoute()
    if (activeTab.value === 'records') {
      void ensureRecordsLoaded().then(() => {
        applyRouteFocus()
        startPredictPollIfNeeded()
      })
    } else {
      applyRouteFocus()
      stopPredictPoll()
    }
  },
)

watch(routeFocus, applyRouteFocus)

onMounted(async () => {
  activeTab.value = resolveTabFromRoute()
  await loadCore()
  applyRouteFocus()

  if (activeTab.value === 'records') {
    await ensureRecordsLoaded()
    startPredictPollIfNeeded()
  }

  try {
    referralUnread.value = await getUnreadNotificationCount('referral_reward')
    const refMe = await getReferralMe()
    inviteSummary.value = {
      effective_invites: refMe.effective_invites,
      season_coins_earned: refMe.season_coins_earned,
      next_tier: refMe.next_tier,
    }
  } catch {
    referralUnread.value = 0
    inviteSummary.value = null
  }

  window.addEventListener('predict-records-refresh', onPredictRefresh)
})

onUnmounted(() => {
  window.removeEventListener('predict-records-refresh', onPredictRefresh)
  stopPredictPoll()
})
</script>

<style scoped>
.user-center {
  max-width: 1040px;
  margin: 0 auto;
  background: transparent;
  overflow-x: hidden;
}

@media (min-width: 769px) {
  .user-center {
    padding: 16px 20px 32px;
  }
}

.page-header {
  margin-bottom: 12px;
}

.page-header h1 {
  margin: 0 0 6px;
  font-size: 1.75rem;
  font-weight: 800;
  font-family: var(--wc-font-serif);
  background: linear-gradient(135deg, #f0d9b5 0%, var(--wc-accent-gold) 50%, var(--wc-accent-rose) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.page-header p {
  margin: 0;
  font-size: 0.9rem;
  color: rgba(255, 255, 255, 0.72);
}

.uc-tabs :deep(.el-tabs__header) {
  margin-bottom: 14px;
}

.uc-tabs :deep(.el-tabs__item) {
  font-weight: 600;
}

.tab-loading {
  min-height: 120px;
}

@media (max-width: 768px) {
  .user-center {
    max-width: 100%;
  }
}
</style>
