<template>
  <div class="assets-page page-shell mobile-page">
    <!-- 顶部 Hero：不透明底板，避免背景人像干扰阅读 -->
    <header v-if="pageLoading" class="hero-card glass-panel">
      <el-skeleton :rows="4" animated />
    </header>
    <header v-else-if="portfolio" class="hero-card glass-panel">
      <div class="hero-head">
        <div>
          <h1>我的资产</h1>
          <p class="hero-sub">球星卡组合 · 质押收益 · 流通记录</p>
        </div>
        <span v-if="achievementStats.total" class="achv-pill">
          成就 {{ achievementStats.unlocked }}/{{ achievementStats.total }}
        </span>
      </div>

      <div class="hero-value-wrap">
        <span class="hero-label">资产组合估值</span>
        <span class="hero-value tabular-nums">{{ portfolio.portfolio_value.toLocaleString() }}</span>
        <span class="hero-unit">{{ portfolio.currency_label }}</span>
      </div>

      <div class="hero-metrics">
        <div class="metric">
          <span class="metric-label">可用积分</span>
          <strong class="metric-val tabular-nums">{{ portfolio.redeem_points.toLocaleString() }}</strong>
        </div>
        <div class="metric-divider" />
        <div class="metric">
          <span class="metric-label">球迷币</span>
          <strong class="metric-val tabular-nums">{{ portfolio.fan_coins.toLocaleString() }}</strong>
        </div>
        <div class="metric-divider" />
        <div class="metric">
          <span class="metric-label">数字阵容</span>
          <strong class="metric-val tabular-nums">{{ fantasyLabel }}</strong>
        </div>
      </div>

      <p class="hero-disclaimer">{{ portfolio.disclaimer }}</p>
    </header>

    <!-- 待办 -->
    <div v-if="hubAlerts.length" class="action-alerts">
      <router-link
        v-for="(a, i) in hubAlerts"
        :key="i"
        :to="a.to"
        class="action-alert glass-panel"
        :class="a.kind"
      >
        <span class="aa-icon">{{ a.icon }}</span>
        <span class="aa-text">{{ a.text }}</span>
        <span class="aa-go">→</span>
      </router-link>
    </div>

    <!-- 实名（未认证时醒目横幅） -->
    <div
      v-if="!pageLoading && realname && !realname.verified"
      class="realname-banner glass-panel"
    >
      <div class="rn-body">
        <span class="rn-icon">🪪</span>
        <div class="rn-copy">
          <strong>完成实名认证</strong>
          <span>转赠、交易行挂牌与购买需实名（合规要求）</span>
        </div>
      </div>
      <button type="button" class="rn-cta" @click="rnDialog = true">立即认证</button>
    </div>
    <div v-else-if="realname?.verified" class="realname-ok glass-panel">
      <span>✓ 已实名认证</span>
    </div>

    <!-- 统一快捷导航（去掉与 Hub 重复的「我的资产」入口） -->
    <nav class="shortcut-nav glass-panel" aria-label="资产相关功能">
      <router-link v-for="item in shortcuts" :key="item.to" :to="item.to" class="shortcut-item">
        <span class="sc-icon" aria-hidden="true">{{ item.icon }}</span>
        <span class="sc-label">{{ item.label }}</span>
        <span v-if="item.badge" class="sc-badge">{{ item.badge > 99 ? '99+' : item.badge }}</span>
      </router-link>
    </nav>

    <p v-if="!pageLoading" class="admin-link">
      <router-link to="/admin/economy">运营经济看板 →</router-link>
    </p>

    <!-- 内容 Tab：减少长页滚动 -->
    <el-tabs v-model="activeTab" class="assets-tabs" stretch>
      <el-tab-pane label="质押" name="stakes">
        <section id="stakes" class="tab-panel glass-panel">
          <div class="panel-head">
            <h3>质押中</h3>
            <span class="panel-hint">被动积分 + 竞猜加成</span>
          </div>
          <div v-if="battalionBoost?.teams?.length" class="battalion-inline">
            <span class="bi-title">军团加成</span>
            <div class="bb-list">
              <span v-for="t in battalionBoost.teams" :key="t.team_id" class="bb-chip">
                {{ t.team_name }} +{{ t.boost_pct }}%
              </span>
            </div>
            <span v-if="battalionBoost.favorite_boost_pct > 0" class="bi-fav">
              主队助威额外 +{{ battalionBoost.favorite_boost_pct }}%
            </span>
          </div>
          <div v-if="!stakes.length" class="empty-block">
            <p>暂无质押卡牌</p>
            <router-link to="/collection" class="empty-cta">去收藏册质押 →</router-link>
          </div>
          <div v-else class="stake-list">
            <div v-for="s in stakes" :key="s.stake_id" class="stake-item">
              <div class="si-img" :style="cardBg(s.image_url)" />
              <div class="si-info">
                <div class="si-name">{{ s.card_name }}</div>
                <div class="si-yield">
                  {{ s.daily_yield }} 积分/天
                  <span v-if="s.pending > 0" class="pending">待领 {{ s.pending }}</span>
                </div>
              </div>
              <div class="si-actions">
                <button
                  type="button"
                  class="btn-primary-sm"
                  :disabled="s.pending <= 0"
                  @click="claim(s.stake_id)"
                >
                  领取
                </button>
                <button type="button" class="btn-ghost-sm" @click="unstake(s.stake_id)">赎回</button>
              </div>
            </div>
          </div>
        </section>
      </el-tab-pane>

      <el-tab-pane name="listings">
        <template #label>
          <span>挂牌</span>
          <span v-if="listings.length" class="tab-count">{{ listings.length }}</span>
        </template>
        <section class="tab-panel glass-panel">
          <div class="panel-head">
            <h3>我的挂牌</h3>
            <router-link to="/market" class="panel-link">去交易行 →</router-link>
          </div>
          <div v-if="!listings.length" class="empty-block">
            <p>暂无在售卡牌</p>
            <router-link to="/collection" class="empty-cta">去收藏册挂牌 →</router-link>
          </div>
          <div v-else class="listing-list">
            <div v-for="l in listings" :key="l.listing_id" class="listing-item">
              <div class="li-img" :style="cardBg(l.image_url)" />
              <div class="li-info">
                <div class="li-name">
                  {{ l.card_name }}
                  <span v-if="l.serial_no" class="serial">#{{ l.serial_no }}</span>
                </div>
                <div class="li-price">
                  {{ l.current_price }} 积分 · {{ l.list_type === 'auction' ? '竞拍' : '一口价' }}
                </div>
              </div>
              <button type="button" class="btn-ghost-sm" @click="doCancel(l.listing_id)">下架</button>
            </div>
          </div>
        </section>
      </el-tab-pane>

      <el-tab-pane name="achievements">
        <template #label>
          <span>成就</span>
          <span v-if="achievementStats.unlocked" class="tab-count">{{ achievementStats.unlocked }}</span>
        </template>
        <section class="tab-panel glass-panel">
          <div class="panel-head">
            <h3>资产成就</h3>
            <span class="panel-hint">收集与流通解锁</span>
          </div>
          <div class="achv-grid">
            <div v-for="a in achievements" :key="a.code" class="achv" :class="{ unlocked: a.unlocked }">
              <span class="achv-name">{{ a.name }}</span>
              <span class="achv-desc">{{ a.desc }}</span>
            </div>
          </div>
        </section>
      </el-tab-pane>

      <el-tab-pane label="记录" name="history">
        <section class="tab-panel glass-panel">
          <div class="panel-head">
            <h3>流转记录</h3>
            <span class="panel-hint">转赠 · 交易 · 回购</span>
          </div>
          <div v-if="!history.length" class="empty-block">
            <p>暂无流转记录</p>
          </div>
          <ul v-else class="history">
            <li v-for="h in history" :key="h.id">
              <span class="h-kind" :class="h.kind">{{ kindLabel(h.kind, h.direction) }}</span>
              <span class="h-name">{{ h.card_name }}</span>
              <span class="h-amount" :class="h.direction">
                <template v-if="h.points_amount">
                  {{ h.direction === 'in' && h.kind !== 'trade' ? '+' : '' }}{{ h.points_amount }}
                </template>
                <template v-else>—</template>
              </span>
            </li>
          </ul>
        </section>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="rnDialog" title="实名认证" width="min(400px, 94vw)" align-center append-to-body class="wc-dialog">
      <el-form label-position="top">
        <el-form-item label="真实姓名">
          <el-input v-model="rnForm.name" placeholder="请输入身份证姓名" />
        </el-form-item>
        <el-form-item label="身份证号">
          <el-input v-model="rnForm.id" placeholder="18 位身份证号" maxlength="18" />
        </el-form-item>
      </el-form>
      <p class="rn-note">仅用于合规核验，平台仅存储加密哈希，不保存明文。</p>
      <template #footer>
        <el-button @click="rnDialog = false">取消</el-button>
        <el-button type="primary" :loading="rnLoading" @click="doVerify">提交认证</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getPortfolio,
  getAchievements,
  getStakes,
  getMyListings,
  getTransferHistory,
  getRealNameStatus,
  getBattalionBoost,
  getAssetHubSummary,
  verifyRealName,
  claimStake,
  unstakeCard,
  cancelListing,
  type PortfolioSummary,
  type Achievement,
  type StakeItem,
  type MarketListing,
  type TransferLogItem,
  type RealNameStatus,
  type BattalionBoostSummary,
  type AssetHubSummary,
} from '@/api/asset'
import { fetchMe } from '@/stores/authStore'
import { extractApiError } from '@/utils/apiError'
import { invalidateRealnameCache } from '@/composables/useAssetRealname'
import { usePageMeta } from '@/composables/usePageMeta'

