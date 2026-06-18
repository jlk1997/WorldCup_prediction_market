<template>
  <el-dialog
    v-model="visible"
    :show-close="false"
    :close-on-click-modal="false"
    width="92%"
    class="predict-reveal-dialog"
    align-center
    @closed="onClosed"
  >
    <div
      v-if="resolved"
      class="reveal-card"
      :class="[`state-${resolved.status}`, slideDir ? `slide-${slideDir}` : '']"
      @touchstart.passive="onTouchStart"
      @touchend="onTouchEnd"
    >
      <div v-if="showCarousel" class="carousel-header">
        <button type="button" class="nav-btn" :disabled="!canPrev" @click="prev">‹</button>
        <span class="carousel-indicator">{{ predictReveal.index + 1 }} / {{ predictReveal.queue.length }}</span>
        <button type="button" class="nav-btn" :disabled="!canNext" @click="next">›</button>
      </div>

      <div v-if="resolved.status === 'won' && showConfetti" class="status-icon success">
        <svg viewBox="0 0 52 52" aria-hidden="true">
          <circle class="check-circle" cx="26" cy="26" r="24" fill="none" />
          <path class="check-mark" fill="none" d="M14 27l8 8 16-18" />
        </svg>
        <div v-if="confettiActive" class="confetti-layer" aria-hidden="true">
          <span v-for="n in 12" :key="n" class="confetti" :style="{ '--i': n }" />
        </div>
      </div>
      <div v-else-if="resolved.status === 'lost'" class="status-icon lost">😔</div>
      <div v-else class="status-icon void">↩</div>

      <h2 class="reveal-title">{{ titleText }}</h2>
      <p class="match-line">{{ matchLine }}</p>
      <p v-if="scoreLine" class="score-line">{{ scoreLine }}</p>
      <p v-if="extraLine" class="extra-line">{{ extraLine }}</p>

      <div v-if="resolved.status === 'won'" class="reward-grid">
        <div v-if="resolved.pointsAwarded" class="reward-item">
          <span class="reward-val">+{{ resolved.pointsAwarded }}</span>
          <span class="reward-label">累计积分</span>
        </div>
        <div v-if="resolved.redeemAwarded" class="reward-item">
          <span class="reward-val">+{{ resolved.redeemAwarded }}</span>
          <span class="reward-label">可用积分</span>
        </div>
        <div v-if="resolved.coinsReturned" class="reward-item">
          <span class="reward-val">+{{ resolved.coinsReturned }}</span>
          <span class="reward-label">球迷币返还</span>
        </div>
        <div v-if="resolved.collectibleDrop?.dropped" class="reward-item card-drop">
          <span class="reward-val">🃏</span>
          <span class="reward-label">获得球星卡</span>
        </div>
        <div v-if="resolved.winStreak >= 2" class="streak-badge">🔥 {{ resolved.winStreak }} 连胜</div>
      </div>

      <div v-if="resolved.status === 'won' && resolved.collectibleDrop?.dropped" class="card-drop-cta">
        <el-button type="primary" plain size="small" @click="openCardReveal">查看新卡</el-button>
      </div>

      <p v-if="resolved.status === 'lost' && comfortHint" class="comfort">{{ comfortHint }}</p>
      <p v-if="resolved.status === 'void' && voidHint" class="comfort">{{ voidHint }}</p>

      <div class="actions">
        <div class="actions-primary">
          <el-button
            v-if="resolved.status === 'lost'"
            type="primary"
            @click="goLostRetry"
          >
            免费再猜一场翻本
          </el-button>
          <el-button
            v-else-if="resolved.status === 'won' && (resolved.winStreak ?? 0) >= 2"
            type="primary"
            @click="goStreakProtect"
          >
            再猜一场保 {{ resolved.winStreak }} 连胜
          </el-button>
          <el-button v-else-if="resolved.nextMatchId" type="primary" @click="goNext">
            {{ btnNext }}
          </el-button>
          <el-button v-else-if="resolved.status === 'won'" type="primary" @click="goStreakProtect">
            继续猜下一场
          </el-button>
        </div>
        <div v-if="resolved.status === 'lost'" class="actions-row">
          <el-button plain @click="goAiInsight">看 AI 复盘</el-button>
        </div>
        <div v-if="resolved.status === 'won'" class="actions-row">
          <el-button type="primary" plain @click="shareWin">晒预测 · 海报</el-button>
          <el-button plain @click="goAiInsight">AI 洞察</el-button>
        </div>
        <div v-if="resolved.status === 'won'" class="actions-muted">
          <button v-if="!hasActivePass" type="button" class="link-btn" @click="goPassShop">
            开通通行证 · 猜中多赚
          </button>
          <button type="button" class="link-btn" @click="goFanCard">{{ btnShare }}</button>
        </div>
        <el-button v-if="resolved.status === 'lost'" plain @click="goRecords">{{ btnRecords }}</el-button>
        <el-button plain @click="() => close()">{{ btnDismiss }}</el-button>
      </div>

      <p v-if="showCarousel" class="swipe-hint">左右滑动可切换多条结算</p>
    </div>

    <CardRevealDialog
      v-model="cardRevealOpen"
      :drop="resolved?.collectibleDrop ?? null"
    />
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getDailyStatus, type DailyStatus } from '@/api/commerce'
import { fetchDailyStatus } from '@/stores/dailyStatusStore'
import {
  currentPredictNotification,
  goPredictReveal,
  markPredictRead,
  predictReveal,
} from '@/stores/headerNotificationsStore'
import { predictRevealConfig, ensurePredictRevealConfig } from '@/stores/predictRevealConfigStore'
import { fetchMe } from '@/stores/authStore'
import { formatTemplate, resolvePredictPayload } from '@/utils/predictRevealPayload'
import { getPredictShareUrl } from '@/api/commerce'
import { openPredictShareSheet } from '@/composables/usePredictShareSheet'
import { isWeChatBrowser, WECHAT_PAY_HINT } from '@/utils/payEnv'
import { ElMessageBox } from 'element-plus'
import { hasActiveSeasonPass } from '@/utils/entitlements'
import { authState } from '@/stores/authStore'
import CardRevealDialog from '@/components/collectible/CardRevealDialog.vue'

