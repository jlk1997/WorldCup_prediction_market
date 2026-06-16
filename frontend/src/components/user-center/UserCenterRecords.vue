<template>
  <div class="uc-records">
    <div v-if="isMobile" class="records-segment">
      <button
        v-for="item in mainTabItems"
        :key="item.name"
        type="button"
        class="seg-btn"
        :class="{ active: subTab === item.name }"
        @click="subTab = item.name"
      >
        {{ item.label }}
      </button>
    </div>

    <el-tabs v-model="subTab" class="records-tabs" :class="{ 'hide-header': isMobile }">
      <el-tab-pane label="竞猜" name="predictions">
        <div id="predictions-section" :class="{ 'focus-flash': focusKey === 'predictions' }">
          <LedgerList :rows="predictions" :columns="predictionColumns" empty-text="暂无竞猜记录">
            <template #mobile="{ row }">
              <div class="predict-match">{{ row.team1 || '?' }} vs {{ row.team2 || '?' }}</div>
              <div class="predict-meta">
                <span class="predict-chip">{{ row.pick_label || row.pick }}</span>
                <span class="predict-chip">{{ row.is_free ? '免费' : `${row.stake_coins} 币` }}</span>
                <span class="predict-chip" :class="statusClass(row.status)">
                  {{ row.status_label || row.status }}
                </span>
              </div>
              <div class="predict-footer">
                <span v-if="row.final_score">赛果 {{ row.final_score }}</span>
                <span v-if="row.status === 'won' && row.points_awarded" class="plus">
                  +{{ row.points_awarded }} 累计分
                </span>
                <span v-if="row.status === 'won' && row.redeem_points_awarded" class="redeem-pts">
                  +{{ row.redeem_points_awarded }} 可用分
                </span>
              </div>
            </template>
            <template #match="{ row }">{{ row.team1 || '?' }} vs {{ row.team2 || '?' }}</template>
            <template #pick="{ row }">{{ row.pick_label || row.pick }}</template>
            <template #stake="{ row }">
              <span v-if="row.is_free">免费</span>
              <span v-else>{{ row.stake_coins }} 币</span>
              <span v-if="row.coins_returned > 0" class="return-coins"> +{{ row.coins_returned }}</span>
            </template>
            <template #status="{ row }">
              <span :class="statusClass(row.status)">{{ row.status_label || row.status }}</span>
            </template>
            <template #final="{ row }">{{ row.final_score || '—' }}</template>
            <template #seasonPts="{ row }">
              <span v-if="row.status === 'won' && row.points_awarded">+{{ row.points_awarded }}</span>
              <span v-else>—</span>
            </template>
            <template #redeemPts="{ row }">
              <span v-if="row.status === 'won' && row.redeem_points_awarded" class="redeem-pts">
                +{{ row.redeem_points_awarded }}
              </span>
              <span v-else>—</span>
            </template>
          </LedgerList>
        </div>
      </el-tab-pane>

      <el-tab-pane label="积分" name="points">
        <div v-if="isMobile" class="records-segment records-segment--sub">
          <button
            v-for="item in pointTabItems"
            :key="item.name"
            type="button"
            class="seg-btn seg-btn--sub"
            :class="{ active: pointSubTab === item.name }"
            @click="pointSubTab = item.name"
          >
            {{ item.label }}
          </button>
        </div>
        <el-tabs v-model="pointSubTab" class="point-sub-tabs" :class="{ 'hide-header': isMobile }">
          <el-tab-pane label="累计积分" name="season">
            <LedgerList :rows="seasonPointLedger" :columns="pointColumns" empty-text="暂无流水">
              <template #mobile="{ row }">
                <div class="ledger-card-head">
                  <span class="ledger-delta" :class="row.delta >= 0 ? 'plus' : 'minus'">
                    {{ formatDelta(row.delta) }}
                  </span>
                  <span class="ledger-time">{{ formatTime(row.created_at) }}</span>
                </div>
                <p class="ledger-reason">{{ pointReasonLabel(row.reason) }}</p>
                <span class="ledger-balance">余额 {{ row.balance_after }}</span>
              </template>
              <template #delta="{ row }">
                <span :class="row.delta >= 0 ? 'plus' : 'minus'">{{ formatDelta(row.delta) }}</span>
              </template>
              <template #time="{ row }">{{ formatTime(row.created_at) }}</template>
              <template #reason="{ row }">{{ pointReasonLabel(row.reason) }}</template>
            </LedgerList>
          </el-tab-pane>
          <el-tab-pane label="可用积分" name="redeem">
            <LedgerList :rows="redeemPointLedger" :columns="pointColumns" empty-text="暂无流水">
              <template #mobile="{ row }">
                <div class="ledger-card-head">
                  <span class="ledger-delta" :class="row.delta >= 0 ? 'plus' : 'minus'">
                    {{ formatDelta(row.delta) }}
                  </span>
                  <span class="ledger-time">{{ formatTime(row.created_at) }}</span>
                </div>
                <p class="ledger-reason">{{ pointReasonLabel(row.reason) }}</p>
                <span class="ledger-balance">余额 {{ row.balance_after }}</span>
              </template>
              <template #delta="{ row }">
                <span :class="row.delta >= 0 ? 'plus' : 'minus'">{{ formatDelta(row.delta) }}</span>
              </template>
              <template #time="{ row }">{{ formatTime(row.created_at) }}</template>
              <template #reason="{ row }">{{ pointReasonLabel(row.reason) }}</template>
            </LedgerList>
          </el-tab-pane>
        </el-tabs>
      </el-tab-pane>

      <el-tab-pane label="球迷币" name="coins">
        <LedgerList :rows="coinLedger" :columns="coinColumns" empty-text="暂无流水">
          <template #mobile="{ row }">
            <div class="ledger-card-head">
              <span class="ledger-delta" :class="row.delta >= 0 ? 'plus' : 'minus'">
                {{ formatDelta(row.delta) }}
              </span>
              <span class="ledger-time">{{ formatTime(row.created_at) }}</span>
            </div>
            <p class="ledger-reason">{{ walletReasonLabel(row.reason) }}</p>
            <span class="ledger-balance">余额 {{ row.balance_after }}</span>
          </template>
          <template #delta="{ row }">
            <span :class="row.delta >= 0 ? 'plus' : 'minus'">{{ formatDelta(row.delta) }}</span>
          </template>
          <template #time="{ row }">{{ formatTime(row.created_at) }}</template>
          <template #reason="{ row }">{{ walletReasonLabel(row.reason) }}</template>
        </LedgerList>
      </el-tab-pane>

      <el-tab-pane label="兑换" name="redeem-orders">
        <LedgerList :rows="redeemOrders" :columns="redeemColumns" empty-text="暂无兑换">
          <template #mobile="{ row }">
            <strong class="ledger-title">{{ row.product_name }}</strong>
            <p class="ledger-reason">消耗 {{ row.redeem_price }} 可用积分</p>
            <span class="ledger-time">{{ formatTime(row.created_at ?? null) }}</span>
          </template>
          <template #time="{ row }">{{ formatTime(row.created_at ?? null) }}</template>
        </LedgerList>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import LedgerList from './LedgerList.vue'
