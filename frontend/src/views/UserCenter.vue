<template>
  <div class="user-center mobile-page" v-loading="authState.loading">
    <header class="page-header">
      <h1>球迷中心</h1>
      <p v-if="profileStatus?.main_team">⚽ {{ profileStatus.main_team.name }} 球迷 · 2026 世界杯</p>
    </header>

    <FanRecommendationsBar :max="3" :daily-status="dailyStatus" />

    <UserEntitlementsPanel v-if="authState.user" id="entitlements" :user="authState.user" />

    <div class="hero glass-panel" v-if="authState.user">
      <div class="hero-top">
        <div class="profile">
          <div class="avatar" :class="avatarFrameClass(authState.user.avatar_frame)">
            {{ authState.user.nickname.slice(0, 1) }}
          </div>
          <div class="profile-text">
            <h2>{{ authState.user.nickname }}</h2>
            <p class="email">{{ authState.user.email }}</p>
            <p v-if="passActive" class="pass-tag active">
              赛季通行证生效中 · 至 {{ formatPassUntil(authState.user.season_pass_until) }}
            </p>
            <p v-else-if="passExpired" class="pass-tag expired">赛季通行证已过期</p>
            <p v-if="profileStatus" class="fan-meta">
              球迷等级 Lv.{{ profileStatus.fan_level }} · 助威 {{ profileStatus.fan_cheers_total }}
              <span v-if="authState.user?.arena_tier"> · {{ tierLabel(authState.user.arena_tier) }}</span>
            </p>
          </div>
        </div>

        <div v-if="profileStatus?.main_team" class="identity glass-inner">
          <div class="id-row">
            <span class="label">主队</span>
            <strong>{{ profileStatus.main_team.name }}</strong>
          </div>
          <div class="id-row" v-if="profileStatus.secondary_team">
            <span class="label">副队</span>
            <strong>{{ profileStatus.secondary_team.name }}</strong>
          </div>
          <div class="stars" v-if="profileStatus.players.length">
            <span v-for="p in profileStatus.players" :key="p.id" class="star">{{ p.name }}</span>
          </div>
          <el-button link type="primary" @click="$router.push('/onboarding')">编辑偏好</el-button>
        </div>
      </div>

      <div v-if="dailyStatus" class="daily-ritual-wrap">
        <DailyRitualPanel :status="dailyStatus" />
      </div>

      <div id="quiz-section" class="quiz-inline glass-inner" v-if="quiz && !quiz.answered">
        <div class="section-head">
          <h2>今日主队问答</h2>
          <span class="section-tag pending">+15 币</span>
        </div>
        <p class="quiz-q">{{ quiz.question }}</p>
        <div class="quiz-grid">
          <button
            v-for="(opt, idx) in quiz.options"
            :key="idx"
            type="button"
            class="quiz-opt"
            @click="answerQuiz(Number(idx))"
          >
            {{ opt }}
          </button>
        </div>
      </div>
      <div id="quiz-section" class="quiz-inline glass-inner quiz-error" v-else-if="quizLoadFailed || (dailyStatus && !dailyStatus.quiz?.answered && !quiz)">
        <p>今日问答加载失败，请刷新页面重试</p>
        <button type="button" class="quiz-retry" @click="reloadQuiz">重新加载</button>
      </div>
      <div id="quiz-section" class="quiz-inline glass-inner answered" v-else-if="quiz && quiz.answered">
        <div class="section-head">
          <h2>今日主队问答</h2>
          <span class="section-tag" :class="quiz.was_correct ? 'ok' : 'fail'">
            {{ quiz.was_correct ? '已答对 +15 币' : '已答错，明天再来' }}
          </span>
        </div>
        <p class="quiz-q muted">{{ quiz.question }}</p>
      </div>

      <div v-if="dailyStatus && dailyStatus.signin_streak > 0" class="signin-calendar glass-inner">
        <span
          v-for="d in 7"
          :key="d"
          class="cal-dot"
          :class="{ lit: d <= Math.min(dailyStatus.signin_streak, 7) }"
        />
        <span class="cal-hint" v-if="dailyStatus.signin_streak_bonus_next">
          下一里程碑：第 {{ dailyStatus.signin_streak_bonus_next }} 天
        </span>
      </div>

      <div class="stats-grid">
        <div class="stat-card">
          <span class="label">球迷币</span>
          <span class="value gold">{{ authState.user.fan_coins }}</span>
        </div>
        <div class="stat-card">
          <span class="label">军团贡献</span>
          <span class="value">{{ authState.user.battalion_points_season ?? 0 }}</span>
        </div>
        <div class="stat-card">
          <span class="label">累计积分</span>
          <span class="value">{{ authState.user.season_points }}</span>
          <button type="button" class="stat-link" @click="$router.push('/leaderboard')">看排名</button>
        </div>
        <div class="stat-card highlight">
          <span class="label">可用积分</span>
          <span class="value rose">{{ authState.user.redeem_points ?? 0 }}</span>
          <button type="button" class="stat-link" @click="$router.push({ path: '/shop', query: { tab: 'redeem' } })">
            去兑换
          </button>
        </div>
        <div class="stat-card" v-if="(authState.user.extra_free_predict_daily ?? 0) > 0">
          <span class="label">额外免费竞猜</span>
          <span class="value">+{{ authState.user.extra_free_predict_daily }}/日</span>
        </div>
        <div class="stat-card">
          <span class="label">连胜</span>
          <span class="value">{{ authState.user.win_streak }}</span>
        </div>
      </div>

      <div id="signin-section" class="quick-actions">
        <div v-if="inviteSummary" class="invite-promo glass-inner" @click="$router.push('/invite')">
          <div class="promo-text">
            <strong>召友中心</strong>
            <span v-if="inviteSummary.next_tier">
              再邀 {{ inviteSummary.next_tier.remaining }} 人解锁「{{ inviteSummary.next_tier.title }}」
            </span>
            <span v-else>有效邀请 {{ inviteSummary.effective_invites }} 人 · 本季已赚 {{ inviteSummary.season_coins_earned }} 币</span>
          </div>
          <el-icon><ArrowRight /></el-icon>
        </div>
        <div class="action-grid">
          <button type="button" class="action-btn primary" :disabled="signedToday" @click="doSignin">
            {{ dailyStatus?.match_day ? '比赛日签到' : '每日签到' }}
            <small>+{{ dailyStatus?.match_day ? 30 : 20 }} 币</small>
          </button>
          <button type="button" class="action-btn" @click="$router.push('/arena')">球迷擂台</button>
          <button type="button" class="action-btn" @click="$router.push('/predict')">去竞猜</button>
          <button type="button" class="action-btn" @click="$router.push('/me/card')">球迷名片</button>
          <button type="button" class="action-btn" @click="$router.push('/invite')">
            召友中心
            <el-badge v-if="referralUnread" :value="referralUnread" class="invite-badge" />
          </button>
          <button type="button" class="action-btn" @click="$router.push('/shop')">球迷商城</button>
          <button type="button" class="action-btn" @click="$router.push({ path: '/shop', query: { tab: 'redeem' } })">
            积分兑换
          </button>
          <button type="button" class="action-btn muted" @click="logout(); $router.push('/')">退出登录</button>
        </div>
      </div>
    </div>

    <div class="content-grid">
      <div class="section glass-panel">
        <h2>账户设置</h2>
        <div class="nick-row">
          <el-input v-model="newNickname" placeholder="新昵称" maxlength="20" style="max-width: 220px" />
          <el-button plain :loading="nickLoading" @click="changeNickname">修改昵称（20 币/次）</el-button>
        </div>
      </div>
    </div>

    <div class="section glass-panel">
      <h2>积分流水</h2>
      <el-tabs v-model="pointLedgerTab" class="tabs-scroll point-ledger-tabs">
        <el-tab-pane label="累计积分" name="season">
          <div v-if="isMobile" class="mobile-ledger-list">
            <div v-for="row in seasonPointLedger" :key="row.id" class="ledger-card glass-inner">
              <div class="ledger-card-head">
                <span :class="row.delta >= 0 ? 'plus' : 'minus'">{{ row.delta >= 0 ? '+' : '' }}{{ row.delta }}</span>
                <span class="ledger-time">{{ formatTime(row.created_at) }}</span>
              </div>
              <p class="ledger-reason">{{ pointReasonLabel(row.reason) }}</p>
              <span class="ledger-balance">余额 {{ row.balance_after }}</span>
            </div>
            <p v-if="!seasonPointLedger.length" class="empty-text">暂无流水</p>
          </div>
          <div v-else class="table-scroll-wrap">
          <el-table :data="seasonPointLedger" size="small" empty-text="暂无流水">
            <el-table-column label="时间" width="160">
              <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
            </el-table-column>
            <el-table-column label="变动" width="90">
              <template #default="{ row }">
                <span :class="row.delta >= 0 ? 'plus' : 'minus'">{{ row.delta >= 0 ? '+' : '' }}{{ row.delta }}</span>
              </template>
            </el-table-column>
            <el-table-column label="原因">
              <template #default="{ row }">{{ pointReasonLabel(row.reason) }}</template>
            </el-table-column>
            <el-table-column prop="balance_after" label="余额" width="80" />
          </el-table>
          </div>
        </el-tab-pane>
        <el-tab-pane label="可用积分" name="redeem">
          <div v-if="isMobile" class="mobile-ledger-list">
            <div v-for="row in redeemPointLedger" :key="row.id" class="ledger-card glass-inner">
              <div class="ledger-card-head">
                <span :class="row.delta >= 0 ? 'plus' : 'minus'">{{ row.delta >= 0 ? '+' : '' }}{{ row.delta }}</span>
                <span class="ledger-time">{{ formatTime(row.created_at) }}</span>
              </div>
              <p class="ledger-reason">{{ pointReasonLabel(row.reason) }}</p>
              <span class="ledger-balance">余额 {{ row.balance_after }}</span>
            </div>
            <p v-if="!redeemPointLedger.length" class="empty-text">暂无流水</p>
          </div>
          <div v-else class="table-scroll-wrap">
          <el-table :data="redeemPointLedger" size="small" empty-text="暂无流水">
            <el-table-column label="时间" width="160">
              <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
            </el-table-column>
            <el-table-column label="变动" width="90">
              <template #default="{ row }">
                <span :class="row.delta >= 0 ? 'plus' : 'minus'">{{ row.delta >= 0 ? '+' : '' }}{{ row.delta }}</span>
              </template>
            </el-table-column>
            <el-table-column label="原因">
              <template #default="{ row }">{{ pointReasonLabel(row.reason) }}</template>
            </el-table-column>
            <el-table-column prop="balance_after" label="余额" width="80" />
          </el-table>
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>

    <div class="section glass-panel">
      <h2>兑换记录</h2>
      <div v-if="isMobile" class="mobile-ledger-list">
        <div v-for="row in redeemOrders" :key="row.id" class="ledger-card glass-inner">
          <strong class="ledger-title">{{ row.product_name }}</strong>
          <p class="ledger-reason">消耗 {{ row.redeem_price }} 可用积分</p>
          <span class="ledger-time">{{ formatTime(row.created_at ?? null) }}</span>
        </div>
        <p v-if="!redeemOrders.length" class="empty-text">暂无兑换</p>
      </div>
      <div v-else class="table-scroll-wrap">
      <el-table :data="redeemOrders" size="small" empty-text="暂无兑换">
        <el-table-column prop="product_name" label="商品" min-width="140" />
        <el-table-column prop="redeem_price" label="消耗积分" width="100" />
        <el-table-column label="时间" width="160">
          <template #default="{ row }">{{ formatTime(row.created_at ?? null) }}</template>
        </el-table-column>
      </el-table>
      </div>
    </div>

    <div class="section glass-panel">
      <h2>球迷币流水</h2>
      <div v-if="isMobile" class="mobile-ledger-list">
        <div v-for="row in ledger" :key="row.id" class="ledger-card glass-inner">
          <div class="ledger-card-head">
            <span :class="row.delta >= 0 ? 'plus' : 'minus'">{{ row.delta >= 0 ? '+' : '' }}{{ row.delta }}</span>
            <span class="ledger-time">{{ formatTime(row.created_at) }}</span>
          </div>
          <p class="ledger-reason">{{ reasonLabel(row.reason) }}</p>
          <span class="ledger-balance">余额 {{ row.balance_after }}</span>
        </div>
        <p v-if="!ledger.length" class="empty-text">暂无流水</p>
      </div>
      <div v-else class="table-scroll-wrap">
      <el-table :data="ledger" size="small" empty-text="暂无流水">
        <el-table-column label="时间" width="160">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="变动" width="90">
          <template #default="{ row }">
            <span :class="row.delta >= 0 ? 'plus' : 'minus'">{{ row.delta >= 0 ? '+' : '' }}{{ row.delta }}</span>
          </template>
        </el-table-column>
        <el-table-column label="原因">
          <template #default="{ row }">{{ reasonLabel(row.reason) }}</template>
        </el-table-column>
        <el-table-column prop="balance_after" label="余额" width="80" />
      </el-table>
      </div>
    </div>

    <div id="predictions-section" class="section glass-panel">
      <h2>我的竞猜</h2>
      <div v-if="isMobile" class="mobile-predict-list">
        <div v-for="row in predictions" :key="row.id" class="predict-card glass-inner">
          <div class="predict-match">{{ row.team1 || '?' }} vs {{ row.team2 || '?' }}</div>
          <div class="predict-meta">
            <span>{{ row.pick_label || row.pick }}</span>
            <span>{{ row.is_free ? '免费' : `${row.stake_coins} 币` }}</span>
            <span>{{ row.status_label || row.status }}</span>
          </div>
          <div class="predict-footer">
            <span v-if="row.final_score">赛果 {{ row.final_score }}</span>
            <span v-if="row.status === 'won' && row.points_awarded" class="plus">+{{ row.points_awarded }} 累计分</span>
            <span v-if="row.status === 'won' && row.redeem_points_awarded" class="redeem-pts">+{{ row.redeem_points_awarded }} 可用分</span>
          </div>
        </div>
        <p v-if="!predictions.length" class="empty-text">暂无记录</p>
      </div>
      <div v-else class="table-scroll-wrap">
      <el-table :data="predictions" size="small" empty-text="暂无记录">
        <el-table-column label="对阵" min-width="160">
          <template #default="{ row }">{{ row.team1 || '?' }} vs {{ row.team2 || '?' }}</template>
        </el-table-column>
        <el-table-column prop="pick_label" label="我的选择" width="100" />
        <el-table-column label="质押/返币" width="110">
          <template #default="{ row }">
            <span v-if="row.is_free">免费</span>
            <span v-else>{{ row.stake_coins }} 币</span>
            <span v-if="row.coins_returned > 0" class="return-coins"> +{{ row.coins_returned }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="status_label" label="状态" width="90" />
        <el-table-column label="赛果" width="70">
          <template #default="{ row }">{{ row.final_score || '—' }}</template>
        </el-table-column>
        <el-table-column label="累计积分" width="90">
          <template #default="{ row }">
            <span v-if="row.status === 'won' && row.points_awarded">+{{ row.points_awarded }}</span>
            <span v-else>—</span>
          </template>
        </el-table-column>
        <el-table-column label="可用积分" width="90">
          <template #default="{ row }">
            <span v-if="row.status === 'won' && row.redeem_points_awarded" class="redeem-pts">
              +{{ row.redeem_points_awarded }}
            </span>
            <span v-else>—</span>
          </template>
        </el-table-column>
      </el-table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowRight } from '@element-plus/icons-vue'