usePageMeta({
  title: '我的资产 — 最后一舞',
  description: '球星卡资产组合、质押收益与流通记录。',
  path: '/me/assets',
  noIndex: true,
})

const portfolio = ref<PortfolioSummary | null>(null)
const pageLoading = ref(true)
const achievements = ref<Achievement[]>([])
const stakes = ref<StakeItem[]>([])
const listings = ref<MarketListing[]>([])
const history = ref<TransferLogItem[]>([])
const realname = ref<RealNameStatus | null>(null)
const battalionBoost = ref<BattalionBoostSummary | null>(null)
const hubSummary = ref<AssetHubSummary | null>(null)
const activeTab = ref('stakes')

const achievementStats = computed(() => ({
  unlocked: achievements.value.filter((a) => a.unlocked).length,
  total: achievements.value.length,
}))

const fantasyLabel = computed(() => {
  const s = hubSummary.value
  if (!s) return '—'
  if (s.fantasy_rank) return `#${s.fantasy_rank}`
  if (s.fantasy_score) return `${s.fantasy_score} 分`
  return '未上榜'
})

const shortcuts = computed(() => {
  const s = hubSummary.value
  return [
    { to: '/collection', label: '收藏册', icon: '📖', badge: 0 },
    { to: '/market', label: '交易行', icon: '🏪', badge: s?.active_listings || 0 },
    { to: '/mint', label: '首发打新', icon: '✨', badge: s?.live_mint_events || 0 },
    { to: '/fantasy', label: '数字阵容', icon: '⚽', badge: 0 },
    { to: '/arena', label: '竞技场', icon: '⚔️', badge: (s?.duel_pending_incoming || 0) + (s?.duel_pending_outgoing || 0) },
    { to: '/agent', label: 'AI 分析', icon: '🤖', badge: 0 },
  ]
})