import type { GamePrediction, CoinLedgerEntry, PointLedgerEntry, RedeemOrder } from '../../api/commerce'
import {
  formatLedgerTime,
  pointReasonLabel,
  walletReasonLabel,
} from '../../constants/walletReasonLabels'
import { useBreakpoint } from '../../composables/useBreakpoint'

const props = defineProps<{
  predictions: GamePrediction[]
  coinLedger: CoinLedgerEntry[]
  seasonPointLedger: PointLedgerEntry[]
  redeemPointLedger: PointLedgerEntry[]
  redeemOrders: RedeemOrder[]
  focusKey?: string | null
}>()

const { isMobile } = useBreakpoint()
const subTab = ref('predictions')
const pointSubTab = ref('season')

const mainTabItems = [
  { name: 'predictions', label: '竞猜' },
  { name: 'points', label: '积分' },
  { name: 'coins', label: '球迷币' },
  { name: 'redeem-orders', label: '兑换' },
]

const pointTabItems = [
  { name: 'season', label: '累计积分' },
  { name: 'redeem', label: '可用积分' },
]

const formatTime = formatLedgerTime

function formatDelta(delta: number) {
  if (delta > 0) return `+${delta}`
  return String(delta)
}

function statusClass(status?: string) {
  if (status === 'won') return 'status-won'
  if (status === 'lost') return 'status-lost'
  if (status === 'void') return 'status-void'
  if (status === 'pending') return 'status-pending'
  return ''
}