const router = useRouter()
const confettiActive = ref(false)
const cardRevealOpen = ref(false)
const slideDir = ref<'left' | 'right' | ''>('')
const touchStartX = ref(0)
const settlementDaily = ref<DailyStatus | null>(null)

void ensurePredictRevealConfig()

watch(
  () => predictReveal.visible,
  async (open) => {
    if (open && authState.accessToken) {
      settlementDaily.value = await getDailyStatus().catch(() => null)
    }
  },
)

const lostRetryPath = computed(() => {
  const mid =
    settlementDaily.value?.next_predictable_match?.match_id ||
    resolved.value?.nextMatchId ||
    null
  if (mid) return `/predict?highlight=${mid}`
  return '/predict'
})

const visible = computed({
  get: () => predictReveal.visible,
  set: (v: boolean) => {
    predictReveal.visible = v
  },
})

const note = computed(() => currentPredictNotification())
const resolved = computed(() => resolvePredictPayload(note.value))

const showCarousel = computed(
  () =>
    predictRevealConfig.carousel?.enabled !== false && predictReveal.queue.length > 1,
)
const canPrev = computed(() => predictReveal.index > 0)
const canNext = computed(() => predictReveal.index < predictReveal.queue.length - 1)

const stateCfg = computed(() => {
  const status = resolved.value?.status || 'lost'
  return predictRevealConfig.states?.[status] ?? predictRevealConfig.states?.lost
})

const titleText = computed(() => stateCfg.value?.title || '竞猜结果')
const showConfetti = computed(() => stateCfg.value?.show_confetti !== false)

const matchLine = computed(() => {
  const r = resolved.value
  if (!r) return ''
  const tpl = r.userPickLabel
    ? stateCfg.value?.pick_template || '{team1} vs {team2} · 你选「{pick}」'
    : stateCfg.value?.match_template || '{team1} vs {team2}'
  return formatTemplate(tpl, {
    team1: r.team1,
    team2: r.team2,
    pick: r.userPickLabel,
  })
})

const scoreLine = computed(() => {
  const r = resolved.value
  if (!r) return ''
  if (r.finalScore && r.resultPickLabel) {
    return formatTemplate(predictRevealConfig.score_template, {
      score: r.finalScore,
      result: r.resultPickLabel,
    })
  }
  if (r.finalScore) {
    return formatTemplate(predictRevealConfig.score_template_simple, {
      score: r.finalScore,
    })
  }
  return ''
})

const extraLine = computed(() => {
  const r = resolved.value
  if (!r?.detailLine) return ''
  const base = `${r.team1} vs ${r.team2}`
  let line = r.detailLine
  if (line.startsWith(base)) {
    line = line.slice(base.length).trim()
  }
  line = line.replace(/^比分\s*\d+:\d+\s*/i, '').trim()
  if (line.startsWith('·')) line = line.slice(1).trim()
  return line || ''
})

const comfortHint = computed(() => {
  const r = resolved.value
  if (!r) return ''
  if (r.lossStreak >= 2) return predictRevealConfig.hints?.loss_streak_protect
  return predictRevealConfig.hints?.loss_default
})

const voidHint = computed(() => {
  const r = resolved.value
  if (!r) return ''
  if (r.voidReason === 'no_score') return predictRevealConfig.hints?.void_no_score
  return predictRevealConfig.hints?.void_default
})