import FanRecommendationsBar from '../components/FanRecommendationsBar.vue'
import DailyRitualPanel from '../components/DailyRitualPanel.vue'
import UserEntitlementsPanel from '../components/UserEntitlementsPanel.vue'
import { authState, fetchMe, logout } from '../stores/authStore'
import { fetchProfileStatus, fetchRecommendations, profileState } from '../stores/profileStore'
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
import { getUnreadNotificationCount } from '../api/notifications'
import { getReferralMe, type ReferralMe } from '../api/referral'
import { showApiError } from '../utils/errorHandler'
import { scrollMeFocus } from '../utils/dailyActionNav'
import { useBreakpoint } from '../composables/useBreakpoint'
import {
  avatarFrameClass,
  formatPassUntil,
  hasActiveSeasonPass,
} from '../utils/entitlements'

const { isMobile } = useBreakpoint()
const route = useRoute()

const predictions = ref<GamePrediction[]>([])
const ledger = ref<CoinLedgerEntry[]>([])
const seasonPointLedger = ref<PointLedgerEntry[]>([])
const redeemPointLedger = ref<PointLedgerEntry[]>([])
const redeemOrders = ref<RedeemOrder[]>([])
const pointLedgerTab = ref('season')
const newNickname = ref('')
const nickLoading = ref(false)
const signedToday = ref(false)
const dailyStatus = ref<DailyStatus | null>(null)
const quiz = ref<any>(null)
const quizLoadFailed = ref(false)
const referralUnread = ref(0)
const inviteSummary = ref<Pick<ReferralMe, 'effective_invites' | 'season_coins_earned' | 'next_tier'> | null>(null)

