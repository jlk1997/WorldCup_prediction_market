<template>
  <div class="payment-result has-bottom-nav">
    <div class="result-card glass-panel" :class="`state-${phase}`">
      <!-- 处理中 -->
      <template v-if="phase === 'processing'">
        <div class="status-icon processing">
          <div class="spinner" />
        </div>
        <h1>正在确认支付结果</h1>
        <p class="lead">请稍候，系统正在核对您的订单…</p>
      </template>

      <!-- 成功 -->
      <template v-else-if="phase === 'success' && order">
        <div class="status-icon success">
          <svg viewBox="0 0 52 52" aria-hidden="true">
            <circle class="check-circle" cx="26" cy="26" r="24" fill="none" />
            <path class="check-mark" fill="none" d="M14 27l8 8 16-18" />
          </svg>
        </div>
        <h1>{{ successTitle }}</h1>
        <p v-if="isMintOrder && order.mint_serial_no" class="pass-success-lead">
          序列号 #{{ order.mint_serial_no }} · {{ chainStatusLabel }}
        </p>
        <div v-if="isMintOrder && mintChainDetail" class="chain-result glass-inner">
          <p v-if="mintChainDetail.chain_nft_id">
            NFT ID：<span class="mono">{{ mintChainDetail.chain_nft_id }}</span>
          </p>
          <p v-if="mintChainDetail.chain_tx_hash">
            Tx：<span class="mono">{{ shortTx(mintChainDetail.chain_tx_hash) }}</span>
          </p>
          <p v-if="chainStatus === 'failed'" class="chain-fail-hint">可在收藏册一键重试铸造</p>
        </div>
        <p v-else-if="isPassOrder" class="pass-success-lead">
          尊享轨道已开启 · 已达等级奖励可一键领取（确定性发放，非盲盒）
        </p>
        <p class="amount">¥{{ (order.amount_fen / 100).toFixed(2) }}</p>

        <div class="summary glass-inner">
          <div class="row">
            <span>商品</span>
            <strong>{{ order.product_name }}</strong>
          </div>
          <ul v-if="grantLines.length" class="grant-summary">
            <li v-for="(line, idx) in grantLines" :key="idx">{{ line }}</li>
          </ul>
          <EntitlementPreview
            v-if="showEntitlementPreview"
            class="result-preview"
            :avatar-frame="previewFrame"
            :theme-key="previewTheme"
            :grants="[]"
            :nickname="authState.user?.nickname"
            compact
          />
          <div class="row">
            <span>订单号</span>
            <strong class="mono">{{ order.out_trade_no }}</strong>
          </div>
          <div v-if="order.paid_at" class="row">
            <span>支付时间</span>
            <strong>{{ formatTime(order.paid_at) }}</strong>
          </div>
        </div>

        <div v-if="authState.user" class="balance-bar" :class="{ pulse: balancePulse }">
          当前余额：<strong>{{ authState.user.fan_coins }}</strong> 球迷币
        </div>

        <div class="actions">
          <el-button
            v-if="isMintOrder"
            type="primary"
            class="action-btn"
            @click="goCollection"
          >
            查看我的球星卡
          </el-button>
          <el-button
            v-if="isMintOrder"
            class="action-btn"
            @click="goCardDuel"
          >
            去卡牌对决
          </el-button>
          <el-button
            v-if="isPassOrder"
            type="primary"
            class="action-btn"
            @click="goCollectionPass"
          >
            领取手册奖励
          </el-button>
          <el-button v-else-if="!isMintOrder" type="primary" class="action-btn" @click="goMe">查看我的权益</el-button>
          <el-button
            v-if="order.product_type === 'collection_pass' && !isPassOrder"
            class="action-btn"
            @click="goCollectionPass"
          >
            打开藏品手册
          </el-button>
          <el-button v-if="order.product_type === 'cosmetic'" class="action-btn" @click="goFanCard">
            查看球迷名片
          </el-button>
          <el-button class="action-btn" @click="goShop">{{ isMintOrder ? '继续打新' : '继续逛逛' }}</el-button>
        </div>
      </template>

      <!-- 处理中（轮询超时） -->
      <template v-else-if="phase === 'pending'">
        <div class="status-icon pending">⏳</div>
        <h1>支付处理中</h1>
        <p class="lead">到账可能稍有延迟，请稍后刷新或返回查看订单。</p>
        <p v-if="order" class="order-hint">订单号：{{ order.out_trade_no }}</p>
        <div class="actions">
          <el-button type="primary" class="action-btn" :loading="refreshing" @click="refreshStatus">
            刷新状态
          </el-button>
          <el-button v-if="order?.status === 'pending'" class="action-btn" :loading="cancelling" @click="cancelPending">
            取消订单
          </el-button>
          <el-button class="action-btn" @click="goShop">返回商城</el-button>
        </div>
      </template>

      <!-- 失败 -->
      <template v-else>
        <div class="status-icon failed">!</div>
        <h1>{{ failTitle }}</h1>
        <p class="lead">{{ failMessage }}</p>
        <div class="actions">
          <el-button type="primary" class="action-btn" @click="goShop">返回商城</el-button>
          <el-button v-if="order?.out_trade_no" class="action-btn" @click="retryPay">重新购买</el-button>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { authState, fetchMe } from '../stores/authStore'
