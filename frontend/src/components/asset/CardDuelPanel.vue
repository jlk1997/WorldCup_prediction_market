<template>

  <div class="duel-panel">

    <div class="duel-head">

      <h3>卡牌对决</h3>

      <span class="hint">三局两胜属性对决 · 选 3 张卡 · 可用积分入场（可选）</span>

    </div>



    <DuelStatsBar ref="statsBarRef" />

    <el-radio-group v-model="mode" size="small" class="mode-tabs">

      <el-radio-button value="ai">练习 vs AI</el-radio-button>
      <el-radio-button value="match">快速匹配</el-radio-button>
      <el-radio-button value="pvp">邀请好友</el-radio-button>

    </el-radio-group>

    <div v-if="matchInQueue" class="match-queue glass-inner">
      <div class="mq-visual" aria-hidden="true">
        <span class="mq-ring" />
        <span class="mq-icon">⚔️</span>
      </div>
      <div class="mq-text">
        <p class="mq-title">正在匹配对手…</p>
        <p class="mq-sub">战力档 T{{ Math.round(matchDeckBp / 100) }} · 已等待 {{ matchWaitSec }} 秒</p>
      </div>
      <el-button size="small" plain :loading="acting" @click="doCancelMatch">取消匹配</el-button>
    </div>

    <div v-if="loading" class="duel-loading">

      <el-skeleton :rows="3" animated />

    </div>

    <template v-else>

      <!-- 待应战 -->

      <div v-if="pending.length" class="pending-block">

        <h4>待应战 ({{ pending.length }})</h4>

        <div v-for="p in pending" :key="p.duel_id" class="pending-row">

          <span>{{ p.challenger_nickname }} 向你发起挑战</span>

          <span v-if="p.stake_points" class="stake-tag">{{ p.stake_points }} 分</span>

          <el-button size="small" type="primary" @click="openAccept(p)">应战</el-button>

        </div>

      </div>



      <div v-if="outgoing.length" class="pending-block outgoing">

        <h4>我发起的挑战 ({{ outgoing.length }})</h4>

        <div v-for="o in outgoing" :key="o.duel_id" class="pending-row">

          <span>等待 {{ o.defender_nickname }} 应战</span>

          <span v-if="o.stake_points" class="stake-tag">{{ o.stake_points }} 分</span>

          <el-button size="small" plain :loading="acting" @click="doCancel(o.duel_id)">取消</el-button>

        </div>

      </div>



      <div v-if="!eligible.length" class="empty">

        暂无可用卡牌，<router-link to="/collection">去收藏册</router-link> 获取可出战卡

      </div>

      <template v-else>

        <div v-if="mode === 'pvp'" class="invite-row">

          <el-input v-model="inviteCode" placeholder="对手邀请码" size="small" clearable />

        </div>



        <div class="pick-row">
          <el-button size="small" plain :loading="recommending" @click="applyRecommendDeck">
            智能组牌
          </el-button>

          <div

            v-for="id in pickedIds"

            :key="id"

            class="picked-slot filled"

            @click="removePick(id)"

          >

            <span>{{ cardName(id) }}</span>

            <small>{{ cardPower(id) }}</small>

          </div>

          <div v-for="i in 3 - pickedIds.length" :key="'e' + i" class="picked-slot">＋</div>

        </div>



        <div v-if="deckPreview && pickedIds.length === 3" class="deck-preview glass-inner">
          <div class="dp-row">
            <span>卡组战力</span>
            <strong>均 {{ deckPreview.avg_bp }} · 档 T{{ deckPreview.tier }}</strong>
          </div>
          <div v-if="deckPreview.chemistry?.length" class="dp-chem">
            <span v-for="c in deckPreview.chemistry" :key="c" class="chem-tag">{{ c }}</span>
          </div>
          <p v-for="h in deckPreview.matchup_hints" :key="h" class="dp-hint">{{ h }}</p>
        </div>



        <div v-if="stakeTiers.length" class="stake-tiers">
          <button
            v-for="t in stakeTiers"
            :key="t.stake"
            type="button"
            class="tier-chip"
            :class="{ active: stake === t.stake }"
            @click="stake = t.stake"
          >
            {{ t.label }}{{ t.stake ? ` · ${t.stake}分` : '' }}
          </button>
        </div>

        <div v-if="chainQueueEnabled && mintedEligibleCount >= 3" class="match-mode-row">
          <span>匹配模式</span>
          <button type="button" class="tier-chip" :class="{ active: matchMode === 'casual' }" @click="matchMode = 'casual'">休闲</button>
          <button type="button" class="tier-chip" :class="{ active: matchMode === 'ranked' }" @click="matchMode = 'ranked'">排位</button>
          <button type="button" class="tier-chip" :class="{ active: matchMode === 'chain' }" @click="matchMode = 'chain'">凭证战</button>
        </div>

        <div class="stake-row">

          <span>入场费（0=免费，{{ stakeMin }}-{{ stakeMax }}）</span>

          <el-input-number v-model="stake" :min="0" :max="stakeMax" :step="10" size="small" />

        </div>



        <div class="grid">

          <div

            v-for="c in eligible"

            :key="c.user_card_id"

            class="duel-card"
            v-memo="[c.user_card_id, pickedIds.includes(c.user_card_id), pickFlashId === c.user_card_id]"

            :class="{ selected: pickedIds.includes(c.user_card_id), [c.rarity]: true, flash: pickFlashId === c.user_card_id }"

            @click="togglePick(c.user_card_id)"

          >

            <div class="img" :style="c.image_url ? { backgroundImage: `url(${c.image_url})` } : {}" />

            <span class="name">{{ c.name }}</span>
            <span v-if="c.position" class="pos">{{ posLabel(c.position) }}</span>
            <span class="pwr">战力 {{ c.power }}</span>

          </div>

        </div>



        <el-button
          type="primary"
          class="start-duel-btn"
          :loading="acting"
          :disabled="pickedIds.length !== 3 || (mode === 'pvp' && !inviteCode.trim())"
          @click="startDuel"
        >

          {{ mode === 'ai' ? '开始对决' : mode === 'match' ? '开始匹配' : '发起挑战' }}

        </el-button>

      </template>



      <div v-if="history.length" class="history">

        <h4>最近对决</h4>

        <ul>

          <li v-for="h in history" :key="h.duel_id" class="history-item" @click="viewHistory(h.duel_id)">

            <span :class="h.won ? 'win' : 'lose'">{{ h.won ? '胜' : '负' }}</span>

            <span class="opp">{{ h.mode === 'pvp' ? h.opponent_nickname : 'AI' }}</span>

            {{ h.challenger_power }} : {{ h.defender_power }}
            <small v-if="h.elo_delta" class="elo-delta" :class="h.elo_delta >= 0 ? 'up' : 'down'">
              · ELO {{ h.elo_delta >= 0 ? '+' : '' }}{{ h.elo_delta }}
            </small>

            <small v-if="h.stake_points"> · {{ h.stake_points }}分</small>

            <small v-if="h.at" class="at"> · {{ formatAt(h.at) }}</small>

          </li>

        </ul>

      </div>

    </template>



    <el-dialog

      v-model="acceptDialog"

      title="应战选卡"

      width="min(440px, 94vw)"

      align-center

      append-to-body

      class="wc-dialog"

    >

      <p v-if="acceptTarget" class="accept-hint">

        应战 {{ acceptTarget.challenger_nickname }} · 需选 3 张卡

        <span v-if="acceptTarget.stake_points"> · 入场 {{ acceptTarget.stake_points }} 分</span>

      </p>

      <div class="grid compact">

        <div

          v-for="c in eligible"

          :key="'a' + c.user_card_id"

          class="duel-card"

          :class="{ selected: acceptPicks.includes(c.user_card_id), [c.rarity]: true }"

          @click="toggleAcceptPick(c.user_card_id)"

        >

          <div class="img" :style="c.image_url ? { backgroundImage: `url(${c.image_url})` } : {}" />

          <span class="name">{{ c.name }}</span>

        </div>

      </div>

      <template #footer>

        <el-button @click="acceptDialog = false">取消</el-button>

        <el-button type="primary" :loading="acting" :disabled="acceptPicks.length !== 3" @click="doAccept">

          确认应战

        </el-button>

      </template>

    </el-dialog>

  </div>