const profileStatus = computed(() => profileState.status)

const passActive = computed(() => hasActiveSeasonPass(authState.user))
const passExpired = computed(
  () => !!authState.user?.has_season_pass && !passActive.value,
)

const tierLabels: Record<string, string> = {
  pioneer: '先锋',
  starter: '主力',
  bench: '替补',
  rookie: '新兵',
}

function tierLabel(code: string) {
  return tierLabels[code] ?? code
}

const reasonLabels: Record<string, string> = {
  register_bonus: '注册赠送',
  signin: '每日签到',
  quiz: '主队问答',
  ai_analysis: 'AI 分析',
  ai_analysis_refund: 'AI 分析退款',
  season_pass_daily: '通行证每日领币',
  cheer: '助威',
  predict_stake: '竞猜质押',
  predict_win: '竞猜猜中（累计）',
  predict_win_redeem: '竞猜猜中（可用）',
  predict_win_return: '竞猜返币',
  predict_void_refund: '流局退质押',
  free_predict_win: '免费竞猜奖励',
  redeem_purchase: '积分兑换',
  referral_tier_5: '召友档位奖励',
  recharge: '充值到账',
  purchase: '商城购买',
  nickname_change: '修改昵称',
  arena_boost: '擂台应援',
  referral_register_invitee: '邀请注册奖励',
  referral_profile_inviter: '好友完成档案',
  referral_profile_invitee: '完成档案奖励',
  referral_action_inviter: '好友首玩奖励',
  referral_action_invitee: '首玩奖励',
  referral_active_7d: '好友7日活跃',
  referral_same_team_inviter: '同主队扩编',
  referral_same_team_invitee: '同主队扩编',
  referral_weekly_rank: '召友周榜',
}

