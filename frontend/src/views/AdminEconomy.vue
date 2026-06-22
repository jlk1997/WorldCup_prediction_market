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

    <div v-else-if="error" class="error-state glass-inner">
      <p>{{ error }}</p>
      <el-button plain @click="load">重试</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  getEconomyDashboard,
  getStoredAdminSecret,
  setStoredAdminSecret,
  type EconomyDashboard,
} from '@/api/asset'
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
const error = ref('')
const adminSecret = ref(getStoredAdminSecret())
const windowDays = ref(7)

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
</style>
