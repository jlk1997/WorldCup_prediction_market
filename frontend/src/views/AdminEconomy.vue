<template>
  <div class="economy-page">
    <div class="page-header">
      <h1>经济健康看板</h1>
      <p class="subtitle">可用积分 faucet / sink · 交易行 · 质押 · 回购（运营调参）</p>
    </div>

    <div class="auth-bar glass-inner">
      <el-input
        v-model="adminSecret"
        type="password"
        placeholder="输入 Admin Secret（X-Admin-Secret）"
        show-password
        clearable
        @keyup.enter="load"
      />
      <el-select v-model="windowDays" size="default" style="width: 110px" @change="load">
        <el-option :value="7" label="近 7 天" />
        <el-option :value="14" label="近 14 天" />
        <el-option :value="30" label="近 30 天" />
      </el-select>
      <el-button type="primary" :loading="loading" @click="load">刷新</el-button>
    </div>

    <div v-if="loading && !data" class="sk-wrap">
      <el-skeleton v-for="i in 4" :key="i" :rows="3" animated class="sk-block" />
    </div>

    <template v-else-if="data">
      <div class="health glass-inner" :class="healthClass">
        <span class="health-label">经济健康</span>
        <p>{{ data.health_hint }}</p>
        <div class="health-metrics">
          <div><span>净流入</span><b :class="data.redeem_points.net_flow >= 0 ? 'up' : 'down'">{{ fmt(data.redeem_points.net_flow) }}</b></div>
          <div><span>通胀率</span><b>{{ data.redeem_points.inflation_pct }}%</b></div>
        </div>
      </div>

      <div class="metric-grid">
        <div class="metric glass-inner">
          <span>积分产出</span>
          <b class="up">+{{ fmt(data.redeem_points.total_in) }}</b>
        </div>
        <div class="metric glass-inner">
          <span>积分消耗</span>
          <b class="down">-{{ fmt(data.redeem_points.total_out) }}</b>
        </div>
        <div class="metric glass-inner">
          <span>交易成交额</span>
          <b>{{ fmt(data.marketplace.trade_volume) }}</b>
          <small>{{ data.marketplace.trade_count }} 笔</small>
        </div>
        <div class="metric glass-inner">
          <span>手续费 sink</span>
          <b>{{ fmt(data.marketplace.fee_sink) }}</b>
        </div>
        <div class="metric glass-inner">
          <span>官方回购</span>
          <b>{{ fmt(data.buyback_spend) }}</b>
        </div>
        <div class="metric glass-inner">
          <span>活跃挂牌</span>
          <b>{{ data.marketplace.active_listings }}</b>
        </div>
        <div class="metric glass-inner">
          <span>质押中</span>
          <b>{{ data.staking.active_stakes }}</b>
          <small>累计产出 {{ fmt(data.staking.total_yield_claimed) }}</small>
        </div>
        <div class="metric glass-inner">
          <span>转赠次数</span>
          <b>{{ data.gift_count }}</b>
        </div>
      </div>

      <div class="tables">
        <section class="glass-inner">
          <h3>积分产出（Faucet）</h3>
          <div v-if="!faucetRows.length" class="empty">暂无数据</div>
          <table v-else class="tbl">
            <thead><tr><th>原因</th><th>金额</th><th>次数</th></tr></thead>
            <tbody>
              <tr v-for="r in faucetRows" :key="r.reason">
                <td>{{ r.reason }}</td>
                <td class="up">+{{ fmt(r.amount) }}</td>
                <td>{{ r.count }}</td>
              </tr>
            </tbody>
          </table>
        </section>
        <section class="glass-inner">
          <h3>积分消耗（Sink）</h3>
          <div v-if="!sinkRows.length" class="empty">暂无数据</div>
          <table v-else class="tbl">
            <thead><tr><th>原因</th><th>金额</th><th>次数</th></tr></thead>
            <tbody>
              <tr v-for="r in sinkRows" :key="r.reason">
                <td>{{ r.reason }}</td>
                <td class="down">-{{ fmt(r.amount) }}</td>
                <td>{{ r.count }}</td>
              </tr>
            </tbody>
          </table>
        </section>
      </div>
    </template>

    <section v-if="opsData" class="glass-inner ops-dashboard">
      <h3>四合一监控（24h）</h3>
      <div class="metric-grid compact">
        <div class="metric glass-inner">
          <span>已支付订单</span>
          <b>{{ opsData.orders.paid }}</b>
          <small>成功率 {{ opsData.orders.success_rate_pct }}%</small>
        </div>
        <div class="metric glass-inner">
          <span>打新支付</span>
          <b>{{ opsData.orders.mint_paid }}</b>
        </div>
        <div class="metric glass-inner">
          <span>链铸造排队</span>
          <b>{{ opsData.chain.pending_mints }}</b>
          <small>失败 {{ opsData.chain.failed_mints }}</small>
        </div>
        <div class="metric glass-inner">
          <span>AI 分析次数</span>
          <b>{{ opsData.ai.runs }}</b>
          <small>队列 active {{ opsData.ai.queue?.active ?? 0 }}</small>
        </div>
      </div>
      <p class="hint-note">
        链 pending {{ opsData.chain.pending_mints }} · failed {{ opsData.chain.failed_mints }}
        <span v-if="opsData.chain.none_legacy"> · 未排队历史 {{ opsData.chain.none_legacy }}</span>
        <span v-if="opsData.chain.avata_active === false" class="chain-alert">⚠ AVATA 未激活</span>
        <span v-if="opsData.chain.alert" class="chain-alert">⚠ 链失败告警</span>
        · AI 队列 {{ opsData.ai.util_pct ?? 0 }}%
        <span v-if="opsData.ai.alert" class="chain-alert">⚠ AI 排队告警</span>
        · Redis {{ opsData.redis_configured ? 'ON' : 'OFF' }}
      </p>
      <ul v-if="opsFunnelRows.length" class="funnel-list">
        <li v-for="r in opsFunnelRows" :key="r.name">{{ r.name }} · {{ r.count }}</li>
      </ul>
      <ul v-if="opsData.chain.top_errors?.length" class="funnel-list chain-errors">
        <li v-for="(e, i) in opsData.chain.top_errors" :key="i">
          链失败 {{ e.error || '(unknown)' }} × {{ e.count }}
        </li>
      </ul>
      <p class="hint-note subtle">
        生产 {{ opsData.production_mode ? 'ON' : 'OFF' }} ·
        ALIPAY_MOCK={{ opsData.alipay_mock }} · AVATA_MOCK={{ opsData.avata_mock }}
      </p>
    </section>

    <section v-if="data && mintBundles.length" class="glass-inner admin-orders">
      <h3>打新组合包 SKU 绑定</h3>
      <p class="hint-note">将 mint_bundle 商品绑定到具体打新活动，支付后自动写入白名单/抽签资格。</p>
      <div v-for="bp in mintBundles" :key="bp.id" class="mint-admin-row bundle-row">
        <span>{{ bp.name }} <code class="mono">{{ bp.sku }}</code></span>
        <span class="mono">
          活动 ID:
          {{ (bp.grant_payload?.mint_event_id as number | undefined) ?? '未绑定' }}
        </span>
        <el-input
          v-model="bundleBindId[bp.id]"
          placeholder="mint_event_id"
          type="number"
          size="small"
          style="max-width: 120px"
        />
        <el-button size="small" type="primary" plain @click="bindBundle(bp.id)">绑定</el-button>
      </div>
    </section>

    <section v-if="data" class="glass-inner tune-hints">
      <h3>调参指引（config keys）</h3>
      <ul>
        <li><code>asset_buyback_floor</code> — 官方回购地板价（按稀有度）</li>
        <li><code>marketplace_fee_pct</code> — 交易行手续费 sink 比例</li>
        <li><code>fantasy_reward_tiers</code> / <code>fantasy_reward_top_n</code> — 数字阵容周榜发奖</li>
        <li><code>card_duel_stake_min/max</code> / <code>card_duel_fee_pct</code> — 卡牌对决入场费与 sink</li>
        <li><code>card_duel_win_battalion</code> — 对决胜利额外军团贡献</li>
        <li><code>asset_cooldown_days</code> — 新卡流通冷却期</li>
      </ul>
      <p class="hint-note">修改后需重启后端；生产环境请经运营/法务复核后再调整。</p>
    </section>

    <section v-if="data" class="glass-inner admin-orders">
      <h3>首发打新活动（Admin）</h3>
      <p class="hint-note">创建人民币/球迷币打新；人民币场次自动同步 Product SKU 供支付宝下单。</p>
      <div class="refund-row">
        <el-button size="small" :loading="mintLoading" @click="loadMintEvents">刷新活动</el-button>
        <el-button size="small" type="primary" plain @click="seedMintDemo">Seed Demo</el-button>
      </div>
      <div v-if="mintEvents.length" class="mint-admin-list">
        <div v-for="ev in mintEvents" :key="ev.id" class="mint-admin-row">
          <span>{{ ev.name }}</span>
          <span class="mono">{{ ev.currency === 'rmb' ? `¥${(ev.price_fen / 100).toFixed(0)}` : `${ev.price_coins}币` }}</span>
          <span>{{ ev.issued }}/{{ ev.total_supply }}</span>
          <span>{{ ev.status }}</span>
        </div>
      </div>
      <div class="refund-row mint-create">
        <el-input v-model="mintForm.code" placeholder="code" />
        <el-input v-model="mintForm.name" placeholder="名称" />
        <el-input v-model="mintForm.card_code" placeholder="card_code" />
        <el-input v-model="mintForm.price_fen" placeholder="price_fen" type="number" />
        <el-button type="primary" :loading="mintCreating" @click="createMint">创建 RMB 打新</el-button>
      </div>
    </section>

    <section v-if="data" class="glass-inner admin-orders">
      <h3>现金订单退款（Admin）</h3>
      <p class="hint-note">输入已支付订单 ID 发起支付宝原路退款（mock 环境仅标记 refunded）。</p>
      <div class="refund-row">
        <el-input v-model="refundOrderId" placeholder="订单 ID" type="number" clearable />
        <el-button type="danger" plain :loading="refunding" @click="doRefund">标记退款</el-button>
      </div>
    </section>

    <div v-else-if="error" class="error-state glass-inner">
      <p>{{ error }}</p>
      <el-button plain @click="load">重试</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  adminCreateMintEvent,
  adminListMintEvents,
  adminSeedMintDemo,
  getEconomyDashboard,
  getOpsDashboard,
  getStoredAdminSecret,
  setStoredAdminSecret,
  type EconomyDashboard,
  type MintEventAdmin,
  type OpsDashboard,
} from '@/api/asset'
import { adminRefundOrder, adminBindMintBundle, adminListCashProducts, type Product } from '@/api/commerce'
import { ElMessage } from 'element-plus'
import { extractApiError } from '@/utils/apiError'
import { usePageMeta } from '@/composables/usePageMeta'