function pointReasonLabel(code: string) {
  const map: Record<string, string> = {
    predict_win: '竞猜猜中（累计积分）',
    predict_win_redeem: '竞猜猜中（可用积分）',
    redeem_purchase: '积分兑换消费',
    referral_tier_5: '召友里程碑',
    referral_weekly_rank: '召友周榜荣誉分',
  }
  return map[code] || reasonLabel(code)
}

function reasonLabel(code: string) {
  return reasonLabels[code] || code
}

function formatTime(iso: string | null) {
  if (!iso) return '-'
  return iso.replace('T', ' ').slice(0, 16)
}

async function changeNickname() {
  const name = newNickname.value.trim()
  if (!name) {
    ElMessage.warning('请输入新昵称')
    return
  }
  nickLoading.value = true
  try {
    await updateProfile({ nickname: name })
    await fetchMe()
    newNickname.value = ''
    ElMessage.success('昵称已更新，已扣除 20 球迷币')
    await load()
  } catch (e) {
    showApiError(e)
  } finally {
    nickLoading.value = false
  }
}

async function refreshPredictions() {
  predictions.value = await getMyPredictions()
}

async function load() {
  await fetchMe()
  await fetchProfileStatus(true)
  await fetchRecommendations(true)
  await refreshPredictions()
  try {
    ledger.value = await getWalletLedger(30)
    seasonPointLedger.value = await getPointLedger('season', 30)
    redeemPointLedger.value = await getPointLedger('redeem', 30)
    redeemOrders.value = await getRedeemOrders()
  } catch {
    ledger.value = []
    seasonPointLedger.value = []
    redeemPointLedger.value = []
    redeemOrders.value = []
  }
  try {
    dailyStatus.value = await getDailyStatus()
    signedToday.value = dailyStatus.value.signed_today
  } catch {
    dailyStatus.value = null
  }
  try {
    quiz.value = await getQuizToday()
    quizLoadFailed.value = false
  } catch {
    quiz.value = null
    quizLoadFailed.value = true
  }
}

