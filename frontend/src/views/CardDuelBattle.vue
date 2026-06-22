<template>
  <div class="duel-battle page-shell">
    <div class="battle-bg" aria-hidden="true" />

    <div v-if="loading" class="battle-loading glass-panel">
      <p>正在进入球场…</p>
      <el-skeleton :rows="4" animated />
    </div>

    <template v-else-if="detail">
      <!-- VS intro -->
      <div v-if="phase === 'intro'" class="phase intro glass-panel animate-in">
        <p class="phase-tag">卡牌对决</p>
        <div class="vs-row">
          <div class="side you">
            <span class="side-label">你</span>
            <strong>{{ youName }}</strong>
          </div>
          <span class="vs-badge pulse">VS</span>
          <div class="side opp">
            <span class="side-label">对手</span>
            <strong>{{ oppName }}</strong>
          </div>
        </div>
        <p class="intro-hint">三局两胜 · 属性对决</p>
        <div v-if="rounds.length" class="round-dots intro-dots">
          <span v-for="r in rounds" :key="'d' + r.round" class="dot pending">{{ r.round }}</span>
        </div>
        <p v-if="chemistryLines.length" class="chemistry-line">
          <span v-for="c in chemistryLines" :key="c" class="chem-pill">{{ c }}</span>
        </p>
      </div>

      <!-- Round reveal -->
      <div v-else-if="phase === 'round' && currentRound" class="phase round glass-panel animate-in">
        <div class="round-dots">
          <span
            v-for="(r, i) in rounds"
            :key="'rd' + r.round"
            class="dot"
            :class="dotClass(i, r)"
          >{{ r.round }}</span>
        </div>
        <p class="round-label">第 {{ currentRound.round }} 回合</p>
        <div class="cards-duel">
          <div
            class="duel-card-side you-side"
            :class="sideClass('challenger')"
          >
            <div class="card-face" :class="rarityClass(currentRound.challenger_card.rarity)">
              <img v-if="currentRound.challenger_card.image_url" :src="currentRound.challenger_card.image_url" alt="" loading="lazy" decoding="async" />
              <span v-else class="card-placeholder">⚽</span>
            </div>
            <p class="card-name">{{ currentRound.challenger_card.name }}</p>
            <p v-if="currentRound.challenger_card.position" class="card-pos">{{ posLabel(currentRound.challenger_card.position) }}</p>
            <p class="card-bp">战力 {{ Math.round(currentRound.challenger_score) }}</p>
          </div>
          <span class="vs-mini">VS</span>
          <div
            class="duel-card-side opp-side"
            :class="sideClass('defender')"
          >
            <div class="card-face" :class="rarityClass(currentRound.defender_card.rarity)">
              <img v-if="currentRound.defender_card.image_url" :src="currentRound.defender_card.image_url" alt="" loading="lazy" decoding="async" />
              <span v-else class="card-placeholder">⚽</span>
            </div>
            <p class="card-name">{{ currentRound.defender_card.name }}</p>
            <p v-if="currentRound.defender_card.position" class="card-pos">{{ posLabel(currentRound.defender_card.position) }}</p>
            <p class="card-bp">战力 {{ Math.round(currentRound.defender_score) }}</p>
          </div>
        </div>

        <div v-if="currentRound.stat_comparison?.length" class="stat-bars">
          <div v-for="s in currentRound.stat_comparison.slice(0, 4)" :key="s.key" class="stat-row">
            <span class="stat-a">{{ s.a }}</span>
            <div class="bar-wrap">
              <span class="bar-label">{{ s.label }}</span>
              <div class="bar-track">
                <div class="bar-a" :style="{ width: barPct(s.a, s.b, 'a') }" />
                <div class="bar-b" :style="{ width: barPct(s.a, s.b, 'b') }" />
              </div>
            </div>
            <span class="stat-b">{{ s.b }}</span>
          </div>
        </div>

        <p v-if="currentRound.modifiers?.length" class="modifier">
          {{ currentRound.modifiers.map((m) => m.label).join(' · ') }}
        </p>
        <p v-if="roundRevealed" class="round-verdict" :class="youWonCurrentRound ? 'win' : 'lose'">
          {{ youWonCurrentRound ? '本局你占优！' : '本局对手更胜一筹' }}
        </p>
        <p class="narrative">{{ currentRound.narrative }}</p>
        <p class="score-line">大比分 {{ displayCWins }} : {{ displayDWins }}</p>
      </div>

      <!-- Result -->
      <div v-else-if="phase === 'result'" class="phase result glass-panel animate-in" :class="{ 'is-win': won }">
        <div v-if="won && !skipped" class="win-burst" aria-hidden="true" />
        <div class="result-stamp" :class="won ? 'win' : 'lose'">{{ won ? '胜利' : '失败' }}</div>
        <p class="final-score">{{ detail.challenger_power }} : {{ detail.defender_power }}</p>
        <p class="result-vs">{{ youName }} vs {{ oppName }}</p>
        <ul v-if="rounds.length" class="round-summary">
          <li v-for="r in rounds" :key="r.round">
            第{{ r.round }}局 · {{ roundWinnerLabel(r) }} · {{ r.narrative }}
          </li>
        </ul>
        <div v-if="settleExtra" class="rewards">{{ settleExtra }}</div>
        <p v-if="eloLine" class="elo-line">{{ eloLine }}</p>
        <div class="result-actions">
          <el-button type="primary" @click="goBack">返回擂台</el-button>
          <el-button plain @click="rematch">再来一局</el-button>
          <el-button v-if="!skipped" plain @click="replay">重播</el-button>
          <el-button plain @click="shareResult">分享结果</el-button>
        </div>
      </div>

      <button v-if="phase !== 'result'" type="button" class="skip-btn" @click="skipToResult">跳过动画</button>
    </template>

    <div v-else class="battle-error glass-panel">
      <p>无法加载对决数据</p>
      <el-button @click="goBack">返回</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getDuelDetail, type DuelDetail, type DuelRound } from '@/api/asset'

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const detail = ref<DuelDetail | null>(null)
const phase = ref<'intro' | 'round' | 'result'>('intro')
const roundIndex = ref(0)
const cWins = ref(0)
const dWins = ref(0)
const skipped = ref(false)
const settleExtra = ref('')
const eloLine = ref('')
const won = ref(false)
const roundRevealed = ref(false)