usePageMeta({
  title: '经济看板 — 运营',
  description: '足球数字资产平台经济健康监控。',
  path: '/admin/economy',
  noIndex: true,
})

const loading = ref(false)
const data = ref<EconomyDashboard | null>(null)
const opsData = ref<OpsDashboard | null>(null)
const error = ref('')

const opsFunnelRows = computed(() => {
  const ev = opsData.value?.funnel_events
  if (!ev) return []
  return Object.entries(ev)
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count)
})
const adminSecret = ref(getStoredAdminSecret())
const windowDays = ref(7)
const refundOrderId = ref('')
const refunding = ref(false)
const mintEvents = ref<MintEventAdmin[]>([])
const mintLoading = ref(false)
const mintCreating = ref(false)
const cashProducts = ref<Product[]>([])
const bundleBindId = ref<Record<number, string>>({})

const mintBundles = computed(() =>
  cashProducts.value.filter((p) => p.product_type === 'mint_bundle'),
)
const mintForm = ref({
  code: '',
  name: '',
  card_code: '',
  price_fen: '6800',
})

const faucetRows = computed(() => {
  if (!data.value) return []
  return Object.entries(data.value.redeem_points.faucet)
    .map(([reason, v]) => ({ reason, ...v }))
    .sort((a, b) => b.amount - a.amount)
})
const sinkRows = computed(() => {
  if (!data.value) return []
  return Object.entries(data.value.redeem_points.sink)
    .map(([reason, v]) => ({ reason, ...v }))
    .sort((a, b) => b.amount - a.amount)
})
const healthClass = computed(() => {
  const p = data.value?.redeem_points.inflation_pct ?? 0
  if (p > 40) return 'warn-high'
  if (p < -10) return 'warn-low'
  return 'ok'
})