async function reloadQuiz() {
  try {
    quiz.value = await getQuizToday()
    quizLoadFailed.value = false
  } catch (e) {
    showApiError(e)
  }
}

async function doSignin() {
  try {
    const res = await signin()
    await fetchMe()
    dailyStatus.value = await getDailyStatus().catch(() => null)
    signedToday.value = true
    const bonus = res.match_day_bonus ? '（含比赛日加成）' : ''
    const streakMsg = res.signin_streak ? ` · 连续 ${res.signin_streak} 天` : ''
    const chestMsg = res.streak_bonus ? ` · 里程碑 +${res.streak_bonus} 币` : ''
    const battalion = (res as { battalion_added?: number }).battalion_added
    const battalionMsg = battalion ? ` · +${battalion} 军团贡献` : ''
    ElMessage.success(`签到成功，+${res.added} 球迷币${bonus}${streakMsg}${chestMsg}${battalionMsg}`)
  } catch (e) {
    showApiError(e)
  }
}

async function answerQuiz(idx: number) {
  try {
    const res = await submitQuizAnswer(idx)
    await fetchMe()
    quiz.value = await getQuizToday()
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

function applyRouteFocus() {
  const focus = route.query.focus
  if (typeof focus !== 'string' || route.path !== '/me') return
  nextTick(() => scrollMeFocus(focus))
}

watch(() => route.query.focus, applyRouteFocus)

let predictPollTimer: ReturnType<typeof setInterval> | null = null

function onPredictRefresh() {
  refreshPredictions()
  fetchMe()
  loadLedgers()
}

async function loadLedgers() {
  try {
    ledger.value = await getWalletLedger(30)
    seasonPointLedger.value = await getPointLedger('season', 30)
    redeemPointLedger.value = await getPointLedger('redeem', 30)
    redeemOrders.value = await getRedeemOrders()
  } catch {
    /* ignore */
  }
}

onMounted(async () => {
  await load()
  applyRouteFocus()
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
  const hasPending = predictions.value.some((p) => p.status === 'pending')
  if (hasPending) {
    predictPollTimer = setInterval(async () => {
      await refreshPredictions()
      if (!predictions.value.some((p) => p.status === 'pending') && predictPollTimer) {
        clearInterval(predictPollTimer)
        predictPollTimer = null
      }
    }, 60000)
  }
})

onUnmounted(() => {
  window.removeEventListener('predict-records-refresh', onPredictRefresh)
  if (predictPollTimer) clearInterval(predictPollTimer)
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
  margin-bottom: 16px;
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

.hero {
  padding: 22px;
  margin-bottom: 16px;
}

.hero-top {
  display: grid;
  grid-template-columns: 1fr minmax(200px, 280px);
  gap: 16px;
  margin-bottom: 16px;
}

@media (max-width: 768px) {
  .hero-top {
    grid-template-columns: 1fr;
  }
  .quick-actions {
    display: flex;
    flex-direction: column;
  }
  .action-btn {
    width: 100%;
    min-height: 44px;
    text-align: center;
  }
}

.profile {
  display: flex;
  align-items: flex-start;
  gap: 16px;
}

.profile-text h2 {
  margin: 0 0 4px;
  font-size: 1.35rem;
  color: #f5f0e8;
}

.email {
  margin: 0;
  font-size: 0.85rem;
  color: rgba(255, 255, 255, 0.55);
  word-break: break-all;
}

.fan-meta {
  color: rgba(255, 255, 255, 0.65);
  font-size: 0.82rem;
  margin-top: 6px;
}

.identity {
  padding: 14px 16px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(212, 165, 116, 0.15);
}

.id-row {
  display: flex;
  gap: 12px;
  margin-bottom: 8px;
}

.id-row .label {
  color: rgba(255, 255, 255, 0.5);
  min-width: 40px;
}

.stars {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 8px 0;
}

.star {
  padding: 3px 10px;
  border-radius: 12px;
  background: rgba(212, 165, 116, 0.15);
  font-size: 0.82rem;
  color: #f0d9b5;
}

.avatar {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--wc-accent-rose), var(--wc-accent-gold));
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
  font-weight: 700;
  flex-shrink: 0;
  color: #1a1208;
}

.avatar.frame-gold_wc {
  box-shadow: 0 0 0 3px #e8c88a, 0 0 14px rgba(212, 165, 116, 0.45);
}

.avatar.frame-silver_wc {
  box-shadow: 0 0 0 3px #c0c0c0, 0 0 12px rgba(200, 200, 200, 0.35);
}

.avatar.frame-referral_squad {
  box-shadow: 0 0 0 3px #c9788a, 0 0 12px rgba(201, 120, 138, 0.35);
}

.pass-tag {
  font-size: 0.78rem;
  margin: 4px 0 0;
  line-height: 1.4;
}

.pass-tag.active {
  color: #8fd48a;
}

.pass-tag.expired {
  color: var(--wc-text-muted);
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 10px;
  margin-bottom: 18px;
}

.stat-card {
  padding: 12px 14px;
  border-radius: 12px;
  background: rgba(12, 14, 28, 0.55);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.stat-card.highlight {
  border-color: rgba(201, 120, 138, 0.35);
  background: rgba(201, 120, 138, 0.08);
}

.stat-card .label {
  display: block;
  font-size: 0.75rem;
  color: rgba(255, 255, 255, 0.55);
  margin-bottom: 4px;
}

.stat-card .value {
  font-size: 1.35rem;
  font-weight: 800;
  color: #f5f0e8;
}

.stat-card .value.gold {
  color: var(--wc-accent-gold);
}

.stat-card .value.rose {
  color: var(--wc-accent-rose);
}

.stat-link {
  margin-top: 6px;
  padding: 0;
  border: none;
  background: none;
  color: var(--wc-accent-gold);
  font-size: 0.78rem;
  cursor: pointer;
}

.stat-link:hover {
  text-decoration: underline;
}

.signin-calendar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  padding: 10px 16px;
  border-radius: 10px;
}

.cal-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.12);
}