import {
  cancelOrder,
  getOrderByTradeNo,
  mockPay,
  pollOrderUntilPaid,
  resolvePaidOrder,
  type OrderDetail,
} from '../api/commerce'
import { getErrorMessage, isRateLimitError } from '../api/client'
import { showApiError } from '../utils/errorHandler'
import { useStadiumStore } from '../stores/stadiumStore'
import EntitlementPreview from '../components/EntitlementPreview.vue'
import { buildOrderGrantSummary } from '../utils/entitlements'
import { clearPendingOrder, resolveOutTradeNo } from '../utils/payEnv'
import { getUserCardChainStatus } from '../api/collectible'

type Phase = 'processing' | 'success' | 'pending' | 'failed'

const route = useRoute()
const router = useRouter()
const { setUiOverlay } = useStadiumStore()

const phase = ref<Phase>('processing')
const order = ref<OrderDetail | null>(null)
const failTitle = ref('支付未完成')
const failMessage = ref('请返回商城重试，或联系客服。')
const refreshing = ref(false)
const cancelling = ref(false)
const balancePulse = ref(false)
const chainStatus = ref<string>('pending')
const mintChainDetail = ref<{
  chain_nft_id: string | null
  chain_tx_hash: string | null
} | null>(null)
let chainPollTimer: ReturnType<typeof setInterval> | null = null

const CHAIN_LABELS: Record<string, string> = {
  none: '等待排队铸造',
  pending: '链上铸造排队中',
  minting: '链上铸造中…',
  minted: '文昌链凭证已就绪',
  failed: '链上铸造失败，可在收藏册重试',
}

const chainStatusLabel = computed(() => CHAIN_LABELS[chainStatus.value] || '链上铸造处理中')

const grantLines = computed(() => (order.value ? buildOrderGrantSummary(order.value) : []))
const isMintOrder = computed(() => order.value?.product_type === 'mint_event')
const isPassOrder = computed(() => order.value?.product_type === 'collection_pass')
const successTitle = computed(() => {
  if (isMintOrder.value) return '打新成功'
  if (isPassOrder.value) return '尊享手册已解锁'
  return '支付成功'
})
const showEntitlementPreview = computed(
  () => order.value?.product_type === 'season_pass' || order.value?.product_type === 'cosmetic',
)
const previewFrame = computed(() => {
  if (order.value?.product_type === 'cosmetic') return authState.user?.avatar_frame ?? 'gold_wc'
  return authState.user?.avatar_frame ?? null
})
const previewTheme = computed(() => {
  if (order.value?.product_type === 'cosmetic') return authState.user?.theme_key ?? 'team_spirit'
  return authState.user?.theme_key ?? null
})

const isDev = !import.meta.env.PROD

function runResolve() {
  phase.value = 'processing'
  void resolvePayment()
}

onMounted(() => {
  setUiOverlay('shop-payment-result', true)
  runResolve()
})

watch(
  () => route.query.out_trade_no,
  (next, prev) => {
    if (next && next !== prev) runResolve()
  },
)

onUnmounted(() => {
  setUiOverlay('shop-payment-result', false)
  stopChainPoll()
})

function stopChainPoll() {
  if (chainPollTimer) {
    clearInterval(chainPollTimer)
    chainPollTimer = null
  }
}

async function pollMintChain(userCardId: number) {
  try {
    const st = await getUserCardChainStatus(userCardId)
    chainStatus.value = st.chain_status || 'pending'
    mintChainDetail.value = {
      chain_nft_id: st.chain_nft_id,
      chain_tx_hash: st.chain_tx_hash,
    }
    if (st.chain_status === 'minted' || st.chain_status === 'failed') {
      stopChainPoll()
    }
  } catch {
    /* ignore transient errors */
  }
}

function shortTx(hash: string) {
  if (hash.length <= 16) return hash
  return `${hash.slice(0, 8)}…${hash.slice(-6)}`
}