function fmt(n: number) {
  return n.toLocaleString()
}

async function load() {
  if (!adminSecret.value.trim()) {
    error.value = '请先输入 Admin Secret'
    return
  }
  setStoredAdminSecret(adminSecret.value.trim())
  loading.value = true
  error.value = ''
  try {
    data.value = await getEconomyDashboard(windowDays.value, adminSecret.value.trim())
    opsData.value = await getOpsDashboard(24, adminSecret.value.trim())
    await Promise.all([loadMintEvents(), loadCashProducts()])
  } catch (e: unknown) {
    data.value = null
    error.value = extractApiError(e, '加载失败，请检查 Secret 是否正确')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  if (adminSecret.value) void load()
})

async function doRefund() {
  const id = parseInt(refundOrderId.value, 10)
  if (!id || !adminSecret.value.trim()) {
    ElMessage.warning('请输入订单 ID 与 Admin Secret')
    return
  }
  refunding.value = true
  try {
    await adminRefundOrder(id, adminSecret.value.trim())
    ElMessage.success('订单已标记退款')
    refundOrderId.value = ''
  } catch (e: unknown) {
    ElMessage.error(extractApiError(e, '退款失败'))
  } finally {
    refunding.value = false
  }
}

async function loadMintEvents() {
  if (!adminSecret.value.trim()) return
  mintLoading.value = true
  try {
    mintEvents.value = await adminListMintEvents(adminSecret.value.trim())
  } catch (e: unknown) {
    ElMessage.error(extractApiError(e, '加载打新活动失败'))
  } finally {
    mintLoading.value = false
  }
}

