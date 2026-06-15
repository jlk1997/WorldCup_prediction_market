<template>

  <div class="predict-hall mobile-page">

    <div class="header glass-panel">

      <header class="page-head">
        <h1>竞猜大厅</h1>
        <p class="subtitle">猜中得累计积分冲榜 · 同时获得可用积分去兑换装扮 · 质押用球迷币</p>
      </header>

      <div v-if="authState.user" class="balance-grid">
        <div class="balance-chip">
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

      <el-alert v-else-if="authState.user" title="加载每日任务…" type="info" show-icon :closable="false" />

      <el-alert v-else title="登录后可提交竞猜" type="info" show-icon :closable="false">

        <el-button type="primary" size="small" @click="$router.push('/login')">立即登录</el-button>

      </el-alert>

    </div>



    <InvitePromptBar v-if="authState.user" scene="predict" />

    <FanRecommendationsBar :daily-status="dailyStatus" />

    <div
      v-if="dailyStatus?.pending_predictions && dailyStatus.next_pending_match"
      class="pending-banner glass-panel"
      role="button"
      tabindex="0"
      @click="$router.push('/me')"
      @keydown.enter="$router.push('/me')"
    >
      ⏳ {{ dailyStatus.pending_predictions }} 场待开奖
      <span v-if="dailyStatus.next_pending_match.hours_until != null">
        · 最近一场「{{ dailyStatus.next_pending_match.label }}」约 {{ formatHours(dailyStatus.next_pending_match.hours_until) }} 后出结果
      </span>
      <span class="pending-link">去个人中心查看 →</span>
    </div>

    <div class="match-list">

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

      <VirtualList

        v-else-if="sortedMatches.length"

        class="predict-virtual-list"

        :items="sortedMatches"

        :item-height="cardItemHeight"

        :item-key="(m) => m.id"

        :scroll-to-index="highlightScrollIndex"

      >

        <template #default="{ item: m }">

          <div

            class="match-card glass-panel"

            :class="{ highlight: m.is_main_team || m.id === highlightId, predicted: m.user_predicted }"

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

              </div>

              <div class="predicted-stake">
                <span v-if="m.user_is_free" class="stake-tag free">免费竞猜</span>
                <span v-else class="stake-tag paid">已质押 {{ m.user_stake_coins ?? 0 }} 球迷币</span>
              </div>

              <div v-if="canRaiseStake(m)" class="raise-row">
                <p class="raise-hint">可在截止前追加质押，提高猜中返币（总额上限 500 币）</p>
                <div class="raise-controls">
                  <el-input-number
                    v-model="raiseAmounts[m.id]"
                    :min="10"
                    :max="raiseMax(m)"
                    size="small"
                    style="width: 120px"
                  />
                  <el-button
                    type="primary"
                    size="small"
                    :loading="raisingId === m.id"
                    :disabled="!authState.user || raisingId === m.id"
                    @click="raiseStake(m.id)"
                  >
                    追加质押
                  </el-button>
                </div>
                <p v-if="raiseErrors[m.id]" class="submit-error">{{ raiseErrors[m.id] }}</p>
              </div>

              <p v-else-if="m.user_prediction_status === 'pending' && m.user_is_free" class="hint muted">
                免费竞猜不可追加质押；下一场可质押球迷币参与
              </p>

            </template>

            <template v-else>

              <div class="pick-row">

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
                <button type="button" class="coin-hint-action" @click="goRecharge">
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
                  @click="goRecharge"
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

            </div>

          </div>

        </template>

      </VirtualList>

      <el-empty v-else-if="!loading && !sortedMatches.length">
        <template #description>
          <p>暂无可竞猜比赛</p>
          <p class="empty-hint">可以先去赛事中心看看赛程，或完成今日签到问答</p>
        </template>
        <el-button type="primary" @click="$router.push('/')">去赛事中心</el-button>
        <el-button type="primary" @click="$router.push('/me')">球迷中心</el-button>
      </el-empty>

    </div>

    <div v-if="winFeed.length" class="win-feed glass-panel">
      <div class="feed-track">
        <span v-for="(item, idx) in winFeedDup" :key="idx" class="feed-item">
          球迷 {{ item.nickname }} 猜中 {{ item.team1 }} vs {{ item.team2 }} +{{ item.points_awarded }} 分
        </span>
      </div>
    </div>

  </div>

</template>



<script setup lang="ts">

import { computed, onMounted, ref, shallowReactive, watch } from 'vue'

import { useRoute, useRouter } from 'vue-router'

import { ElMessage, ElNotification } from 'element-plus'

import { authState, fetchMe } from '../stores/authStore'

import { fetchRecommendations, profileState } from '../stores/profileStore'

import { getPredictableMatches, submitPrediction, raisePredictionStake, getDailyStatus, getWinFeed, signin, type GameMatch, type DailyStatus } from '../api/commerce'

import { calcPredictPreview, formatPredictPreviewText } from '../utils/predictPreview'

import { getErrorMessage, isRateLimitError } from '../api/client'
import { showApiError } from '../utils/errorHandler'