function startChainPoll(userCardId: number | null | undefined) {
  stopChainPoll()
  if (!userCardId) return
  void pollMintChain(userCardId)
  chainPollTimer = setInterval(() => void pollMintChain(userCardId), 4000)
}

function formatTime(iso: string) {
  try {
    return new Date(iso).toLocaleString('zh-CN', { hour12: false })
  } catch {
    return iso
  }
}

function clearQuery() {
  if (route.query.out_trade_no || route.query.mock) {
    router.replace({ path: '/shop/result' })
  }
}

async function afterSuccess(detail: OrderDetail) {
  order.value = detail
  phase.value = 'success'
  clearPendingOrder()
  try {
    sessionStorage.removeItem('wc_mint_return')
  } catch {
    /* ignore */
  }
  await fetchMe()
  if (detail.product_type === 'mint_event' && detail.mint_user_card_id) {
    startChainPoll(detail.mint_user_card_id)
  }
  balancePulse.value = true
  setTimeout(() => {
    balancePulse.value = false
  }, 1800)
  clearQuery()
}

async function resolvePayment() {
  const outTradeNo = resolveOutTradeNo(route.query as Record<string, unknown>)
  const isMock = route.query.mock === '1'

  if (!outTradeNo) {
    // 无 query：若已有 paid 订单缓存则展示，否则失败
    phase.value = 'failed'
    failTitle.value = '缺少订单信息'
    failMessage.value = '未找到支付订单，请从商城重新发起购买。'
    return
  }

  phase.value = 'processing'

  try {
    if (isMock && isDev) {
      const detail = await mockPay(outTradeNo)
      await afterSuccess(detail)
      return
    }

    // 已支付单直接展示（避免重复 mock）
    const existing = await getOrderByTradeNo(outTradeNo)
    if (existing.status === 'paid') {
      await afterSuccess(existing)
      return
    }

    const result = await pollOrderUntilPaid(outTradeNo)
    if (result.ok) {
      await afterSuccess(result.order)
      return
    }

    order.value = result.order ?? null
    if (result.reason === 'timeout') {
      phase.value = 'pending'
      clearQuery()
      return
    }

    phase.value = 'failed'
    failTitle.value = '支付失败'
    failMessage.value = '订单未支付成功，请返回商城重新购买。'
    clearQuery()
  } catch (e) {
    showApiError(e)
    if (!(isRateLimitError(e) && e.notified)) {
      phase.value = 'failed'
      failTitle.value = '无法确认支付'
      failMessage.value = getErrorMessage(e)
    }
    clearQuery()
  }
}

async function refreshStatus() {
  const outTradeNo = order.value?.out_trade_no ?? resolveOutTradeNo(route.query as Record<string, unknown>)
  if (!outTradeNo) return
  refreshing.value = true
  try {
    const paid = await resolvePaidOrder(outTradeNo)
    if (paid) {
      await afterSuccess(paid)
      return
    }
    const detail = await getOrderByTradeNo(outTradeNo)
    order.value = detail
  } catch (e) {
    showApiError(e)
    if (!(isRateLimitError(e) && e.notified)) {
      failMessage.value = getErrorMessage(e)
    }
  } finally {
    refreshing.value = false
  }
}

function goShop() {
  router.push('/shop')
}

function goMe() {
  router.push({ path: '/me', hash: '#entitlements' })
}

function goFanCard() {
  router.push('/me/card')
}

function goCollectionPass() {
  router.push('/collection?tab=pass')
}

function goCollection() {
  router.push('/collection')
}

function goCardDuel() {
  router.push('/arena#duel')
}

async function cancelPending() {
  const outTradeNo = order.value?.out_trade_no ?? resolveOutTradeNo(route.query as Record<string, unknown>)
  if (!outTradeNo) return
  cancelling.value = true
  try {
    await cancelOrder(outTradeNo)
    phase.value = 'failed'
    failTitle.value = '订单已取消'
    failMessage.value = '库存已释放，可重新发起打新或购买。'
    clearPendingOrder()
  } catch (e) {
    showApiError(e)
  } finally {
    cancelling.value = false
  }
}

function retryPay() {
  if (sessionStorage.getItem('wc_mint_return')) {
    router.push('/mint')
    return
  }
  router.push('/shop')
}
</script>

<style scoped>
.payment-result {
  min-height: calc(100dvh - var(--wc-header-height, 64px));
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px 16px calc(24px + var(--wc-bottom-nav-height, 0px) + env(safe-area-inset-bottom, 0px));
}