.cal-dot.lit {
  background: linear-gradient(135deg, #d4a574, #c9788a);
  box-shadow: 0 0 6px rgba(212, 165, 116, 0.5);
}

.cal-hint {
  margin-left: 8px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.55);
}

.quick-actions {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.invite-promo {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  border-radius: 12px;
  cursor: pointer;
  border: 1px solid rgba(212, 165, 116, 0.28);
  background: rgba(212, 165, 116, 0.06);
}

.invite-promo:hover {
  background: rgba(212, 165, 116, 0.12);
}

.promo-text {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 0.85rem;
  color: rgba(255, 255, 255, 0.75);
}

.promo-text strong {
  color: var(--wc-accent-gold);
}

.action-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(118px, 1fr));
  gap: 10px;
}

.action-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  min-height: 52px;
  padding: 10px 8px;
  border-radius: 12px;
  border: 1px solid rgba(212, 165, 116, 0.28);
  background: rgba(18, 22, 36, 0.75);
  color: #f5f0e8;
  font-size: 0.82rem;
  font-weight: 600;
  cursor: pointer;
  transition: border-color 0.2s, background 0.2s, transform 0.15s;
}

.action-btn small {
  font-size: 0.7rem;
  font-weight: 500;
  color: var(--wc-accent-gold);
}