async function loadCashProducts() {
  if (!adminSecret.value.trim()) return
  try {
    cashProducts.value = await adminListCashProducts(adminSecret.value.trim())
  } catch {
    cashProducts.value = []
  }
}

async function bindBundle(productId: number) {
  const raw = bundleBindId.value[productId]
  const eventId = parseInt(raw, 10)
  if (!eventId || !adminSecret.value.trim()) {
    ElMessage.warning('请输入有效的 mint_event_id')
    return
  }
  try {
    await adminBindMintBundle(productId, eventId, adminSecret.value.trim())
    ElMessage.success('组合包已绑定打新活动')
    await loadCashProducts()
  } catch (e: unknown) {
    ElMessage.error(extractApiError(e, '绑定失败'))
  }
}

async function seedMintDemo() {
  if (!adminSecret.value.trim()) return
  mintLoading.value = true
  try {
    await adminSeedMintDemo(adminSecret.value.trim())
    ElMessage.success('Demo 打新已 seed')
    await loadMintEvents()
  } catch (e: unknown) {
    ElMessage.error(extractApiError(e, 'Seed 失败'))
  } finally {
    mintLoading.value = false
  }
}

async function createMint() {
  if (!adminSecret.value.trim()) return
  const code = mintForm.value.code.trim()
  const name = mintForm.value.name.trim()
  const card_code = mintForm.value.card_code.trim()
  if (!code || !name || !card_code) {
    ElMessage.warning('请填写 code / 名称 / card_code')
    return
  }
  mintCreating.value = true
  try {
    const now = new Date()
    const ends = new Date(now.getTime() + 7 * 86400000)
    await adminCreateMintEvent(adminSecret.value.trim(), {
      code,
      name,
      card_code,
      currency: 'rmb',
      price_fen: parseInt(mintForm.value.price_fen, 10) || 6800,
      total_supply: 100,
      sale_mode: 'public',
      starts_at: now.toISOString(),
      ends_at: ends.toISOString(),
    })
    ElMessage.success('打新活动已创建')
    mintForm.value = { code: '', name: '', card_code: '', price_fen: '6800' }
    await loadMintEvents()
  } catch (e: unknown) {
    ElMessage.error(extractApiError(e, '创建失败'))
  } finally {
    mintCreating.value = false
  }
}
</script>