let timer: ReturnType<typeof setTimeout> | null = null
let revealTimer: ReturnType<typeof setTimeout> | null = null

const duelId = computed(() => Number(route.params.duelId))

const rounds = computed(() => detail.value?.rounds ?? [])

const POS_LABELS: Record<string, string> = { FWD: '前锋', MID: '中场', DEF: '后卫', GK: '门将' }
function posLabel(p?: string) {
  return POS_LABELS[p || ''] || p || ''
}

const chemistryLines = computed(() => {
  const r0 = rounds.value[0]
  if (!r0) return []
  const mods = r0.challenger_card?.bp ? [] : []
  void mods
  const lines: string[] = []
  const positions = rounds.value.map((r) => r.challenger_card?.position).filter(Boolean)
  if (positions.length === 3 && new Set(positions).size === 1) lines.push('同阵型对决')
  return lines
})

const currentRound = computed(() => rounds.value[roundIndex.value] ?? null)

const isChallenger = computed(() => detail.value?.role === 'challenger')

const displayCWins = computed(() => {
  if (!roundRevealed.value && phase.value === 'round') {
    return rounds.value.slice(0, roundIndex.value).filter((r) => r.winner_side === 'challenger').length
  }
  return cWins.value
})

const displayDWins = computed(() => {
  if (!roundRevealed.value && phase.value === 'round') {
    return rounds.value.slice(0, roundIndex.value).filter((r) => r.winner_side === 'defender').length
  }
  return dWins.value
})

const youWonCurrentRound = computed(() => {
  const r = currentRound.value
  if (!r) return false
  return youWonRound(r)
})

function youWonRound(r: DuelRound) {
  return (
    (r.winner_side === 'challenger' && isChallenger.value) ||
    (r.winner_side === 'defender' && !isChallenger.value)
  )
}

function dotClass(i: number, r: DuelRound) {
  if (i < roundIndex.value) return youWonRound(r) ? 'win' : 'lose'
  if (i === roundIndex.value && phase.value === 'round') {
    if (!roundRevealed.value) return 'active'
    return youWonRound(r) ? 'win' : 'lose'
  }
  return 'pending'
}