.action-btn:hover:not(:disabled) {
  border-color: var(--wc-accent-gold);
  background: rgba(212, 165, 116, 0.1);
  transform: translateY(-1px);
}

.action-btn.primary {
  border-color: rgba(212, 165, 116, 0.55);
  background: linear-gradient(135deg, rgba(212, 165, 116, 0.22) 0%, rgba(201, 120, 138, 0.12) 100%);
}

.action-btn.primary:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.action-btn.muted {
  color: rgba(255, 255, 255, 0.55);
  border-color: rgba(255, 255, 255, 0.12);
}

.content-grid {
  display: grid;
  grid-template-columns: 1.2fr 0.8fr;
  gap: 16px;
  margin-bottom: 16px;
}

@media (max-width: 860px) {
  .content-grid {
    grid-template-columns: 1fr;
  }
}

.section {
  padding: 18px 20px;
  margin-bottom: 16px;
}

.section h2 {
  margin: 0 0 14px;
  font-size: 1rem;
  font-weight: 700;
  color: #f0d9b5;
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.section-head h2 {
  margin: 0;
}

.section-tag {
  font-size: 0.75rem;
  padding: 3px 10px;
  border-radius: 999px;
}

.section-tag.ok {
  background: rgba(103, 194, 58, 0.15);
  color: #8fd48a;
}

.section-tag.fail {
  background: rgba(245, 108, 108, 0.15);
  color: #f89898;
}

.quiz-inline {
  padding: 16px 18px;
  margin-bottom: 16px;
  border-radius: 12px;
  border: 1px solid rgba(212, 165, 116, 0.25);
  background: rgba(212, 165, 116, 0.06);
}

.quiz-inline.answered {
  opacity: 0.85;
}

.quiz-inline.focus-flash,
#signin-section.focus-flash,
#predictions-section.focus-flash {
  animation: focusPulse 2s ease;
}