<style scoped>
.economy-page {
  max-width: 900px;
  margin: 0 auto;
  padding-bottom: 32px;
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
.glass-inner {
  border-radius: 14px;
  padding: 16px;
  margin-bottom: 14px;
}
.auth-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}
.auth-bar .el-input {
  flex: 1;
  min-width: 200px;
}
.health.ok { border-left: 3px solid #5fc88f; }
.health.warn-high { border-left: 3px solid #e07a7a; }
.health.warn-low { border-left: 3px solid #6eb5e0; }
.health-label {
  font-size: 0.72rem;
  color: var(--wc-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.health p {
  margin: 6px 0 10px;
  font-size: 0.9rem;
  color: var(--wc-text-secondary);
}
.health-metrics {
  display: flex;
  gap: 24px;
  font-size: 0.82rem;
}
.health-metrics span { color: var(--wc-text-muted); margin-right: 6px; }
.metric-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 12px;
  margin-bottom: 14px;
}
.metric {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 0;
}
.metric span { font-size: 0.72rem; color: var(--wc-text-muted); }
.metric b { font-size: 1.2rem; color: var(--wc-text-secondary); font-variant-numeric: tabular-nums; }
.metric small { font-size: 0.68rem; color: var(--wc-text-muted); }
.up { color: #5fc88f !important; }
.down { color: #e07a7a !important; }
.tables {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}
@media (max-width: 640px) {
  .tables { grid-template-columns: 1fr; }
}
.tables h3 {
  margin: 0 0 10px;
  font-size: 0.9rem;
  color: var(--wc-text-secondary);
}
.tbl {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.78rem;
}
.tbl th, .tbl td {
  padding: 6px 8px;
  text-align: left;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}
.tbl th { color: var(--wc-text-muted); font-weight: 500; }
.empty, .error-state {
  text-align: center;
  color: var(--wc-text-muted);
  font-size: 0.85rem;
}
.tune-hints h3 {
  margin: 0 0 10px;
  font-size: 0.9rem;
  color: var(--wc-text-secondary);
}
.tune-hints ul {
  margin: 0;
  padding-left: 18px;
  font-size: 0.78rem;
  color: var(--wc-text-muted);
  line-height: 1.7;
}
.tune-hints code {
  font-size: 0.72rem;
  color: var(--wc-accent-gold);
}
.hint-note {
  margin: 10px 0 0;
  font-size: 0.68rem;
  color: var(--wc-text-muted);
}
.sk-block {
  margin-bottom: 12px;
  padding: 14px;
  border-radius: 12px;
  background: rgba(20, 24, 42, 0.4);
}
.admin-orders {
  margin-top: 16px;
  padding: 16px;
  border-radius: 12px;
}
.admin-orders h3 {
  margin: 0 0 8px;
  font-size: 0.95rem;
}
.refund-row {
  display: flex;
  gap: 10px;
  margin-top: 10px;
  flex-wrap: wrap;
}
.mint-admin-list {
  margin: 12px 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.mint-admin-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  font-size: 0.82rem;
  padding: 6px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}
.bundle-row {
  margin-top: 8px;
}
.chain-alert {
  color: #f5a623;
  margin-left: 8px;
}
.hint-note.subtle {
  margin-top: 8px;
  opacity: 0.85;
}
.mint-admin-list .mint-admin-row {
  display: grid;
  grid-template-columns: 1fr auto auto auto;
  gap: 8px;
  font-size: 0.75rem;
  color: var(--wc-text-muted);
  padding: 6px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}
.mint-create {
  align-items: flex-end;
}
.mint-create .el-input {
  max-width: 140px;
}
</style>
