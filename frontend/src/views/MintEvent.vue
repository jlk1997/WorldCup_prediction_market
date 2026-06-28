<template>
  <div class="mint-page">
    <div class="page-header">
      <h1>首发打新</h1>
      <p class="subtitle">限量发行 · 序列号稀缺 · 错过即绝版。球星卡为站内虚拟藏品，无现金价值、不可提现</p>
    </div>

    <div v-if="loading" class="mint-list">
      <el-skeleton v-for="i in 3" :key="i" :rows="4" animated class="sk-card" />
    </div>
    <div v-else-if="!events.length" class="empty-state glass-inner">
      <p>暂无打新活动</p>
      <span>新赛事限量球星卡即将开售，敬请关注</span>
    </div>
    <div v-else class="mint-list">
      <div v-for="ev in events" :key="ev.id" :id="'mint-event-' + ev.id" class="mint-card glass-inner" :class="[ev.rarity, { collab: isCollab(ev), matchday: isMatchday(ev), highlighted: highlightId === ev.id }]">
        <div class="mint-banner" :style="ev.image_url ? { backgroundImage: `url(${ev.image_url})` } : {}">
          <span class="phase" :class="ev.phase">{{ phaseLabel(ev) }}</span>
          <span v-if="isCollab(ev)" class="collab-tag">联名/IP</span>
          <span v-else-if="isMatchday(ev)" class="matchday-tag">比赛日限定</span>
          <span v-else-if="ev.competition" class="comp">{{ ev.competition }}</span>
        </div>
        <div class="mint-body">
          <div class="title-row">
            <h3>{{ ev.name }}</h3>
            <span class="rarity" :class="ev.rarity">{{ rarityLabel(ev.rarity) }}</span>
          </div>
          <p class="desc">{{ ev.description }}</p>
          <div v-if="advisors[ev.id]" class="mint-advisor glass-inner">
            <span class="adv-verdict">{{ advisors[ev.id]?.verdict }}</span>
            <ul>
              <li v-for="(b, bi) in advisors[ev.id]?.bullets" :key="bi">{{ b }}</li>
            </ul>
            <p class="adv-disclaimer">{{ advisors[ev.id]?.disclaimer }}</p>
          </div>

          <div class="time-row">
            <span v-if="ev.phase === 'scheduled' && ev.reserve_starts_at" class="time-chip">
              {{ timeUntil(ev.reserve_starts_at, '预约开启') }}
            </span>
            <span v-else-if="ev.phase === 'reserving'" class="time-chip reserving">
              {{ timeUntil(ev.starts_at, '开售') }}
            </span>
            <span v-else-if="ev.phase === 'live'" class="time-chip live">
              {{ timeUntil(ev.ends_at, '结束') }}
            </span>
            <span v-if="ev.per_user_limit" class="limit-chip">限购 {{ ev.per_user_limit }} 张/人</span>
          </div>

          <div class="supply">
            <div class="supply-bar">
              <div class="supply-fill" :style="{ width: `${(ev.issued / ev.total_supply) * 100}%` }" />
            </div>
            <div class="supply-meta">
              <span>已发行 {{ ev.issued }} / {{ ev.total_supply }}</span>
              <span class="remain">剩余 {{ ev.remaining }}</span>
            </div>
          </div>

          <div class="mint-foot">
            <div class="price">
              <template v-if="ev.currency === 'coins'">
                <b>{{ ev.price_coins }}</b><span>球迷币</span>
              </template>
              <template v-else>
                <b>¥{{ (ev.price_fen / 100).toFixed(2) }}</b><span>人民币首发</span>
              </template>
              <span class="mode-tag">{{ modeLabel(ev.sale_mode) }}</span>
            </div>
            <div class="actions">
              <el-button
                v-if="ev.phase === 'reserving' || (ev.phase === 'scheduled' && ev.sale_mode !== 'public')"
                size="small"
                :type="ev.reserved ? 'success' : 'primary'"
                plain
                :disabled="ev.reserved"
                :loading="actingId === ev.id"
                @click="doReserve(ev)"
              >
                {{ ev.reserved ? '已预约' : '预约/报名' }}
              </el-button>
              <el-button
                v-if="ev.phase === 'live' && ev.currency === 'coins'"
                size="small"
                type="primary"
                :disabled="!ev.can_buy || ev.remaining <= 0"
                :loading="actingId === ev.id"
                @click="doPurchase(ev)"
              >
                {{ purchaseLabel(ev) }}
              </el-button>
              <el-button
                v-if="ev.phase === 'live' && ev.currency === 'rmb'"
                size="small"
                type="primary"
                :disabled="(!ev.can_buy && !ev.pending_payment) || (ev.remaining <= 0 && !ev.pending_payment)"
                :loading="actingId === ev.id"
                @click="doRmbPurchase(ev)"
              >
                {{ rmbPurchaseLabel(ev) }}
              </el-button>
              <el-button
                v-else-if="ev.phase === 'live' && ev.currency !== 'coins' && ev.currency !== 'rmb'"
                size="small"
                disabled
              >
                即将开放
              </el-button>
              <span v-if="ev.phase === 'sold_out'" class="soldout">已售罄</span>
              <span v-if="ev.phase === 'ended'" class="ended">已结束</span>
            </div>
          </div>
          <p v-if="ev.currency === 'rmb'" class="rmb-alt">支付成功后自动分配序列号并排队链上铸造</p>
          <div v-if="ev.sale_mode === 'lottery' && ev.reserved && ev.reservation_status === 'reserved'" class="lottery-note pending">
            已报名，等待抽签结果…
          </div>
          <div v-else-if="ev.reservation_status === 'lost'" class="lottery-note lost">很遗憾未中签</div>
          <div v-else-if="ev.reservation_status === 'won'" class="lottery-note won">恭喜中签，快去打新！</div>
        </div>
      </div>
    </div>

    <!-- 球迷币打新成功：链铸造进度 -->
    <el-dialog
      v-model="chainDialogOpen"
      title="打新成功 · 链上凭证"
      width="min(380px, 92vw)"
      align-center
      append-to-body
      class="wc-dialog"
      @closed="stopChainPoll"
    >
      <p class="chain-dialog-lead">{{ chainDialogNotice }}</p>
      <p class="chain-dialog-status">{{ chainStatusLabel }}</p>
      <p v-if="mintChainDetail?.chain_nft_id" class="chain-dialog-row">
        NFT ID：<span class="mono">{{ mintChainDetail.chain_nft_id }}</span>
      </p>
      <p v-if="mintChainDetail?.chain_tx_hash" class="chain-dialog-row">
        Tx：<span class="mono">{{ shortTx(mintChainDetail.chain_tx_hash) }}</span>
      </p>
      <template #footer>
        <el-button @click="chainDialogOpen = false">关闭</el-button>
        <el-button type="primary" @click="goCollectionFromMint">查看收藏册</el-button>
      </template>
    </el-dialog>

    <p class="disclaimer">
      一级限量发行属合规数字藏品发售；二级流通仅支持站内可用积分计价，平台不支持人民币二级交易与提现。
    </p>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getMintEvents, reserveMint, purchaseMint, createMintOrder, getMintAdvisor, type MintEvent, type MintAdvisor } from '@/api/asset'