const hubAlerts = computed(() => {
  const s = hubSummary.value
  if (!s) return []
  const out: { to: string; text: string; icon: string; kind: string }[] = []
  if (s.claimable_stake_points > 0) {
    out.push({
      to: '#stakes',
      text: `质押收益待领 ${s.claimable_stake_points} 积分`,
      icon: '💰',
      kind: 'stake',
    })
  }
  if (s.duel_pending_incoming > 0) {
    out.push({
      to: '/arena',
      text: `${s.duel_pending_incoming} 场对决待应战`,
      icon: '⚔️',
      kind: 'duel',
    })
  }
  if (s.duel_pending_outgoing > 0) {
    out.push({
      to: '/arena',
      text: `${s.duel_pending_outgoing} 场对决等待对方应战`,
      icon: '⏳',
      kind: 'pending',
    })
  }
  if (s.live_mint_events > 0) {
    out.push({
      to: '/mint',
      text: `${s.live_mint_events} 场打新正在进行`,
      icon: '✨',
      kind: 'mint',
    })
  }
  return out
})

const rnDialog = ref(false)
const rnLoading = ref(false)
const rnForm = reactive({ name: '', id: '' })

const KIND: Record<string, string> = {
  gift: '转赠', trade: '交易', buyback: '回购', mint: '铸造', primary: '打新',
}

function kindLabel(kind: string, dir: string) {
  const base = KIND[kind] || kind
  if (kind === 'gift') return dir === 'in' ? '收到转赠' : '赠出'
  if (kind === 'trade') return dir === 'in' ? '买入' : '卖出'
  return base
}

function cardBg(url?: string | null) {
  return url ? { backgroundImage: `url(${url})` } : {}
}