const btnNext = computed(() => predictRevealConfig.buttons?.next_match || '去猜下一场')
const btnShare = computed(() => predictRevealConfig.buttons?.share_fan_card || '分享球迷名片')
const btnRecords = computed(() => predictRevealConfig.buttons?.view_records || '查看流水')
const btnDismiss = computed(() => predictRevealConfig.buttons?.dismiss || '知道了')

watch(
  () => [visible.value, predictReveal.index, resolved.value?.status, resolved.value?.collectibleDrop?.dropped] as const,
  ([open, , status, cardDropped]) => {
    if (open && status === 'won' && showConfetti.value) {
      confettiActive.value = true
      setTimeout(() => {
        confettiActive.value = false
      }, 2800)
    }
    if (open && status === 'won' && cardDropped) {
      setTimeout(() => {
        cardRevealOpen.value = true
      }, 900)
    }
  },
)

function openCardReveal() {
  cardRevealOpen.value = true
}

function prev() {
  slideDir.value = 'right'
  goPredictReveal(-1)
  resetSlide()
}

function next() {
  slideDir.value = 'left'
  goPredictReveal(1)
  resetSlide()
}

function resetSlide() {
  setTimeout(() => {
    slideDir.value = ''
  }, 220)
}

function onTouchStart(e: TouchEvent) {
  touchStartX.value = e.changedTouches[0]?.clientX ?? 0
}

function onTouchEnd(e: TouchEvent) {
  if (!showCarousel.value) return
  const endX = e.changedTouches[0]?.clientX ?? 0
  const delta = endX - touchStartX.value
  const threshold = predictRevealConfig.carousel?.swipe_threshold_px ?? 50
  if (delta > threshold && canPrev.value) prev()
  else if (delta < -threshold && canNext.value) next()
}

async function close(options?: { skipCoach?: boolean }) {
  await markPredictRead(async () => {
    await fetchMe()
    window.dispatchEvent(new CustomEvent('predict-records-refresh'))
  })
  const daily = await fetchDailyStatus(true)
  settlementDaily.value = daily
  if (options?.skipCoach) return
  if (daily?.activation_segment === 'one_and_done' && (daily?.predict_count_total ?? 0) === 1) {
    window.dispatchEvent(new CustomEvent('second-predict-coach'))
  }
}

function onClosed() {
  confettiActive.value = false
  slideDir.value = ''
}

function goNext() {
  const id = resolved.value?.nextMatchId
  void close({ skipCoach: true })
  if (id) router.push({ path: '/predict', query: { highlight: String(id) } })
}

function goLostRetry() {
  const path = lostRetryPath.value
  void close({ skipCoach: true })
  router.push(path)
}

function goStreakProtect() {
  const id = resolved.value?.nextMatchId
  void close({ skipCoach: true })
  if (id) router.push({ path: '/predict', query: { highlight: String(id) } })
  else router.push('/predict')
}

async function goAiInsight() {
  if (isWeChatBrowser() && !hasActiveSeasonPass(authState.user)) {
    try {
      await ElMessageBox.confirm(
        `${WECHAT_PAY_HINT}\n\n也可在竞猜大厅用球迷币单次购买 AI 分析。`,
        '通行证 / 充值提示',
        { confirmButtonText: '去商城', cancelButtonText: '先去看看 AI', distinguishCancelAndClose: true },
      )
      close()
      router.push('/shop')
      return
    } catch (action) {
      if (action === 'cancel') {
        close()
        router.push('/agent')
        return
      }
      return
    }
  }
  close()
  router.push('/agent')
}

function goPassShop() {
  close()
  router.push('/shop')
}

const hasActivePass = computed(() => hasActiveSeasonPass(authState.user))

function goFanCard() {
  close()
  router.push('/me/card')
}

async function shareWin() {
  const r = resolved.value
  const predId = Number(note.value?.payload?.prediction_id)
  if (!r || !predId) {
    ElMessage.warning('暂时无法分享，请稍后在球迷名片中分享')
    goFanCard()
    return
  }
  try {
    const url = await getPredictShareUrl(predId)
    const pickLabel = r.userPickLabel
      ? `${r.userPickLabel} · 猜中 +${r.pointsAwarded || 0} 分`
      : `猜中 +${r.pointsAwarded || 0} 分`
    openPredictShareSheet({
      team1: r.team1,
      team2: r.team2,
      pickLabel,
      shareUrl: url,
      nickname: authState.user?.nickname,
    })
  } catch {
    ElMessage.warning('分享链接获取失败，请稍后再试')
  }
}

function goRecords() {
  close()
  router.push('/me?tab=records')
}
</script>