import { getUserCardChainStatus } from '@/api/collectible'
import { authState, fetchMe } from '@/stores/authStore'
import { extractApiError } from '@/utils/apiError'
import { usePageMeta } from '@/composables/usePageMeta'
import { useCountdownTick, formatTimeUntil } from '@/composables/useCountdown'
import { isWeChatBrowser, PENDING_ORDER_KEY, resolvePayChannel, WECHAT_PAY_HINT } from '@/utils/payEnv'

usePageMeta({
  title: '首发打新 — 最后一舞',
  description: '限量球星卡首发打新，序列号稀缺。站内虚拟藏品，无现金价值。',
  path: '/mint',
  noIndex: true,
})

const tick = useCountdownTick()
const route = useRoute()
const router = useRouter()
const loading = ref(false)
const events = ref<MintEvent[]>([])
const highlightId = ref<number | null>(null)
const advisors = ref<Record<number, MintAdvisor>>({})
const actingId = ref<number | null>(null)
const chainDialogOpen = ref(false)
const chainDialogNotice = ref('')
const chainStatus = ref('pending')
const mintChainDetail = ref<{ chain_nft_id: string | null; chain_tx_hash: string | null } | null>(null)
let chainPollTimer: ReturnType<typeof setInterval> | null = null

const CHAIN_LABELS: Record<string, string> = {
  none: '等待排队铸造',
  pending: '链上铸造排队中',
  minting: '链上铸造中…',
  minted: '文昌链凭证已就绪',
  failed: '链上铸造失败，可在收藏册重试',
}
const chainStatusLabel = computed(() => CHAIN_LABELS[chainStatus.value] || '链上铸造处理中')