import FanRecommendationsBar from '../components/FanRecommendationsBar.vue'
import DailyRitualPanel from '../components/DailyRitualPanel.vue'
import InvitePromptBar from '../components/InvitePromptBar.vue'
import VirtualList from '../components/VirtualList.vue'
import { useBreakpoint } from '../composables/useBreakpoint'
import { useInviteShare } from '../composables/useInviteShare'



const route = useRoute()
const router = useRouter()
const { isMobile } = useBreakpoint()
const { openShareSheet } = useInviteShare()

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
const raiseAmounts = shallowReactive<Record<number, number>>({})

const submittingId = ref<number | null>(null)
const raisingId = ref<number | null>(null)

const dailyStatus = ref<DailyStatus | null>(null)
const signingIn = ref(false)
const previewText = shallowReactive<Record<number, string>>({})
const winFeed = ref<{ nickname: string; team1: string; team2: string; points_awarded: number }[]>([])
const winFeedDup = computed(() => [...winFeed.value, ...winFeed.value])
const activePreviewId = ref<number | null>(null)

/** 虚拟列表行高：移动端选项纵向堆叠需更高行 */
const cardItemHeight = computed(() => (isMobile.value ? 460 : 288))



const highlightId = computed(

  () =>

    Number(route.query.highlight) ||

    profileState.recommendations?.next_main_match?.id ||

    null

)



const sortedMatches = computed(() => {

  const list = [...matches.value]

  list.sort((a, b) => {

    const score = (m: GameMatch) =>

      (m.is_main_team ? 100 : 0) + (m.is_sub_team ? 50 : 0) + (m.has_star_player ? 25 : 0)

    return score(b) - score(a)

  })

  return list

})



const highlightScrollIndex = computed(() => {

  const id = highlightId.value

  if (!id) return null

  const idx = sortedMatches.value.findIndex((m) => m.id === id)

  return idx >= 0 ? idx : null

})

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

function goRecharge() {
  router.push('/shop')
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

async function raiseStake(matchId: number) {
  delete raiseErrors[matchId]
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
    await fetchMe()
    ElMessage.success(`已追加质押 ${amount} 币，当前共 ${(m.user_stake_coins ?? 0) + amount} 币`)
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

function formatHours(h: number) {
  if (h < 1) return `${Math.round(h * 60)} 分钟`
  return `${h.toFixed(1)} 小时`
}

async function doSignin() {
  if (signingIn.value) return
  signingIn.value = true
  try {
    const res = await signin()
    await fetchMe()
    dailyStatus.value = await getDailyStatus().catch(() => null)
    ElMessage.success(`签到成功 +${res.added} 币${res.streak_bonus ? ` · 连签奖励 +${res.streak_bonus}` : ''}`)
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

      dailyStatus.value = await getDailyStatus().catch(() => null)

    }

    matches.value = await getPredictableMatches()
    winFeed.value = await getWinFeed().catch(() => [])

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
    return
  }
  submittingId.value = matchId
  try {
    await submitPrediction({
      match_id: matchId,
      pick: picks[matchId],
      stake_coins: free ? 0 : stakes[matchId],
      use_free: free,
    })
    await fetchMe()
    const msg = free ? '免费竞猜已提交，猜中得积分！' : `已质押 ${stakes[matchId]} 币，祝你好运！`
    ElMessage.success(msg)
    if (authState.user && shouldShowPredictShareNudge()) {
      markPredictShareNudge()
      ElNotification({
        title: '竞猜已提交',
        message: '点此通知 · 邀球友一起猜，双方都能得球迷币',
        type: 'success',
        duration: 6000,
        onClick: () => openShareSheet(),
      })
    }
    delete submitErrors[matchId]
    dailyStatus.value = await getDailyStatus().catch(() => dailyStatus.value)
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
      dailyStatus.value = await getDailyStatus().catch(() => dailyStatus.value)
      syncFreeCheckboxDefaults()
    }
  } finally {
    submittingId.value = null
  }
}



onMounted(load)

</script>



<style scoped>

.predict-hall {

  max-width: 920px;

  margin: 0 auto;

  min-height: calc(100dvh - var(--wc-header-height) - 48px);

  display: flex;

  flex-direction: column;

  background: transparent;

}

@media (min-width: 769px) {
  .predict-hall {
    padding: 16px 20px 24px;
  }
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

.predict-virtual-list :deep(.virtual-item) {
  overflow: visible;
  padding-bottom: 4px;
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

.match-list {

  flex: 1;

  min-height: 0;

  position: relative;

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

.predict-virtual-list {

  height: 100%;

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
}

.won-tag { color: #8fd48a; }
.lost-tag { color: #f89898; }

.raise-row {
  margin-top: 12px;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px dashed rgba(212, 165, 116, 0.35);
  background: rgba(212, 165, 116, 0.06);
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

  .match-card {
    min-height: 320px;
  }
}

@media (max-width: 480px) {
  .balance-grid {
    grid-template-columns: 1fr;
  }
}

</style>