function sideClass(side: 'challenger' | 'defender') {
  if (!roundRevealed.value) return {}
  const win = currentRound.value?.winner_side === side
  return { winner: win, loser: !win }
}

const youName = computed(() =>
  isChallenger.value ? detail.value?.challenger_nickname : detail.value?.defender_nickname,
)

const oppName = computed(() =>
  isChallenger.value ? detail.value?.defender_nickname : detail.value?.challenger_nickname,
)

function rarityClass(r?: string) {
  return r ? `rarity-${r}` : 'rarity-common'
}

function barPct(a: number, b: number, side: 'a' | 'b') {
  const max = Math.max(a, b, 1)
  const v = side === 'a' ? a : b
  return `${Math.round((v / max) * 100)}%`
}

function roundWinnerLabel(r: DuelRound) {
  const youWin =
    (r.winner_side === 'challenger' && isChallenger.value) ||
    (r.winner_side === 'defender' && !isChallenger.value)
  return youWin ? '你赢' : '对手赢'
}

function clearRoundTimer() {
  if (timer) {
    clearTimeout(timer)
    timer = null
  }
}

function clearRevealTimer() {
  if (revealTimer) {
    clearTimeout(revealTimer)
    revealTimer = null
  }
}

function clearTimer() {
  clearRoundTimer()
  clearRevealTimer()
}

function schedule(fn: () => void, ms: number) {
  clearRoundTimer()
  timer = setTimeout(fn, ms)
}

function playRound() {
  phase.value = 'round'
  roundRevealed.value = false
  clearRevealTimer()
  const r = currentRound.value
  if (!r) {
    finishResult()
    return
  }
  revealTimer = setTimeout(() => {
    roundRevealed.value = true
  }, 950)
  schedule(() => {
    if (r.winner_side === 'challenger') cWins.value += 1
    else dWins.value += 1
    if (roundIndex.value < rounds.value.length - 1) {
      roundIndex.value += 1
      playRound()
    } else {
      finishResult()
    }
  }, 3200)
}

function finishResult() {
  phase.value = 'result'
  won.value = detail.value?.won === true
  clearTimer()
}

function skipToResult() {
  skipped.value = true
  roundRevealed.value = true
  cWins.value = detail.value?.challenger_power ?? 0
  dWins.value = detail.value?.defender_power ?? 0
  finishResult()
}

function replay() {
  skipped.value = false
  roundIndex.value = 0
  cWins.value = 0
  dWins.value = 0
  roundRevealed.value = false
  phase.value = 'intro'
  schedule(() => {
    phase.value = 'round'
    playRound()
  }, 1200)
}

function rematch() {
  router.push('/arena#duel')
}

function goBack() {
  router.push('/arena')
}

async function shareResult() {
  const d = detail.value
  if (!d) return
  const text = `卡牌对决${won.value ? '胜利' : '惜败'}！${youName.value} vs ${oppName.value} · ${d.challenger_power}:${d.defender_power}`
  const url = `${window.location.origin}/arena/battle/${duelId.value}`
  try {
    if (navigator.share) {
      await navigator.share({ title: '世界杯2026 卡牌对决', text, url })
    } else {
      await navigator.clipboard.writeText(`${text}\n${url}`)
      ElMessage.success('已复制分享链接')
    }
  } catch {
    /* user cancelled */
  }
}

async function load() {
  loading.value = true
  try {
    detail.value = await getDuelDetail(duelId.value)
    won.value = detail.value.won === true
    const q = route.query
    if (q.payout) settleExtra.value = String(q.payout)
    if (q.battalion) settleExtra.value += (settleExtra.value ? ' · ' : '') + `军团 +${q.battalion}`
    if (q.elo_delta) {
      const delta = Number(q.elo_delta)
      eloLine.value = `ELO ${delta >= 0 ? '+' : ''}${delta}${q.duel_elo ? ` · 当前 ${q.duel_elo}` : ''}`
    } else if (detail.value.your_elo_delta != null && detail.value.your_elo_delta !== 0) {
      const delta = detail.value.your_elo_delta
      eloLine.value = `ELO ${delta >= 0 ? '+' : ''}${delta}`
    }
    phase.value = 'intro'
    roundIndex.value = 0
    cWins.value = 0
    dWins.value = 0
    roundRevealed.value = false
    schedule(() => {
      phase.value = 'round'
      playRound()
    }, 1500)
  } catch {
    detail.value = null
  } finally {
    loading.value = false
  }
}