@keyframes focusPulse {
  0%, 100% { box-shadow: none; }
  20%, 60% { box-shadow: 0 0 0 2px rgba(212, 165, 116, 0.7), 0 0 24px rgba(212, 165, 116, 0.35); }
}

.section-tag.pending {
  background: rgba(212, 165, 116, 0.18);
  color: var(--wc-accent-gold);
}

.quiz-q.muted {
  color: rgba(255, 255, 255, 0.55);
  margin-bottom: 0;
}

.quiz-inline .section-head h2 {
  margin: 0;
  font-size: 1rem;
  font-weight: 700;
  color: #f0d9b5;
}

.quiz-q {
  margin: 0 0 14px;
  font-size: 1rem;
  line-height: 1.5;
  color: rgba(255, 255, 255, 0.9);
}

.quiz-inline .quiz-q {
  margin-bottom: 12px;
}

.quiz-error {
  text-align: center;
  color: rgba(255, 255, 255, 0.7);
}

.quiz-retry {
  margin-top: 10px;
  padding: 8px 16px;
  border-radius: 8px;
  border: 1px solid rgba(212, 165, 116, 0.4);
  background: rgba(212, 165, 116, 0.12);
  color: var(--wc-accent-gold);
  cursor: pointer;
}

#signin-section.focus-flash .action-btn.primary {
  animation: focusPulse 2s ease;
}

.quiz-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
}

@media (max-width: 520px) {
  .quiz-grid {
    grid-template-columns: 1fr;
  }
}

.quiz-opt {
  padding: 12px 14px;
  border-radius: 10px;
  border: 1px solid rgba(212, 165, 116, 0.3);
  background: rgba(12, 14, 28, 0.6);
  color: #f5f0e8;
  font-size: 0.9rem;
  font-weight: 600;
  text-align: left;
  cursor: pointer;
  transition: border-color 0.2s, background 0.2s;
}

.quiz-opt:hover {
  border-color: var(--wc-accent-gold);
  background: rgba(212, 165, 116, 0.12);
}

.nick-row {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  align-items: center;
}

.plus {
  color: #67c23a;
  font-weight: 600;
}

.minus {
  color: #f56c6c;
  font-weight: 600;
}

.redeem-pts {
  color: var(--wc-accent-rose);
  font-weight: 600;
}

.return-coins {
  color: #6ec99a;
  margin-left: 4px;
}

.mobile-ledger-list,
.mobile-predict-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.ledger-card,
.predict-card {
  padding: 12px 14px;
  border-radius: 10px;
}

.ledger-card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  margin-bottom: 4px;
}

.ledger-time {
  font-size: 0.72rem;
  color: var(--wc-text-muted);
}

.ledger-reason {
  margin: 0 0 4px;
  font-size: 0.85rem;
  color: rgba(255, 255, 255, 0.85);
}

.ledger-balance {
  font-size: 0.75rem;
  color: var(--wc-text-muted);
}

.ledger-title {
  display: block;
  color: #f5f0e8;
  margin-bottom: 4px;
}

.empty-text {
  text-align: center;
  color: var(--wc-text-muted);
  font-size: 0.85rem;
  padding: 16px 0;
}

.predict-match {
  font-weight: 700;
  color: #f5f0e8;
  margin-bottom: 6px;
}

.predict-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 12px;
  font-size: 0.78rem;
  color: var(--wc-text-muted);
}

.predict-footer {
  margin-top: 6px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  font-size: 0.75rem;
  color: var(--wc-text-muted);
}

.point-ledger-tabs :deep(.el-tabs__nav-wrap) {
  overflow-x: auto;
}

@media (max-width: 768px) {
  .user-center {
    max-width: 100%;
  }

  .hero {
    padding: 16px;
  }

  .stats-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .action-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .nick-row {
    flex-direction: column;
    align-items: stretch;
  }

  .nick-row .el-input {
    max-width: none !important;
    width: 100%;
  }

  .nick-row .el-button {
    width: 100%;
    min-height: 44px;
  }
}
</style>