</template>



<script setup lang="ts">

import { onMounted, onUnmounted, ref, watch, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import DuelStatsBar from '@/components/asset/DuelStatsBar.vue'
import {
  getDuelEligible,
  getDuelConfig,
  getDuelPending,
  getDuelOutgoing,
  cancelDuel,
  challengeAiDuel,
  challengeUserDuel,
  acceptDuel,
  getDuelHistory,
  enterDuelMatch,
  cancelDuelMatch,
  getDuelMatchStatus,
  previewDuelDeck,
  recommendDuelDeck,
  type DuelDeckPreview,
  type DuelEligibleCard,
  type DuelHistoryItem,
  type DuelPendingItem,
  type DuelOutgoingItem,
} from '@/api/asset'

import { extractApiError } from '@/utils/apiError'
import { readStagedDuelPicks, clearStagedDuelPicks } from '@/composables/useDuelStagedPicks'

import { useAssetRealname } from '@/composables/useAssetRealname'

import { fetchMe } from '@/stores/authStore'



const { ensureVerified } = useAssetRealname()
const router = useRouter()

const loading = ref(true)
const acting = ref(false)
const mode = ref<'ai' | 'pvp' | 'match'>('ai')
const matchInQueue = ref(false)
const matchDeckBp = ref(0)
let matchPollTimer: ReturnType<typeof setInterval> | null = null

const eligible = ref<DuelEligibleCard[]>([])

const history = ref<DuelHistoryItem[]>([])

const pending = ref<DuelPendingItem[]>([])

const outgoing = ref<DuelOutgoingItem[]>([])

const pickedIds = ref<number[]>([])

const stake = ref(0)

const stakeMin = ref(10)

const stakeMax = ref(100)
const stakeTiers = ref<{ stake: number; label: string }[]>([])
const matchMode = ref<'casual' | 'ranked' | 'chain'>('casual')
const chainQueueEnabled = ref(true)

const inviteCode = ref('')

const mintedEligibleCount = computed(() =>
  eligible.value.filter((c) => c.chain_status === 'minted').length,
)

const acceptDialog = ref(false)

const acceptTarget = ref<DuelPendingItem | null>(null)

const acceptPicks = ref<number[]>([])
const deckPreview = ref<DuelDeckPreview | null>(null)
const recommending = ref(false)
const statsBarRef = ref<InstanceType<typeof DuelStatsBar> | null>(null)
const pickFlashId = ref<number | null>(null)
const matchWaitSec = ref(0)
let matchWaitTimer: ReturnType<typeof setInterval> | null = null
let previewDebounceTimer: ReturnType<typeof setTimeout> | null = null

function applyStagedPicks() {
  const staged = readStagedDuelPicks()
  if (staged.length !== 3) return
  const valid = staged.filter((id) => eligible.value.some((c) => c.user_card_id === id))
  if (valid.length === 3) {
    pickedIds.value = valid
    clearStagedDuelPicks()
  }
}

function startMatchPoll() {
  stopMatchPoll()
  startMatchWaitTimer()
  matchPollTimer = setInterval(() => {
    if (typeof document !== 'undefined' && document.visibilityState === 'hidden') return
    void pollMatchStatus()
  }, 4000)
}

const POS_LABELS: Record<string, string> = { FWD: '前锋', MID: '中场', DEF: '后卫', GK: '门将' }
function posLabel(p?: string) {
  return POS_LABELS[p || ''] || p || ''
}

watch(
  pickedIds,
  (ids) => {
    if (previewDebounceTimer) clearTimeout(previewDebounceTimer)
    if (ids.length !== 3) {
      deckPreview.value = null
      return
    }
    const snapshot = [...ids]
    previewDebounceTimer = setTimeout(async () => {
      try {
        deckPreview.value = await previewDuelDeck(snapshot)
      } catch {
        deckPreview.value = null
      }
    }, 320)
  },
  { deep: true },
)


function cardName(id: number) {
  return eligible.value.find((c) => c.user_card_id === id)?.name || '—'
}

async function applyRecommendDeck() {
  if (eligible.value.length < 3) {
    ElMessage.warning('可用卡牌不足 3 张')
    return
  }
  recommending.value = true
  try {
    const rec = await recommendDuelDeck()
    pickedIds.value = rec.card_ids.slice(0, 3)
    ElMessage.success(rec.reason || '已为你推荐最优卡组')
  } catch (e) {
    ElMessage.error(extractApiError(e, '智能组牌失败'))
  } finally {
    recommending.value = false
  }
}

function navigateToBattle(
  duelId: number,
  extra?: { payout?: string; battalion?: number; elo_delta?: number; duel_elo?: number },
) {
  const query: Record<string, string> = {}
  if (extra?.payout) query.payout = extra.payout
  if (extra?.battalion) query.battalion = String(extra.battalion)
  if (extra?.elo_delta != null) query.elo_delta = String(extra.elo_delta)
  if (extra?.duel_elo != null) query.duel_elo = String(extra.duel_elo)
  router.push({ path: `/arena/battle/${duelId}`, query })
}

function viewHistory(duelId: number) {
  router.push(`/arena/battle/${duelId}`)
}

function stopMatchPoll() {
  if (matchPollTimer) {
    clearInterval(matchPollTimer)
    matchPollTimer = null
  }
  if (matchWaitTimer) {
    clearInterval(matchWaitTimer)
    matchWaitTimer = null
  }
  matchWaitSec.value = 0
}

function startMatchWaitTimer() {
  matchWaitSec.value = 0
  if (matchWaitTimer) clearInterval(matchWaitTimer)
  matchWaitTimer = setInterval(() => {
    matchWaitSec.value += 1
  }, 1000)
}

async function pollMatchStatus() {
  try {
    const st = await getDuelMatchStatus()
    matchInQueue.value = st.in_queue === true
    if (st.deck_bp) matchDeckBp.value = st.deck_bp
    if (st.matched && st.duel_id) {
      stopMatchPoll()
      matchInQueue.value = false
      pickedIds.value = []
      ElMessage.success('匹配成功，即将进入对决！')
      router.push(`/arena/battle/${st.duel_id}`)
    }
  } catch {
    /* ignore */
  }
}

async function doCancelMatch() {
  acting.value = true
  try {
    await cancelDuelMatch()
    stopMatchPoll()
    matchInQueue.value = false
    ElMessage.info('已取消匹配')
  } catch (e: unknown) {
    ElMessage.error(extractApiError(e, '取消失败'))
  } finally {
    acting.value = false
  }
}

function cardPower(id: number) {

  const c = eligible.value.find((x) => x.user_card_id === id)

  return c ? `战力${c.power}` : ''

}

function formatAt(iso: string) {

  try {

    const d = new Date(iso)

    return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`

  } catch {

    return ''

  }

}



function togglePick(id: number) {

  const idx = pickedIds.value.indexOf(id)

  if (idx >= 0) {

    pickedIds.value.splice(idx, 1)

    return

  }

  if (pickedIds.value.length >= 3) {

    ElMessage.warning('最多选择 3 张卡')

    return

  }

  pickedIds.value.push(id)
  pickFlashId.value = id
  setTimeout(() => {
    if (pickFlashId.value === id) pickFlashId.value = null
  }, 320)
}



function removePick(id: number) {

  pickedIds.value = pickedIds.value.filter((x) => x !== id)

}



function toggleAcceptPick(id: number) {

  const idx = acceptPicks.value.indexOf(id)

  if (idx >= 0) {

    acceptPicks.value.splice(idx, 1)

    return

  }

  if (acceptPicks.value.length >= 3) {

    ElMessage.warning('最多选择 3 张卡')

    return

  }

  acceptPicks.value.push(id)

}



function openAccept(p: DuelPendingItem) {

  acceptTarget.value = p

  acceptPicks.value = []

  acceptDialog.value = true

}



async function startDuel() {
  if (!(await ensureVerified('卡牌对决'))) return
  if (pickedIds.value.length !== 3) return
  try {
    const msg =
      stake.value > 0
        ? `确认消耗 ${stake.value} 可用积分参与对决？胜者获得扣除手续费后的奖励。`
        : mode.value === 'ai'
          ? '确认开始免费练习对决？'
          : mode.value === 'match'
            ? '确认进入快速匹配队列？匹配成功后自动开战。'
            : `确认向邀请码 ${inviteCode.value.trim()} 发起挑战？`
    await ElMessageBox.confirm(msg, '卡牌对决', {
      customClass: 'wc-message-box',
      roundButton: true,
      confirmButtonText: mode.value === 'pvp' ? '发起' : '开战',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  acting.value = true
  try {
    if (mode.value === 'match') {
      const res = await enterDuelMatch(pickedIds.value, stake.value, matchMode.value)
      matchInQueue.value = true
      matchDeckBp.value = res.deck_bp
      startMatchWaitTimer()
      ElMessage.success(res.notice || '已进入匹配队列')
      stopMatchPoll()
      startMatchPoll()
      await pollMatchStatus()
    } else if (mode.value === 'ai') {
      const res = await challengeAiDuel(pickedIds.value, stake.value)
      pickedIds.value = []
      navigateToBattle(res.duel_id, {
        payout: res.payout_notice,
        battalion: res.battalion_added,
        elo_delta: res.elo_delta,
        duel_elo: res.duel_elo,
      })
    } else {
      const res = await challengeUserDuel(pickedIds.value, {
        invite_code: inviteCode.value.trim(),
        stake_points: stake.value,
      })
      ElMessage.success(res.notice || '挑战已发出')
      pickedIds.value = []
      inviteCode.value = ''
      await refreshAll()
    }
  } catch (e: unknown) {
    ElMessage.error(extractApiError(e, '对决失败'))
  } finally {
    acting.value = false
  }
}



async function doAccept() {
  if (!(await ensureVerified('卡牌对决'))) return
  if (!acceptTarget.value || acceptPicks.value.length !== 3) return
  acting.value = true
  try {
    const res = await acceptDuel(acceptTarget.value.duel_id, acceptPicks.value)
    acceptDialog.value = false
    acceptTarget.value = null
    acceptPicks.value = []
    navigateToBattle(res.duel_id, {
      payout: res.payout_notice,
      battalion: res.battalion_added,
      elo_delta: res.elo_delta,
      duel_elo: res.duel_elo,
    })
  } catch (e: unknown) {
    ElMessage.error(extractApiError(e, '应战失败'))
  } finally {
    acting.value = false
  }
}



async function refreshAll() {
  await Promise.all([loadEligible(), loadHistory(), loadPending(), loadOutgoing(), fetchMe()])
  await statsBarRef.value?.refresh?.()
}



async function loadEligible() {

  eligible.value = await getDuelEligible()

}



async function loadHistory() {

  history.value = await getDuelHistory()

}



async function loadPending() {

  pending.value = await getDuelPending()

}



async function loadOutgoing() {

  outgoing.value = await getDuelOutgoing()

}



async function doCancel(duelId: number) {

  try {

    await ElMessageBox.confirm('取消后将退还入场费并解锁卡牌。确认取消？', '取消挑战', {

      customClass: 'wc-message-box',

      roundButton: true,

    })

  } catch {

    return

  }

  acting.value = true

  try {

    const res = await cancelDuel(duelId)

    ElMessage.success(res.notice || '已取消')

    await refreshAll()

  } catch (e: unknown) {

    ElMessage.error(extractApiError(e, '取消失败'))

  } finally {

    acting.value = false

  }

}



onMounted(async () => {
  try {
    const cfg = await getDuelConfig()
    stakeMin.value = cfg.stake_min
    stakeMax.value = cfg.stake_max
    stakeTiers.value = cfg.stake_tiers || [{ stake: 0, label: '休闲' }]
    chainQueueEnabled.value = cfg.chain_queue_enabled ?? true
    await Promise.all([loadEligible(), loadHistory(), loadPending(), loadOutgoing()])
    applyStagedPicks()
    await pollMatchStatus()
    if (matchInQueue.value) {
      startMatchPoll()
    }
  } finally {
    loading.value = false
  }
  window.addEventListener('duel-matched', onDuelMatched as EventListener)
})

function onDuelMatched() {
  void statsBarRef.value?.refresh?.()
}

onUnmounted(() => {
  stopMatchPoll()
  if (previewDebounceTimer) clearTimeout(previewDebounceTimer)
  window.removeEventListener('duel-matched', onDuelMatched as EventListener)
})

</script>



<style scoped>

.duel-panel {

  margin-top: 8px;

}

.duel-head h3 {

  margin: 0 0 4px;

  font-size: 1rem;

  color: var(--wc-text-secondary);

}

.hint {

  font-size: 0.72rem;

  color: var(--wc-text-muted);

}

.mode-tabs {

  margin: 10px 0;

}

.pending-block {

  margin-bottom: 12px;

  padding: 10px;

  border-radius: 8px;

  background: rgba(212, 165, 116, 0.08);

}

.pending-block.outgoing {
  background: rgba(100, 120, 180, 0.08);
}

.pending-block h4 {

  margin: 0 0 8px;

  font-size: 0.82rem;

}

.pending-row {

  display: flex;

  align-items: center;

  gap: 8px;

  flex-wrap: wrap;

  font-size: 0.78rem;

  padding: 4px 0;

}

.stake-tag {

  color: #f0b86c;

  font-size: 0.72rem;

}

.invite-row {

  margin-bottom: 10px;

}

.pick-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin: 12px 0;
}

.picked-slot {

  flex: 1;

  min-height: 52px;

  border: 1px dashed rgba(212, 165, 116, 0.35);

  border-radius: 8px;

  display: flex;

  flex-direction: column;

  align-items: center;

  justify-content: center;

  font-size: 0.65rem;

  color: var(--wc-text-muted);

  cursor: pointer;

}

.picked-slot.filled {

  border-style: solid;

  color: var(--wc-text-secondary);

}

.stake-tiers,
.match-mode-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  margin-bottom: 10px;
}
.tier-chip {
  border: 1px solid rgba(255, 255, 255, 0.14);
  background: rgba(255, 255, 255, 0.04);
  color: var(--wc-text-secondary);
  border-radius: 999px;
  padding: 6px 12px;
  font-size: 0.72rem;
  cursor: pointer;
}
.tier-chip.active {
  border-color: var(--wc-accent-gold);
  color: var(--wc-accent-gold);
  background: rgba(212, 165, 116, 0.12);
}
.stake-row {

  display: flex;

  align-items: center;

  justify-content: space-between;

  margin-bottom: 10px;

  font-size: 0.78rem;

  color: var(--wc-text-muted);

}

.grid {

  display: grid;

  grid-template-columns: repeat(auto-fill, minmax(72px, 1fr));

  gap: 8px;

  max-height: 220px;

  overflow-y: auto;

  margin-bottom: 12px;

}

.grid.compact {

  max-height: 180px;

}

.duel-card {

  border-radius: 8px;

  overflow: hidden;

  border: 1px solid transparent;

  cursor: pointer;

}

.duel-card.selected {

  border-color: var(--wc-accent-gold);

}

.duel-card .img {

  aspect-ratio: 3/4;

  background: rgba(20, 16, 30, 0.8);

  background-size: cover;

  background-position: center;

}

.duel-card .name {

  display: block;

  font-size: 0.58rem;

  padding: 2px 4px;

  white-space: nowrap;

  overflow: hidden;

  text-overflow: ellipsis;

}

.duel-card .pwr {

  font-size: 0.55rem;

  color: #f0b86c;

  padding: 0 4px 4px;

}

.history {

  margin-top: 16px;

}

.history h4 {

  margin: 0 0 8px;

  font-size: 0.85rem;

}

.history ul {

  margin: 0;

  padding: 0;

  list-style: none;

  font-size: 0.75rem;

}

.history li,
.history-item {
  padding: 4px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  cursor: pointer;
}
.history-item:hover {
  color: #e8c88a;
}
.duel-card .pos {
  font-size: 0.62rem;
  color: #9ec8ff;
}
.deck-preview {
  margin: 10px 0;
  padding: 10px 12px;
  border-radius: 10px;
  background: rgba(232, 200, 138, 0.08);
  border: 1px solid rgba(232, 200, 138, 0.2);
}
.dp-row {
  display: flex;
  justify-content: space-between;
  font-size: 0.78rem;
  margin-bottom: 6px;
}
.dp-row strong {
  color: #e8c88a;
}
.dp-chem {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 6px;
}
.chem-tag {
  font-size: 0.65rem;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(95, 200, 143, 0.15);
  color: #7dd3a8;
}
.dp-hint {
  margin: 4px 0 0;
  font-size: 0.68rem;
  color: rgba(255, 255, 255, 0.5);
}
.match-queue {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 10px 0;
  padding: 12px 14px;
  border-radius: 12px;
  background: rgba(126, 184, 255, 0.08);
  border: 1px solid rgba(126, 184, 255, 0.25);
}
.mq-visual {
  position: relative;
  width: 44px;
  height: 44px;
  flex-shrink: 0;
}
.mq-ring {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  border: 2px solid rgba(126, 184, 255, 0.35);
  animation: mq-pulse 1.4s ease-out infinite;
}
.mq-icon {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.2rem;
}
.mq-text {
  flex: 1;
  min-width: 0;
}
.mq-title {
  margin: 0 0 4px;
  font-size: 0.82rem;
  font-weight: 700;
  color: #9ec8ff;
}
.mq-sub {
  margin: 0;
  font-size: 0.72rem;
  color: rgba(255, 255, 255, 0.55);
}
@keyframes mq-pulse {
  0% { transform: scale(0.85); opacity: 0.9; }
  100% { transform: scale(1.35); opacity: 0; }
}
.start-duel-btn {
  width: 100%;
  margin-top: 8px;
  min-height: 44px;
  font-weight: 800;
  letter-spacing: 0.04em;
}
.duel-card.flash {
  animation: pick-flash 0.32s ease;
}
@keyframes pick-flash {
  0% { transform: scale(1); }
  50% { transform: scale(1.04); box-shadow: 0 0 12px rgba(232, 200, 138, 0.45); }
  100% { transform: scale(1); }
}
.elo-delta.up { color: #7dd3a8; }
.elo-delta.down { color: #e07a7a; }

.win { color: #5fc88f; margin-right: 6px; }

.lose { color: #e07a7a; margin-right: 6px; }

.opp { color: var(--wc-text-muted); margin-right: 4px; }

.at { color: var(--wc-text-muted); }

.empty {

  font-size: 0.8rem;

  color: var(--wc-text-muted);

  padding: 12px 0;

}

.empty a { color: var(--wc-accent-gold); }

.accept-hint {

  margin: 0 0 10px;

  font-size: 0.8rem;

  color: var(--wc-text-secondary);

}

</style>