const predictionColumns = [
  { label: '对阵', minWidth: 160, slot: 'match' },
  { label: '我的选择', width: 100, slot: 'pick' },
  { label: '质押/返币', width: 110, slot: 'stake' },
  { label: '状态', width: 90, slot: 'status' },
  { label: '赛果', width: 70, slot: 'final' },
  { label: '累计积分', width: 90, slot: 'seasonPts' },
  { label: '可用积分', width: 90, slot: 'redeemPts' },
]

const pointColumns = [
  { label: '时间', width: 160, slot: 'time' },
  { label: '变动', width: 90, slot: 'delta' },
  { label: '原因', slot: 'reason' },
  { prop: 'balance_after', label: '余额', width: 80 },
]

const coinColumns = [
  { label: '时间', width: 160, slot: 'time' },
  { label: '变动', width: 90, slot: 'delta' },
  { label: '原因', slot: 'reason' },
  { prop: 'balance_after', label: '余额', width: 80 },
]

const redeemColumns = [
  { prop: 'product_name', label: '商品', minWidth: 140 },
  { prop: 'redeem_price', label: '消耗积分', width: 100 },
  { label: '时间', width: 160, slot: 'time' },
]

watch(
  () => props.focusKey,
  (focus) => {
    if (focus === 'predictions') subTab.value = 'predictions'
  },
  { immediate: true },
)
</script>

<style scoped>
.uc-records {
  padding: 4px 0 8px;
}

.records-segment {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding-bottom: 12px;
  margin-bottom: 4px;
  -webkit-overflow-scrolling: touch;
}

.records-segment--sub {
  margin-top: 4px;
  margin-bottom: 10px;
}

.seg-btn {
  flex-shrink: 0;
  padding: 9px 14px;
  border-radius: 999px;
  border: 1px solid rgba(212, 165, 116, 0.28);
  background: rgba(10, 12, 24, 0.72);
  color: rgba(255, 255, 255, 0.72);
  font-size: 0.82rem;
  font-weight: 600;
  cursor: pointer;
}

.seg-btn--sub {
  font-size: 0.78rem;
  padding: 8px 12px;
}

.seg-btn.active {
  color: #1a1208;
  border-color: rgba(212, 165, 116, 0.55);
  background: linear-gradient(135deg, #f0d9b5 0%, var(--wc-accent-gold) 100%);
}

.records-tabs.hide-header :deep(.el-tabs__header),
.point-sub-tabs.hide-header :deep(.el-tabs__header) {
  display: none;
}

.records-tabs :deep(.el-tabs__content),
.point-sub-tabs :deep(.el-tabs__content) {
  overflow: visible;
}

.records-tabs :deep(.el-tabs__nav-wrap),
.point-sub-tabs :deep(.el-tabs__nav-wrap) {
  overflow-x: auto;
}

.records-tabs :deep(.el-tabs__item),
.point-sub-tabs :deep(.el-tabs__item) {
  font-weight: 600;
}

.focus-flash {
  animation: focusPulse 2s ease;
  border-radius: 10px;
}

@keyframes focusPulse {
  0%, 100% { box-shadow: none; }
  20%, 60% { box-shadow: 0 0 0 2px rgba(212, 165, 116, 0.7), 0 0 24px rgba(212, 165, 116, 0.35); }
}

.status-won { color: #8fd48a; }
.status-lost { color: #f89898; }
.status-void { color: #79bbff; }
.status-pending { color: #e6a23c; }
</style>