const RARITY: Record<string, string> = { common: '普通', rare: '稀有', epic: '史诗', legend: '传奇' }
const MODE: Record<string, string> = { public: '公开发售', whitelist: '白名单', lottery: '抽签' }
const PHASE: Record<string, string> = {
  scheduled: '未开始',
  reserving: '预约中',
  live: '发售中',
  sold_out: '已售罄',
  ended: '已结束',
}
function rarityLabel(r: string) {
  return RARITY[r] || r
}
function modeLabel(m: string) {
  return MODE[m] || m
}
function phaseLabel(ev: MintEvent) {
  return PHASE[ev.phase] || ev.phase
}
function timeUntil(iso?: string | null, prefix = '还剩') {
  void tick.value
  return formatTimeUntil(iso, prefix)
}
function purchaseLabel(ev: MintEvent) {
  if (ev.currency !== 'coins') return '立即打新'
  if (ev.remaining <= 0) return '已售罄'
  if (ev.sale_mode === 'lottery' && ev.reservation_status !== 'won') return '待中签'
  if (ev.sale_mode === 'whitelist' && !ev.reserved) return '需预约'
  return '立即打新'
}

function rmbPurchaseLabel(ev: MintEvent) {
  if (ev.pending_payment) return '继续支付'
  if (ev.remaining <= 0) return '已售罄'
  if (ev.sale_mode === 'lottery' && ev.reservation_status !== 'won') return '待中签'
  if (ev.sale_mode === 'whitelist' && !ev.reserved) return '需预约'
  return '支付宝打新'
}

function isCollab(ev: MintEvent) {
  return ev.competition === 'Collab2026' || ev.code.startsWith('mint_collab_')
}

function isMatchday(ev: MintEvent) {
  return ev.competition === 'matchday_limited'
}