async function loadHub() {
  try {
    hubSummary.value = await getAssetHubSummary()
  } catch {
    hubSummary.value = null
  }
}

async function loadAll() {
  pageLoading.value = true
  try {
    const [p, a, s, l, h, r, bb] = await Promise.all([
      getPortfolio(),
      getAchievements(),
      getStakes(),
      getMyListings(),
      getTransferHistory(),
      getRealNameStatus(),
      getBattalionBoost().catch(() => null),
    ])
    await loadHub()
    portfolio.value = p
    achievements.value = a
    stakes.value = s
    listings.value = l
    history.value = h
    realname.value = r
    battalionBoost.value = bb
    if (p.newly_unlocked.length) {
      ElMessage.success(`解锁新成就 ×${p.newly_unlocked.length}`)
    }
    if (s.some((x) => x.pending > 0)) activeTab.value = 'stakes'
    else if (l.length) activeTab.value = 'listings'
  } finally {
    pageLoading.value = false
  }
}

async function claim(id: number) {
  try {
    const res = await claimStake(id)
    ElMessage.success(`领取 ${res.points_gained} 可用积分`)
    await Promise.all([loadAll(), fetchMe()])
  } catch (e: unknown) {
    ElMessage.error(errMsg(e) || '领取失败')
  }
}

