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
    <div v-if="note" class="reveal-card" :class="`state-${status}`">
      <div v-if="status === 'won'" class="status-icon success">
        <svg viewBox="0 0 52 52" aria-hidden="true">
          <circle class="check-circle" cx="26" cy="26" r="24" fill="none" />
          <path class="check-mark" fill="none" d="M14 27l8 8 16-18" />
        </svg>
        <div v-if="showConfetti" class="confetti-layer" aria-hidden="true">
          <span v-for="n in 12" :key="n" class="confetti" :style="{ '--i': n }" />
        </div>
      </div>
      <div v-else-if="status === 'lost'" class="status-icon lost">😔</div>
      <div v-else class="status-icon void">↩</div>

      <h2 class="reveal-title">{{ titleText }}</h2>
      <p class="match-line">{{ matchLine }}</p>
      <p v-if="scoreLine" class="score-line">{{ scoreLine }}</p>

      <div v-if="status === 'won'" class="reward-grid">
        <div v-if="pointsAwarded" class="reward-item">
          <span class="reward-val">+{{ pointsAwarded }}</span>
          <span class="reward-label">累计积分</span>
        </div>
        <div v-if="redeemAwarded" class="reward-item">
          <span class="reward-val">+{{ redeemAwarded }}</span>
          <span class="reward-label">可用积分</span>
        </div>
        <div v-if="coinsReturned" class="reward-item">
          <span class="reward-val">+{{ coinsReturned }}</span>
          <span class="reward-label">球迷币返还</span>
        </div>
        <div v-if="winStreak >= 2" class="streak-badge">🔥 {{ winStreak }} 连胜</div>
      </div>

      <p v-if="status === 'lost' && lossProtectHint" class="comfort">{{ lossProtectHint }}</p>
      <p v-if="status === 'void'" class="comfort">{{ voidHint }}</p>

      <div class="actions">
        <el-button v-if="nextMatchId" type="primary" @click="goNext">去猜下一场</el-button>
        <el-button v-if="status === 'won'" plain @click="goFanCard">分享球迷名片</el-button>
        <el-button v-if="status === 'lost'" plain @click="goRecords">查看流水</el-button>
        <el-button plain @click="close">知道了</el-button>
      </div>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { predictReveal, markPredictRead } from '@/stores/headerNotificationsStore'
import { fetchMe } from '@/stores/authStore'

const router = useRouter()
const showConfetti = ref(false)

const visible = computed({
  get: () => predictReveal.visible,
  set: (v: boolean) => {
    predictReveal.visible = v
  },
})

const note = computed(() => predictReveal.notification)
const payload = computed(() => (note.value?.payload || {}) as Record<string, unknown>)
const status = computed(() => String(payload.value.status || 'lost'))

const titleText = computed(() => {
  if (status.value === 'won') return '猜中了！'
  if (status.value === 'void') return '流局退款'
  return '差一点'
})

const matchLine = computed(() => {
  const t1 = payload.value.team1 || '?'
  const t2 = payload.value.team2 || '?'
  const pick = payload.value.user_pick_label || payload.value.user_pick
  if (pick) return `${t1} vs ${t2} · 你选「${pick}」`
  return `${t1} vs ${t2}`
})

const scoreLine = computed(() => {
  const fs = payload.value.final_score
  const rp = payload.value.result_pick_label
  if (fs && rp) return `赛果 ${fs}（${rp}）`
  if (fs) return `赛果 ${fs}`
  return note.value?.body || ''
})

const pointsAwarded = computed(() => Number(payload.value.points_awarded || 0))
const redeemAwarded = computed(() => Number(payload.value.redeem_points_awarded || 0))
const coinsReturned = computed(() => Number(payload.value.coins_returned || 0))
const winStreak = computed(() => Number(payload.value.win_streak_after || 0))
const nextMatchId = computed(() => payload.value.next_match_id as number | undefined)

const lossProtectHint = computed(() => {
  const ls = Number(payload.value.loss_streak_after || 0)
  if (ls >= 2) return '连败保护已生效：下次猜中积分有额外加成，继续加油！'
  return '下次继续加油，下一场还有机会。'
})

const voidHint = computed(() => {
  if (payload.value.void_reason === 'no_score') {
    return '比赛完场超过 72 小时仍无比分，质押已原路退还。'
  }
  return '比赛推迟或取消，质押已退还。'
})

watch(visible, (open) => {
  if (open && status.value === 'won') {
    showConfetti.value = true
    setTimeout(() => {
      showConfetti.value = false
    }, 2800)
  }
})

async function close() {
  await markPredictRead(async () => {
    await fetchMe()
    window.dispatchEvent(new CustomEvent('predict-records-refresh'))
  })
}

function onClosed() {
  showConfetti.value = false
}

function goNext() {
  const id = nextMatchId.value
  close()
  if (id) router.push({ path: '/predict', query: { highlight: String(id) } })
}

function goFanCard() {
  close()
  router.push('/me?tab=card')
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
.score-line {
  margin: 0 0 8px;
  color: var(--wc-text-muted, #9a94a8);
  font-size: 0.92rem;
  line-height: 1.5;
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
  gap: 8px;
  margin-top: 8px;
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
