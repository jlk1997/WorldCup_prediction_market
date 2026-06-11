<template>
  <div class="uc-records">
    <el-tabs v-model="subTab" class="records-tabs">
      <el-tab-pane label="竞猜" name="predictions">
        <div id="predictions-section" :class="{ 'focus-flash': focusKey === 'predictions' }">
          <LedgerList :rows="predictions" :columns="predictionColumns" empty-text="暂无竞猜记录">
            <template #mobile="{ row }">
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
            </template>
            <template #match="{ row }">{{ row.team1 || '?' }} vs {{ row.team2 || '?' }}</template>
            <template #pick="{ row }">{{ row.pick_label || row.pick }}</template>
            <template #stake="{ row }">
              <span v-if="row.is_free">免费</span>
              <span v-else>{{ row.stake_coins }} 币</span>
              <span v-if="row.coins_returned > 0" class="return-coins"> +{{ row.coins_returned }}</span>
            </template>
            <template #status="{ row }">{{ row.status_label || row.status }}</template>
            <template #final="{ row }">{{ row.final_score || '—' }}</template>
            <template #seasonPts="{ row }">
              <span v-if="row.status === 'won' && row.points_awarded">+{{ row.points_awarded }}</span>
              <span v-else>—</span>
            </template>
            <template #redeemPts="{ row }">
              <span v-if="row.status === 'won' && row.redeem_points_awarded" class="redeem-pts">+{{ row.redeem_points_awarded }}</span>
              <span v-else>—</span>
            </template>
          </LedgerList>
        </div>
      </el-tab-pane>

      <el-tab-pane label="积分" name="points">
        <el-tabs v-model="pointSubTab" class="point-sub-tabs">
          <el-tab-pane label="累计积分" name="season">
            <LedgerList :rows="seasonPointLedger" :columns="pointColumns" empty-text="暂无流水">
              <template #mobile="{ row }">
                <div class="ledger-card-head">
                  <span :class="row.delta >= 0 ? 'plus' : 'minus'">{{ row.delta >= 0 ? '+' : '' }}{{ row.delta }}</span>
                  <span class="ledger-time">{{ formatTime(row.created_at) }}</span>
                </div>
                <p class="ledger-reason">{{ pointReasonLabel(row.reason) }}</p>
                <span class="ledger-balance">余额 {{ row.balance_after }}</span>
              </template>
              <template #delta="{ row }">
                <span :class="row.delta >= 0 ? 'plus' : 'minus'">{{ row.delta >= 0 ? '+' : '' }}{{ row.delta }}</span>
              </template>
              <template #time="{ row }">{{ formatTime(row.created_at) }}</template>
              <template #reason="{ row }">{{ pointReasonLabel(row.reason) }}</template>
            </LedgerList>
          </el-tab-pane>
          <el-tab-pane label="可用积分" name="redeem">
            <LedgerList :rows="redeemPointLedger" :columns="pointColumns" empty-text="暂无流水">
              <template #mobile="{ row }">
                <div class="ledger-card-head">
                  <span :class="row.delta >= 0 ? 'plus' : 'minus'">{{ row.delta >= 0 ? '+' : '' }}{{ row.delta }}</span>
                  <span class="ledger-time">{{ formatTime(row.created_at) }}</span>
                </div>
                <p class="ledger-reason">{{ pointReasonLabel(row.reason) }}</p>
                <span class="ledger-balance">余额 {{ row.balance_after }}</span>
              </template>
              <template #delta="{ row }">
                <span :class="row.delta >= 0 ? 'plus' : 'minus'">{{ row.delta >= 0 ? '+' : '' }}{{ row.delta }}</span>
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
              <span :class="row.delta >= 0 ? 'plus' : 'minus'">{{ row.delta >= 0 ? '+' : '' }}{{ row.delta }}</span>
              <span class="ledger-time">{{ formatTime(row.created_at) }}</span>
            </div>
            <p class="ledger-reason">{{ walletReasonLabel(row.reason) }}</p>
            <span class="ledger-balance">余额 {{ row.balance_after }}</span>
          </template>
          <template #delta="{ row }">
            <span :class="row.delta >= 0 ? 'plus' : 'minus'">{{ row.delta >= 0 ? '+' : '' }}{{ row.delta }}</span>
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

const props = defineProps<{
  predictions: GamePrediction[]
  coinLedger: CoinLedgerEntry[]
  seasonPointLedger: PointLedgerEntry[]
  redeemPointLedger: PointLedgerEntry[]
  redeemOrders: RedeemOrder[]
  focusKey?: string | null
}>()

const subTab = ref('predictions')
const pointSubTab = ref('season')

const formatTime = formatLedgerTime

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
  padding: 4px 0;
}

.records-tabs :deep(.el-tabs__nav-wrap),
.point-sub-tabs :deep(.el-tabs__nav-wrap) {
  overflow-x: auto;
}

.focus-flash {
  animation: focusPulse 2s ease;
  border-radius: 10px;
}

@keyframes focusPulse {
  0%, 100% { box-shadow: none; }
  20%, 60% { box-shadow: 0 0 0 2px rgba(212, 165, 116, 0.7), 0 0 24px rgba(212, 165, 116, 0.35); }
}
</style>
