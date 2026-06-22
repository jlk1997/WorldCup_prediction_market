<template>

  <div class="duel-panel">

    <div class="duel-head">

      <h3>卡牌对决</h3>

      <span class="hint">选 3 张卡比战力 · 可用积分入场（可选）</span>

    </div>



    <el-radio-group v-model="mode" size="small" class="mode-tabs">

      <el-radio-button value="ai">练习 vs AI</el-radio-button>

      <el-radio-button value="pvp">邀请好友</el-radio-button>

    </el-radio-group>



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



        <div class="stake-row">

          <span>入场费（0=免费，{{ stakeMin }}-{{ stakeMax }}）</span>

          <el-input-number v-model="stake" :min="0" :max="stakeMax" :step="10" size="small" />

        </div>



        <div class="grid">

          <div

            v-for="c in eligible"

            :key="c.user_card_id"

            class="duel-card"

            :class="{ selected: pickedIds.includes(c.user_card_id), [c.rarity]: true }"

            @click="togglePick(c.user_card_id)"

          >

            <div class="img" :style="c.image_url ? { backgroundImage: `url(${c.image_url})` } : {}" />

            <span class="name">{{ c.name }}</span>

            <span class="pwr">战力 {{ c.power }}</span>

          </div>

        </div>



        <el-button

          type="primary"

          :loading="acting"

          :disabled="pickedIds.length !== 3 || (mode === 'pvp' && !inviteCode.trim())"

          @click="startDuel"

        >

          {{ mode === 'ai' ? '开始对决' : '发起挑战' }}

        </el-button>

      </template>



      <div v-if="history.length" class="history">

        <h4>最近对决</h4>

        <ul>

          <li v-for="h in history" :key="h.duel_id">

            <span :class="h.won ? 'win' : 'lose'">{{ h.won ? '胜' : '负' }}</span>

            <span class="opp">{{ h.mode === 'pvp' ? h.opponent_nickname : 'AI' }}</span>

            {{ h.challenger_power }} : {{ h.defender_power }}

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

import { onMounted, ref } from 'vue'

import { ElMessage, ElMessageBox } from 'element-plus'

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

  type DuelEligibleCard,

  type DuelHistoryItem,

  type DuelPendingItem,

  type DuelOutgoingItem,

} from '@/api/asset'

import { extractApiError } from '@/utils/apiError'

import { useAssetRealname } from '@/composables/useAssetRealname'

import { fetchMe } from '@/stores/authStore'



const { ensureVerified } = useAssetRealname()

const loading = ref(true)

const acting = ref(false)

const mode = ref<'ai' | 'pvp'>('ai')

const eligible = ref<DuelEligibleCard[]>([])

const history = ref<DuelHistoryItem[]>([])

const pending = ref<DuelPendingItem[]>([])

const outgoing = ref<DuelOutgoingItem[]>([])

const pickedIds = ref<number[]>([])

const stake = ref(0)

const stakeMin = ref(10)

const stakeMax = ref(100)

const inviteCode = ref('')

const acceptDialog = ref(false)

const acceptTarget = ref<DuelPendingItem | null>(null)

const acceptPicks = ref<number[]>([])


function cardName(id: number) {

  return eligible.value.find((c) => c.user_card_id === id)?.name || '—'

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

          : `确认向邀请码 ${inviteCode.value.trim()} 发起挑战？`

    await ElMessageBox.confirm(msg, '卡牌对决', {

      customClass: 'wc-message-box',

      roundButton: true,

      confirmButtonText: mode.value === 'ai' ? '开战' : '发起',

      cancelButtonText: '取消',

    })

  } catch {

    return

  }

  acting.value = true

  try {

    if (mode.value === 'ai') {

      const res = await challengeAiDuel(pickedIds.value, stake.value)

      const extra = res.battalion_added ? ` · 军团 +${res.battalion_added}` : ''

      ElMessage.success(`${res.notice} ${res.payout_notice || ''}${extra}`)

    } else {

      const res = await challengeUserDuel(pickedIds.value, {

        invite_code: inviteCode.value.trim(),

        stake_points: stake.value,

      })

      ElMessage.success(res.notice || '挑战已发出')

    }

    pickedIds.value = []

    inviteCode.value = ''

    await refreshAll()

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

    const extra = res.battalion_added ? ` · 军团 +${res.battalion_added}` : ''

    ElMessage.success(`${res.notice} ${res.payout_notice || ''}${extra}`)

    acceptDialog.value = false

    acceptTarget.value = null

    acceptPicks.value = []

    await refreshAll()

  } catch (e: unknown) {

    ElMessage.error(extractApiError(e, '应战失败'))

  } finally {

    acting.value = false

  }

}



async function refreshAll() {

  await Promise.all([loadEligible(), loadHistory(), loadPending(), loadOutgoing(), fetchMe()])

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

    await Promise.all([loadEligible(), loadHistory(), loadPending(), loadOutgoing()])

  } finally {

    loading.value = false

  }

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

.history li {

  padding: 4px 0;

  border-bottom: 1px solid rgba(255, 255, 255, 0.05);

}

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