.result-card {
  width: min(480px, 100%);
  padding: 28px 24px 24px;
  text-align: center;
  border: 1px solid rgba(212, 165, 116, 0.28);
}

.status-icon {
  margin: 0 auto 16px;
  width: 72px;
  height: 72px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.status-icon.processing .spinner {
  width: 52px;
  height: 52px;
  border: 3px solid rgba(212, 165, 116, 0.2);
  border-top-color: var(--wc-accent-gold);
  border-radius: 50%;
  animation: spin 0.85s linear infinite;
}

.status-icon.success svg {
  width: 72px;
  height: 72px;
}

.check-circle {
  stroke: rgba(103, 194, 58, 0.35);
  stroke-width: 2;
}

.check-mark {
  stroke: #67c23a;
  stroke-width: 3.5;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-dasharray: 48;
  stroke-dashoffset: 48;
  animation: drawCheck 0.55s ease forwards 0.15s;
}

.status-icon.pending,
.status-icon.failed {
  font-size: 2.2rem;
  font-weight: 900;
  border-radius: 50%;
  background: rgba(212, 165, 116, 0.12);
  color: var(--wc-accent-gold);
}

.status-icon.failed {
  color: #f56c6c;
  background: rgba(245, 108, 108, 0.12);
}

h1 {
  margin: 0 0 8px;
  font-size: 1.35rem;
  color: #f5f0e8;
}

.pass-success-lead {
  margin: 0 0 12px;
  font-size: 0.82rem;
  color: #7eb8ff;
  line-height: 1.5;
}

.chain-result {
  text-align: left;
  margin: 0 0 14px;
  padding: 10px 12px;
  border-radius: 8px;
  font-size: 0.78rem;
  color: var(--wc-text-muted);
  line-height: 1.55;
}

.chain-result p {
  margin: 0 0 4px;
}

.chain-result p:last-child {
  margin-bottom: 0;
}

.chain-result .mono {
  color: #c8e6ff;
  word-break: break-all;
}

.chain-fail-hint {
  color: #f0b86c !important;
  margin-top: 6px !important;
}

.amount {
  margin: 0 0 18px;
  font-size: 2rem;
  font-weight: 800;
  color: var(--wc-accent-gold);
}

.lead {
  margin: 0 0 20px;
  font-size: 0.9rem;
  color: var(--wc-text-muted);
  line-height: 1.55;
}

.order-hint {
  font-size: 0.78rem;
  color: var(--wc-text-muted);
  margin: -8px 0 16px;
  word-break: break-all;
}

.summary {
  text-align: left;
  padding: 14px 16px;
  border-radius: 10px;
  margin-bottom: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  font-size: 0.85rem;
  color: var(--wc-text-muted);
}

.row strong {
  color: #f0e6d8;
  text-align: right;
  font-weight: 600;
}

.row .mono {
  font-size: 0.72rem;
  word-break: break-all;
  max-width: 62%;
}

.row.highlight .grant {
  color: var(--wc-accent-rose);
  font-size: 0.95rem;
}

.grant-summary {
  margin: 0;
  padding: 10px 12px;
  border-radius: 8px;
  background: rgba(103, 194, 58, 0.08);
  list-style: none;
  text-align: left;
}

.grant-summary li {
  font-size: 0.84rem;
  color: #d4edda;
  line-height: 1.55;
  padding-left: 1rem;
  position: relative;
}

.grant-summary li::before {
  content: '✓';
  position: absolute;
  left: 0;
  color: #67c23a;
  font-weight: 700;
}

.result-preview {
  margin: 4px 0 8px;
  justify-content: flex-start;
}

.balance-bar {
  margin-bottom: 18px;
  padding: 10px 14px;
  border-radius: 8px;
  background: rgba(212, 165, 116, 0.1);
  font-size: 0.88rem;
  color: var(--wc-text-muted);
  transition: background 0.3s, transform 0.3s;
}

.balance-bar strong {
  color: var(--wc-accent-gold);
  font-size: 1.05rem;
}

.balance-bar.pulse {
  background: rgba(103, 194, 58, 0.15);
  transform: scale(1.02);
}

.balance-bar.pulse strong {
  color: #67c23a;
}

.actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.action-btn {
  flex: 1;
  min-width: 140px;
  min-height: 44px;
  margin: 0 !important;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@keyframes drawCheck {
  to {
    stroke-dashoffset: 0;
  }
}

@media (max-width: 768px) {
  .payment-result {
    align-items: flex-start;
    padding-top: 24px;
  }

  .actions {
    flex-direction: column;
  }

  .action-btn {
    width: 100%;
    min-width: 0;
  }
}
</style>