<style scoped>
.reveal-card {
  text-align: center;
  padding: 8px 4px 4px;
  transition: transform 0.2s ease, opacity 0.2s ease;
}
.reveal-card.slide-left {
  animation: slide-left 0.22s ease;
}
.reveal-card.slide-right {
  animation: slide-right 0.22s ease;
}
@keyframes slide-left {
  from { transform: translateX(12px); opacity: 0.6; }
  to { transform: translateX(0); opacity: 1; }
}
@keyframes slide-right {
  from { transform: translateX(-12px); opacity: 0.6; }
  to { transform: translateX(0); opacity: 1; }
}
.carousel-header {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-bottom: 8px;
}
.carousel-indicator {
  font-size: 0.82rem;
  color: var(--wc-text-muted, #9a94a8);
  min-width: 56px;
}
.nav-btn {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: 1px solid rgba(212, 165, 116, 0.35);
  background: rgba(255, 255, 255, 0.06);
  color: #f5f0e8;
  font-size: 1.2rem;
  line-height: 1;
  cursor: pointer;
}
.nav-btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}
.swipe-hint {
  margin: 10px 0 0;
  font-size: 0.72rem;
  color: var(--wc-text-muted, #9a94a8);
}
.reveal-card.state-won .reveal-title {
  color: var(--wc-accent-gold, #d4a574);
}
.reveal-card.state-lost .reveal-title {
  color: #c9d1d9;
}
.reveal-card.state-void .reveal-title {
  color: #79bbff;
}
.status-icon {
  margin: 0 auto 12px;
  position: relative;
}
.status-icon.success {
  width: 72px;
  height: 72px;
}
.status-icon.success svg {
  width: 72px;
  height: 72px;
}
.check-circle {
  stroke: var(--wc-accent-gold, #d4a574);
  stroke-width: 2;
  stroke-dasharray: 166;
  stroke-dashoffset: 166;
  animation: draw-circle 0.6s ease forwards;
}
.check-mark {
  stroke: var(--wc-accent-gold, #d4a574);
  stroke-width: 3;
  stroke-linecap: round;
  stroke-dasharray: 48;
  stroke-dashoffset: 48;
  animation: draw-check 0.4s 0.5s ease forwards;
}
@keyframes draw-circle {
  to { stroke-dashoffset: 0; }
}
@keyframes draw-check {
  to { stroke-dashoffset: 0; }
}
.status-icon.lost,
.status-icon.void {
  font-size: 2.5rem;
  line-height: 1;
}
.reveal-title {
  margin: 0 0 8px;
  font-size: 1.5rem;
  font-weight: 800;
}
.match-line,
.score-line,
.extra-line {
  margin: 0 0 8px;
  color: var(--wc-text-muted, #9a94a8);
  font-size: 0.92rem;
  line-height: 1.5;
}
.extra-line {
  font-size: 0.85rem;
}
.reward-grid {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 12px;
  margin: 16px 0;
}
.reward-item {
  min-width: 88px;
  padding: 10px 12px;
  border-radius: 12px;
  background: rgba(212, 165, 116, 0.12);
  border: 1px solid rgba(212, 165, 116, 0.25);
}
.reward-val {
  display: block;
  font-size: 1.25rem;
  font-weight: 800;
  color: var(--wc-accent-gold, #d4a574);
}
.reward-label {
  font-size: 0.75rem;
  color: var(--wc-text-muted);
}
.streak-badge {
  width: 100%;
  font-size: 0.9rem;
  color: #ffb347;
}
.comfort {
  font-size: 0.85rem;
  color: var(--wc-text-muted);
  margin: 0 0 12px;
}
.actions {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 8px;
}
.actions-primary {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.actions-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
.actions-muted {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 12px;
}
.link-btn {
  border: none;
  background: none;
  padding: 0;
  font-size: 0.78rem;
  color: var(--wc-text-muted, #9a94a8);
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 2px;
}
.link-btn:hover {
  color: var(--wc-accent-gold, #d4a574);
}
.confetti-layer {
  position: absolute;
  inset: -20px;
  pointer-events: none;
  overflow: hidden;
}
.confetti {
  position: absolute;
  left: calc(50% + (var(--i) - 6) * 8px);
  top: 50%;
  width: 6px;
  height: 10px;
  background: var(--wc-accent-gold, #d4a574);
  opacity: 0.85;
  animation: confetti-fall 1.8s ease-out forwards;
  animation-delay: calc(var(--i) * 0.05s);
}
@keyframes confetti-fall {
  0% { transform: translateY(0) rotate(0deg); opacity: 1; }
  100% { transform: translateY(120px) rotate(360deg); opacity: 0; }
}
</style>

<style>
.predict-reveal-dialog .el-dialog__header {
  display: none;
}
.predict-reveal-dialog .el-dialog__body {
  padding: 20px 16px 16px;
}
</style>