async function unstake(id: number) {
  try {
    await ElMessageBox.confirm('赎回后将解除质押，卡牌恢复可流通。确认赎回？', '赎回质押', {
      customClass: 'wc-message-box',
      roundButton: true,
      confirmButtonText: '确认赎回',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  try {
    const res = await unstakeCard(id)
    ElMessage.success(`已赎回，结算 ${res.points_gained} 积分`)
    await Promise.all([loadAll(), fetchMe()])
  } catch (e: unknown) {
    ElMessage.error(errMsg(e) || '赎回失败')
  }
}

async function doCancel(id: number) {
  try {
    await cancelListing(id)
    ElMessage.success('已下架')
    await loadAll()
  } catch (e: unknown) {
    ElMessage.error(errMsg(e) || '下架失败')
  }
}

async function doVerify() {
  rnLoading.value = true
  try {
    realname.value = await verifyRealName(rnForm.name, rnForm.id)
    invalidateRealnameCache()
    ElMessage.success('实名认证成功')
    rnDialog.value = false
    await loadAll()
  } catch (e: unknown) {
    ElMessage.error(errMsg(e) || '认证失败')
  } finally {
    rnLoading.value = false
  }
}

function errMsg(e: unknown): string {
  return extractApiError(e)
}

onMounted(loadAll)
</script>

<style scoped>
.assets-page {
  max-width: 720px;
  margin: 0 auto;
}

/* Hero */
.hero-card {
  padding: 18px 16px 16px;
  margin-bottom: 12px;
}
.hero-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 14px;
}
.hero-card h1 {
  margin: 0;
  font-size: 1.35rem;
  font-weight: 800;
  color: var(--wc-text-primary);
  font-family: var(--wc-font-serif, inherit);
}
.hero-sub {
  margin: 4px 0 0;
  font-size: 0.72rem;
  color: var(--wc-text-muted);
}
.achv-pill {
  flex-shrink: 0;
  font-size: 0.65rem;
  padding: 4px 10px;
  border-radius: 20px;
  background: rgba(212, 165, 116, 0.15);
  color: var(--wc-accent-gold);
  border: 1px solid rgba(212, 165, 116, 0.25);
}
.hero-value-wrap {
  text-align: center;
  padding: 12px 0 14px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}
.hero-label {
  display: block;
  font-size: 0.72rem;
  color: var(--wc-text-muted);
  margin-bottom: 4px;
}
.hero-value {
  display: block;
  font-size: 2.4rem;
  font-weight: 800;
  line-height: 1.1;
  color: var(--wc-accent-gold);
  text-shadow: 0 2px 12px rgba(212, 165, 116, 0.25);
}
.hero-unit {
  display: block;
  margin-top: 2px;
  font-size: 0.68rem;
  color: var(--wc-text-muted);
}
.hero-metrics {
  display: flex;
  align-items: center;
  justify-content: space-around;
  margin-top: 14px;
  gap: 8px;
}
.metric {
  flex: 1;
  text-align: center;
}
.metric-label {
  display: block;
  font-size: 0.66rem;
  color: var(--wc-text-muted);
  margin-bottom: 2px;
}
.metric-val {
  font-size: 1.05rem;
  color: var(--wc-text-primary);
}
.metric-divider {
  width: 1px;
  height: 28px;
  background: rgba(255, 255, 255, 0.1);
  flex-shrink: 0;
}
.hero-disclaimer {
  margin: 12px 0 0;
  font-size: 0.62rem;
  color: rgba(255, 255, 255, 0.45);
  line-height: 1.45;
  text-align: center;
}

/* Alerts */
.action-alerts {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 12px;
}
.action-alert {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 11px 14px;
  border-radius: 12px;
  text-decoration: none;
  color: var(--wc-text-primary);
}
.action-alert.stake { border-left: 3px solid var(--wc-accent-gold); }
.action-alert.duel { border-left: 3px solid #e85d5d; }
.action-alert.mint { border-left: 3px solid #7dd3a8; }
.action-alert.pending { border-left: 3px solid #f0b86c; }
.aa-icon { font-size: 1.1rem; }
.aa-text { flex: 1; font-size: 0.82rem; font-weight: 500; }
.aa-go { color: var(--wc-text-muted); }

/* Realname */
.realname-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
  margin-bottom: 12px;
  border: 1px solid rgba(232, 93, 93, 0.35);
  background: linear-gradient(135deg, rgba(80, 30, 30, 0.55), rgba(20, 14, 28, 0.92)) !important;
}
.rn-body {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  min-width: 0;
}
.rn-icon { font-size: 1.3rem; line-height: 1; }
.rn-copy {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.rn-copy strong {
  font-size: 0.88rem;
  color: var(--wc-text-primary);
}
.rn-copy span {
  font-size: 0.68rem;
  color: var(--wc-text-muted);
  line-height: 1.35;
}
.rn-cta {
  flex-shrink: 0;
  padding: 8px 14px;
  border: none;
  border-radius: 8px;
  background: linear-gradient(135deg, #e8c88a, #c99850);
  color: #1a1208;
  font-size: 0.78rem;
  font-weight: 700;
  cursor: pointer;
  box-shadow: 0 4px 14px rgba(212, 165, 116, 0.35);
}
.rn-cta:active { transform: scale(0.97); }
.realname-ok {
  padding: 8px 14px;
  margin-bottom: 12px;
  font-size: 0.75rem;
  color: #5fc88f;
  text-align: center;
}

/* Shortcut nav */
.shortcut-nav {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  padding: 12px;
  margin-bottom: 12px;
}
.shortcut-item {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 12px 6px;
  border-radius: 10px;
  text-decoration: none;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.06);
  transition: background 0.15s, transform 0.12s;
}
.shortcut-item:active {
  transform: scale(0.97);
  background: rgba(212, 165, 116, 0.08);
}
.sc-icon { font-size: 1.25rem; line-height: 1; }
.sc-label {
  font-size: 0.72rem;
  font-weight: 600;
  color: var(--wc-text-primary);
}
.sc-badge {
  position: absolute;
  top: 4px;
  right: 4px;
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  border-radius: 8px;
  background: #e85d5d;
  color: #fff;
  font-size: 0.58rem;
  font-weight: 700;
  line-height: 16px;
  text-align: center;
}

.admin-link {
  text-align: right;
  margin: -4px 0 10px;
  font-size: 0.68rem;
}
.admin-link a {
  color: var(--wc-text-muted);
  text-decoration: none;
}

/* Tabs */
.assets-tabs {
  margin-top: 4px;
}
.assets-tabs :deep(.el-tabs__header) {
  margin-bottom: 10px;
}
.assets-tabs :deep(.el-tabs__item) {
  font-size: 0.82rem;
  color: var(--wc-text-muted);
  padding: 0 12px;
}
.assets-tabs :deep(.el-tabs__item.is-active) {
  color: var(--wc-accent-gold);
  font-weight: 700;
}
.assets-tabs :deep(.el-tabs__active-bar) {
  background: var(--wc-accent-gold);
}
.tab-count {
  margin-left: 4px;
  font-size: 0.62rem;
  padding: 1px 5px;
  border-radius: 6px;
  background: rgba(212, 165, 116, 0.2);
  color: var(--wc-accent-gold);
}

.tab-panel {
  padding: 14px 14px 16px;
}
.panel-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 12px;
}
.panel-head h3 {
  margin: 0;
  font-size: 0.95rem;
  color: var(--wc-text-primary);
  font-weight: 700;
}
.panel-hint {
  font-size: 0.68rem;
  color: var(--wc-text-muted);
}
.panel-link {
  font-size: 0.72rem;
  color: var(--wc-accent-gold);
  text-decoration: none;
  white-space: nowrap;
}

.battalion-inline {
  margin-bottom: 12px;
  padding: 10px 12px;
  border-radius: 10px;
  background: rgba(125, 211, 168, 0.08);
  border: 1px solid rgba(125, 211, 168, 0.15);
}
.bi-title {
  display: block;
  font-size: 0.68rem;
  color: var(--wc-text-muted);
  margin-bottom: 6px;
}
.bi-fav {
  display: block;
  margin-top: 6px;
  font-size: 0.72rem;
  color: #7dd3a8;
}
.bb-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.bb-chip {
  font-size: 0.72rem;
  padding: 4px 10px;
  border-radius: 8px;
  background: rgba(125, 211, 168, 0.12);
  color: var(--wc-text-primary);
}

.empty-block {
  text-align: center;
  padding: 20px 12px;
}
.empty-block p {
  margin: 0 0 8px;
  font-size: 0.82rem;
  color: var(--wc-text-muted);
}
.empty-cta {
  font-size: 0.78rem;
  color: var(--wc-accent-gold);
  text-decoration: none;
  font-weight: 600;
}

.stake-list,
.listing-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.stake-item,
.listing-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.05);
}
.si-img,
.li-img {
  width: 44px;
  height: 58px;
  border-radius: 6px;
  background: linear-gradient(160deg, rgba(40, 30, 20, 0.8), rgba(20, 16, 30, 0.95));
  background-size: cover;
  background-position: center;
  flex-shrink: 0;
}
.si-info,
.li-info {
  flex: 1;
  min-width: 0;
}
.si-name,
.li-name {
  font-size: 0.84rem;
  font-weight: 600;
  color: var(--wc-text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.serial {
  font-size: 0.68rem;
  color: var(--wc-text-muted);
  font-weight: 400;
}
.si-yield,
.li-price {
  font-size: 0.72rem;
  color: var(--wc-text-muted);
  margin-top: 2px;
}
.si-yield .pending {
  margin-left: 6px;
  color: var(--wc-accent-gold);
  font-weight: 600;
}
.si-actions {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex-shrink: 0;
}

.btn-primary-sm,
.btn-ghost-sm {
  padding: 5px 10px;
  border-radius: 6px;
  font-size: 0.72rem;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  border: none;
}
.btn-primary-sm {
  background: linear-gradient(135deg, rgba(212, 165, 116, 0.35), rgba(180, 130, 60, 0.25));
  color: var(--wc-accent-gold);
  border: 1px solid rgba(212, 165, 116, 0.4);
}
.btn-primary-sm:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.btn-ghost-sm {
  background: transparent;
  color: var(--wc-text-muted);
  border: 1px solid rgba(255, 255, 255, 0.12);
}

.achv-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}
@media (min-width: 520px) {
  .achv-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}
.achv {
  padding: 10px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.05);
  opacity: 0.45;
}
.achv.unlocked {
  opacity: 1;
  background: linear-gradient(135deg, rgba(80, 60, 30, 0.45), rgba(40, 30, 50, 0.5));
  border-color: rgba(231, 175, 92, 0.35);
}
.achv-name {
  display: block;
  font-size: 0.8rem;
  font-weight: 700;
  color: var(--wc-accent-gold);
  margin-bottom: 2px;
}
.achv-desc {
  font-size: 0.64rem;
  color: var(--wc-text-muted);
  line-height: 1.35;
}

.history {
  margin: 0;
  padding: 0;
  list-style: none;
}
.history li {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}
.history li:last-child {
  border-bottom: none;
}
.h-kind {
  font-size: 0.62rem;
  padding: 3px 7px;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.08);
  color: var(--wc-text-muted);
  white-space: nowrap;
  flex-shrink: 0;
}
.h-name {
  flex: 1;
  font-size: 0.8rem;
  color: var(--wc-text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.h-amount {
  font-size: 0.78rem;
  font-variant-numeric: tabular-nums;
  color: var(--wc-text-muted);
  flex-shrink: 0;
}
.h-amount.in { color: #5fc88f; }
.h-amount.out { color: #e07a7a; }

.rn-note {
  font-size: 0.66rem;
  color: var(--wc-text-muted);
  margin: 4px 0 0;
}
</style>