function scrollToHighlight() {
  const raw = route.params.id ?? route.query.highlight
  const id = parseInt(String(raw || ''), 10)
  if (!id) return
  highlightId.value = id
  nextTick(() => {
    document.getElementById(`mint-event-${id}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  })
}

function stopChainPoll() {
  if (chainPollTimer) {
    clearInterval(chainPollTimer)
    chainPollTimer = null
  }
}

function shortTx(hash: string) {
  if (hash.length <= 16) return hash
  return `${hash.slice(0, 8)}…${hash.slice(-6)}`
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

function startChainPoll(userCardId: number, notice: string) {
  stopChainPoll()
  chainDialogNotice.value = notice
  chainStatus.value = 'pending'
  mintChainDetail.value = null
  chainDialogOpen.value = true
  void pollMintChain(userCardId)
  chainPollTimer = setInterval(() => void pollMintChain(userCardId), 4000)
}

function goCollectionFromMint() {
  chainDialogOpen.value = false
  router.push('/collection')
}

async function load() {
  loading.value = true
  try {
    events.value = await getMintEvents()
    scrollToHighlight()
    if (authState.user) {
      const map: Record<number, MintAdvisor> = {}
      for (const ev of events.value.filter((e) => e.phase === 'live')) {
        try {
          map[ev.id] = await getMintAdvisor(ev.id)
        } catch {
          /* skip */
        }
      }
      advisors.value = map
    }
  } finally {
    loading.value = false
  }
}

async function doReserve(ev: MintEvent) {
  actingId.value = ev.id
  try {
    await reserveMint(ev.id)
    ElMessage.success('预约成功，开售/开奖后将通知你')
    await load()
  } catch (e: unknown) {
    ElMessage.error(extractApiError(e, '预约失败'))
  } finally {
    actingId.value = null
  }
}

async function doPurchase(ev: MintEvent) {
  try {
    await ElMessageBox.confirm(
      ev.currency === 'coins'
        ? `确认消耗 ${ev.price_coins} 球迷币打新「${ev.name}」？`
        : `确认以 ¥${(ev.price_fen / 100).toFixed(2)} 打新「${ev.name}」？`,
      '首发打新',
      { customClass: 'wc-message-box', roundButton: true, confirmButtonText: '确认打新', cancelButtonText: '再想想' },
    )
  } catch {
    return
  }
  actingId.value = ev.id
  try {
    const res = await purchaseMint(ev.id)
    ElMessage.success(`${res.notice} 序列号 #${res.serial_no ?? '—'}`)
    await fetchMe()
    await load()
    if (res.user_card_id) {
      startChainPoll(res.user_card_id, `${res.card_name} · #${res.serial_no ?? '—'}`)
    }
  } catch (e: unknown) {
    ElMessage.error(extractApiError(e, '打新失败'))
  } finally {
    actingId.value = null
  }
}

async function doRmbPurchase(ev: MintEvent) {
  if (isWeChatBrowser()) {
    ElMessage.warning(WECHAT_PAY_HINT)
    return
  }
  try {
    await ElMessageBox.confirm(
      `确认以 ¥${(ev.price_fen / 100).toFixed(2)} 打新「${ev.name}」？`,
      '人民币首发打新',
      { customClass: 'wc-message-box', roundButton: true, confirmButtonText: '去支付', cancelButtonText: '再想想' },
    )
  } catch {
    return
  }
  actingId.value = ev.id
  try {
    const { order, pay_url } = await createMintOrder(ev.id, true, resolvePayChannel())
    sessionStorage.setItem(PENDING_ORDER_KEY, order.out_trade_no)
    sessionStorage.setItem('wc_mint_return', '1')
    window.location.href = pay_url
  } catch (e: unknown) {
    ElMessage.error(extractApiError(e, '下单失败'))
  } finally {
    actingId.value = null
  }
}

onMounted(load)
onUnmounted(stopChainPoll)
</script>

<style scoped>
.mint-page {
  max-width: 760px;
  margin: 0 auto;
  padding-bottom: calc(var(--wc-bottom-nav-height, 56px) + 24px);
}
.page-header h1 {
  margin: 0 0 4px;
  font-size: 1.5rem;
  color: var(--wc-accent-gold);
}
.subtitle {
  margin: 0 0 16px;
  font-size: 0.82rem;
  color: var(--wc-text-muted);
}
.mint-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.mint-card {
  border-radius: 14px;
  overflow: hidden;
  border: 1px solid rgba(212, 165, 116, 0.2);
}
.mint-card.legend { border-color: rgba(231, 175, 92, 0.5); }
.mint-card.epic { border-color: rgba(168, 120, 224, 0.4); }
.mint-card.collab {
  border-color: rgba(255, 120, 180, 0.55);
  box-shadow: 0 0 24px rgba(255, 100, 160, 0.12);
}
.collab-tag {
  position: absolute;
  top: 10px;
  right: 10px;
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 0.68rem;
  font-weight: 600;
  background: linear-gradient(135deg, rgba(255, 120, 180, 0.85), rgba(168, 120, 224, 0.85));
  color: #fff;
}
.rmb-muted { opacity: 0.55; }
.rmb-alt {
  margin: 6px 0 0;
  font-size: 0.66rem;
  color: var(--wc-text-muted);
  line-height: 1.35;
}
.coming-soon {
  margin-left: 8px;
  font-size: 0.68rem;
  color: var(--wc-text-muted);
  padding: 2px 8px;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.06);
}
.mint-banner {
  position: relative;
  height: 130px;
  background: linear-gradient(135deg, rgba(40, 30, 20, 0.7), rgba(20, 16, 32, 0.95));
  background-size: cover;
  background-position: center;
}
.phase {
  position: absolute;
  top: 10px;
  left: 10px;
  font-size: 0.7rem;
  padding: 3px 10px;
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.55);
  color: #f0d9b5;
}
.phase.live {
  background: linear-gradient(90deg, #c0392b, #e74c3c);
  color: #fff;
  animation: pulse 1.6s infinite;
}
.phase.reserving { background: rgba(46, 134, 193, 0.85); color: #fff; }
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}
.comp {
  position: absolute;
  top: 10px;
  right: 10px;
  font-size: 0.66rem;
  padding: 3px 8px;
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.5);
  color: var(--wc-text-secondary);
}
.mint-body {
  padding: 14px 16px 16px;
}
.title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.title-row h3 {
  margin: 0;
  font-size: 1.05rem;
  color: var(--wc-text-secondary);
}
.rarity {
  font-size: 0.66rem;
  padding: 2px 8px;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.06);
  color: var(--wc-text-muted);
}
.rarity.legend { background: linear-gradient(90deg, #b8860b, #e7af5c); color: #1a1208; }
.rarity.epic { background: rgba(138, 80, 184, 0.85); color: #fff; }
.desc {
  margin: 6px 0 8px;
  font-size: 0.8rem;
  color: var(--wc-text-muted);
  line-height: 1.5;
}
.mint-advisor {
  margin: 8px 0;
  padding: 8px 10px;
  text-align: left;
  font-size: 0.75rem;
}
.adv-verdict {
  color: #a371f7;
  font-weight: 600;
}
.mint-advisor ul {
  margin: 6px 0;
  padding-left: 16px;
  color: var(--wc-text-secondary);
}
.adv-disclaimer {
  margin: 4px 0 0;
  font-size: 0.68rem;
  color: var(--wc-text-muted);
}
.time-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 10px;
}
.time-chip {
  font-size: 0.72rem;
  padding: 3px 10px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.06);
  color: var(--wc-text-muted);
}
.time-chip.reserving { color: #6eb5e0; }
.time-chip.live { color: #f0b86c; }
.limit-chip {
  font-size: 0.68rem;
  padding: 3px 8px;
  border-radius: 6px;
  background: rgba(212, 165, 116, 0.12);
  color: var(--wc-accent-gold);
}
.supply-bar {
  height: 8px;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.08);
  overflow: hidden;
}
.supply-fill {
  height: 100%;
  background: linear-gradient(90deg, #d4a574, #e7af5c);
  transition: width 0.4s;
}
.supply-meta {
  display: flex;
  justify-content: space-between;
  margin-top: 5px;
  font-size: 0.7rem;
  color: var(--wc-text-muted);
}
.supply-meta .remain {
  color: #f0b86c;
}
.mint-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 14px;
  gap: 10px;
}
.price {
  display: flex;
  align-items: baseline;
  gap: 4px;
  flex-wrap: wrap;
}
.price b {
  font-size: 1.3rem;
  color: var(--wc-accent-gold);
  font-variant-numeric: tabular-nums;
}
.price span {
  font-size: 0.7rem;
  color: var(--wc-text-muted);
}
.mode-tag {
  margin-left: 6px;
  padding: 2px 7px;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.06);
  font-size: 0.62rem !important;
}
.soldout, .ended {
  font-size: 0.8rem;
  color: var(--wc-text-muted);
}
.lottery-note {
  margin-top: 10px;
  font-size: 0.75rem;
  padding: 6px 10px;
  border-radius: 8px;
}
.lottery-note.pending { background: rgba(110, 181, 224, 0.12); color: #6eb5e0; }
.lottery-note.won { background: rgba(46, 160, 100, 0.15); color: #5fc88f; }
.lottery-note.lost { background: rgba(160, 70, 70, 0.12); color: #e07a7a; }
.mint-card.matchday {
  border-color: rgba(232, 120, 90, 0.35);
}
.mint-card.highlighted {
  box-shadow: 0 0 0 2px rgba(212, 165, 116, 0.55);
  animation: mint-pulse 2s ease-in-out 2;
}
@keyframes mint-pulse {
  0%, 100% { box-shadow: 0 0 0 2px rgba(212, 165, 116, 0.35); }
  50% { box-shadow: 0 0 0 4px rgba(212, 165, 116, 0.65); }
}
.matchday-tag {
  position: absolute;
  top: 10px;
  right: 10px;
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(232, 100, 70, 0.85);
  color: #fff;
  font-size: 0.68rem;
  font-weight: 700;
}
.empty-state {
  text-align: center;
  padding: 40px 20px;
  border-radius: 12px;
  color: var(--wc-text-muted);
}
.empty-state p {
  margin: 0 0 6px;
  font-size: 1rem;
  color: var(--wc-text-secondary);
}
.disclaimer {
  margin-top: 20px;
  font-size: 0.68rem;
  color: var(--wc-text-muted);
  line-height: 1.5;
  text-align: center;
}
.sk-card {
  padding: 14px;
  border-radius: 12px;
  background: rgba(20, 24, 42, 0.4);
}
.chain-dialog-lead {
  margin: 0 0 8px;
  font-size: 0.88rem;
  color: var(--wc-text-secondary);
}
.chain-dialog-status {
  margin: 0 0 10px;
  font-size: 0.82rem;
  color: #7eb8ff;
}
.chain-dialog-row {
  margin: 0 0 6px;
  font-size: 0.75rem;
  color: var(--wc-text-muted);
  word-break: break-all;
}
.chain-dialog-row .mono {
  color: #c8e6ff;
}
</style>