onMounted(load)
onUnmounted(clearTimer)
</script>

<style scoped>
.duel-battle {
  position: relative;
  min-height: 100vh;
  padding: 16px;
  padding-bottom: 80px;
}
.battle-bg {
  position: fixed;
  inset: 0;
  background: radial-gradient(ellipse at 50% 0%, rgba(30, 60, 120, 0.35), transparent 60%),
    linear-gradient(180deg, #0a0e1a 0%, #121828 100%);
  z-index: -1;
}
.glass-panel {
  background: rgba(8, 12, 28, 0.92) !important;
  border: 1px solid rgba(126, 184, 255, 0.25);
  border-radius: 16px;
  padding: 20px 16px;
}
.battle-loading,
.battle-error {
  margin-top: 40px;
  text-align: center;
}
.phase {
  margin-top: 12px;
}
.phase-tag,
.round-label {
  text-align: center;
  font-size: 0.72rem;
  color: #9ec8ff;
  margin: 0 0 12px;
  letter-spacing: 0.08em;
}
.vs-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
}
.side {
  text-align: center;
  flex: 1;
}
.side-label {
  display: block;
  font-size: 0.68rem;
  color: rgba(255, 255, 255, 0.5);
}
.side strong {
  font-size: 1rem;
  color: #f5f0e8;
}
.vs-badge {
  font-size: 1.4rem;
  font-weight: 900;
  color: #e8c88a;
  text-shadow: 0 0 20px rgba(232, 200, 138, 0.5);
}
.intro-hint {
  text-align: center;
  font-size: 0.78rem;
  color: rgba(255, 255, 255, 0.55);
  margin: 16px 0 0;
}
.cards-duel {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}
.duel-card-side.winner {
  opacity: 1;
  transform: scale(1.05);
}
.duel-card-side.loser {
  opacity: 0.45;
  transform: scale(0.96);
  filter: grayscale(0.35);
}
.animate-in {
  animation: fade-slide-in 0.45s ease;
}
@keyframes fade-slide-in {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
.vs-badge.pulse {
  animation: vs-pulse 1.2s ease-in-out infinite;
}
@keyframes vs-pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.08); }
}
.round-dots {
  display: flex;
  justify-content: center;
  gap: 10px;
  margin-bottom: 14px;
}
.round-dots.intro-dots {
  margin-top: 12px;
}
.round-dots .dot {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.72rem;
  font-weight: 800;
  border: 2px solid rgba(255, 255, 255, 0.15);
  color: rgba(255, 255, 255, 0.4);
  background: rgba(0, 0, 0, 0.25);
}
.round-dots .dot.pending { opacity: 0.6; }
.round-dots .dot.active {
  border-color: #9ec8ff;
  color: #9ec8ff;
  box-shadow: 0 0 12px rgba(126, 184, 255, 0.45);
  animation: dot-active 0.9s ease infinite;
}
.round-dots .dot.win {
  border-color: #7dd3a8;
  background: rgba(95, 200, 143, 0.2);
  color: #7dd3a8;
}
.round-dots .dot.lose {
  border-color: #e07a7a;
  background: rgba(224, 122, 122, 0.15);
  color: #e07a7a;
}
@keyframes dot-active {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.1); }
}
.round-verdict {
  text-align: center;
  font-size: 0.85rem;
  font-weight: 800;
  margin: 8px 0 4px;
  animation: fade-slide-in 0.35s ease;
}
.round-verdict.win { color: #7dd3a8; }
.round-verdict.lose { color: #e07a7a; }
.phase.result.is-win {
  position: relative;
  overflow: hidden;
}
.win-burst {
  position: absolute;
  inset: -20%;
  background: radial-gradient(circle, rgba(232, 200, 138, 0.18) 0%, transparent 65%);
  animation: win-burst 1.2s ease-out forwards;
  pointer-events: none;
}
@keyframes win-burst {
  from { opacity: 0; transform: scale(0.6); }
  30% { opacity: 1; }
  to { opacity: 0; transform: scale(1.4); }
}
.duel-card-side {
  flex: 1;
  text-align: center;
  opacity: 0.92;
  transition: opacity 0.45s, transform 0.45s, filter 0.45s;
}
.card-face {
  width: 100%;
  max-width: 120px;
  margin: 0 auto 8px;
  aspect-ratio: 3/4;
  border-radius: 10px;
  overflow: hidden;
  border: 2px solid rgba(255, 255, 255, 0.2);
  background: rgba(0, 0, 0, 0.4);
}
.card-face.rarity-rare { border-color: #5b9bd5; }
.card-face.rarity-epic { border-color: #b57edc; }
.card-face.rarity-legend { border-color: #e8c88a; box-shadow: 0 0 16px rgba(232, 200, 138, 0.35); }
.card-face img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.card-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  font-size: 2rem;
}
.card-name {
  margin: 0;
  font-size: 0.82rem;
  color: #f5f0e8;
}
.card-bp {
  margin: 4px 0 0;
  font-size: 0.75rem;
  color: #e8c88a;
  font-weight: 700;
}
.card-pos {
  margin: 2px 0 0;
  font-size: 0.65rem;
  color: #9ec8ff;
}
.chemistry-line {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  justify-content: center;
  margin: 10px 0 0;
}
.chem-pill {
  font-size: 0.65rem;
  padding: 3px 10px;
  border-radius: 999px;
  background: rgba(95, 200, 143, 0.12);
  color: #7dd3a8;
}
.vs-mini {
  font-weight: 800;
  color: rgba(255, 255, 255, 0.4);
  font-size: 0.85rem;
}
.stat-bars {
  margin: 16px 0 8px;
}
.stat-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  font-size: 0.72rem;
}
.stat-a, .stat-b {
  width: 24px;
  text-align: center;
  color: rgba(255, 255, 255, 0.7);
}
.bar-wrap {
  flex: 1;
}
.bar-label {
  display: block;
  text-align: center;
  font-size: 0.65rem;
  color: rgba(255, 255, 255, 0.45);
  margin-bottom: 2px;
}
.bar-track {
  display: flex;
  height: 6px;
  border-radius: 3px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.08);
}
.bar-a {
  background: linear-gradient(90deg, #e8c88a, #c99850);
  transition: width 0.6s ease;
}
.bar-b {
  background: linear-gradient(90deg, #5b9bd5, #3a7bc8);
  transition: width 0.6s ease;
}
.modifier {
  text-align: center;
  font-size: 0.72rem;
  color: #9ec8ff;
  margin: 8px 0;
}
.narrative {
  text-align: center;
  font-size: 0.88rem;
  color: #f5f0e8;
  line-height: 1.5;
  margin: 12px 0;
  padding: 10px;
  background: rgba(255, 255, 255, 0.04);
  border-radius: 8px;
}
.score-line {
  text-align: center;
  font-size: 1.1rem;
  font-weight: 700;
  color: #e8c88a;
  margin: 0;
}
.result-stamp {
  text-align: center;
  font-size: 2rem;
  font-weight: 900;
  margin-bottom: 8px;
}
.result-stamp.win { color: #7dd3a8; }
.result-stamp.lose { color: #e87878; }
.final-score {
  text-align: center;
  font-size: 1.6rem;
  font-weight: 800;
  color: #e8c88a;
  margin: 0;
}
.result-vs {
  text-align: center;
  font-size: 0.8rem;
  color: rgba(255, 255, 255, 0.55);
  margin: 8px 0 16px;
}
.round-summary {
  margin: 0 0 16px;
  padding-left: 1.2em;
  font-size: 0.75rem;
  color: rgba(255, 255, 255, 0.65);
  line-height: 1.6;
}
.rewards {
  text-align: center;
  font-size: 0.82rem;
  color: #9ec8ff;
  margin: 8px 0;
}
.elo-line {
  text-align: center;
  font-size: 0.78rem;
  color: #e8c88a;
  margin: 0 0 12px;
}
.result-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: center;
}
.skip-btn {
  position: fixed;
  bottom: 90px;
  right: 16px;
  padding: 8px 14px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  background: rgba(0, 0, 0, 0.5);
  color: rgba(255, 255, 255, 0.7);
  font-size: 0.75rem;
  cursor: pointer;
}
</style>
