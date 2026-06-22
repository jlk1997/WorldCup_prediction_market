<template>
  <div class="assets-page">
    <div class="page-header">
      <h1>我的资产</h1>
      <p class="subtitle">球星卡资产组合 · 质押收益 · 流通记录</p>
    </div>

    <!-- 资产总览 -->
    <div v-if="pageLoading" class="overview glass-inner">
      <el-skeleton :rows="3" animated />
    </div>
    <div class="overview glass-inner" v-else-if="portfolio">
      <div class="ov-main">
        <span class="label">资产组合估值（{{ portfolio.currency_label }}）</span>
        <span class="value">{{ portfolio.portfolio_value.toLocaleString() }}</span>
      </div>
      <div class="ov-stats">
        <div class="ov-stat"><span>可用积分</span><b>{{ portfolio.redeem_points.toLocaleString() }}</b></div>
        <div class="ov-stat"><span>球迷币</span><b>{{ portfolio.fan_coins.toLocaleString() }}</b></div>
      </div>
      <p class="ov-disclaimer">{{ portfolio.disclaimer }}</p>
    </div>

    <AssetHubBar ref="hubBarRef" @loaded="onHubLoaded" />

    <!-- 待办提醒 -->
    <div v-if="hubAlerts.length" class="action-alerts">
      <router-link
        v-for="(a, i) in hubAlerts"
        :key="i"
        :to="a.to"
        class="action-alert glass-inner"
        :class="a.kind"
      >
        <span class="aa-icon">{{ a.icon }}</span>
        <span class="aa-text">{{ a.text }}</span>
        <span class="aa-go">→</span>
      </router-link>
    </div>

    <!-- 实名 -->
    <div class="realname glass-inner" :class="{ verified: realname?.verified }">
      <div class="rn-head">
        <span class="rn-title">实名认证</span>
        <span class="rn-badge" :class="{ ok: realname?.verified }">{{ realname?.verified ? '已认证' : '未认证' }}</span>
      </div>
      <p class="rn-desc">完成实名认证后可进行转赠、交易行挂牌与购买（合规要求）。</p>
      <el-button v-if="!realname?.verified" type="primary" size="small" @click="rnDialog = true">立即认证</el-button>
    </div>

    <!-- 快捷入口 -->
    <div class="quick-nav">
      <router-link class="qn glass-inner" to="/collection"><span>收藏册</span><small>图鉴与流通</small></router-link>
      <router-link class="qn glass-inner" to="/arena"><span>竞技场</span><small>卡牌对决</small></router-link>
      <router-link class="qn glass-inner" to="/agent"><span>AI 分析</span><small>持卡折扣</small></router-link>
      <router-link class="qn glass-inner" to="/market"><span>交易行</span><small>买卖球星卡</small></router-link>
    </div>

    <p v-if="!pageLoading" class="admin-link">
      <router-link to="/admin/economy">运营经济看板 →</router-link>
    </p>

    <!-- 军团卡牌加成 -->
    <section v-if="battalionBoost?.teams?.length" class="block glass-inner battalion-boost">
      <h3>军团卡牌加成 <span class="muted">助威贡献额外加成</span></h3>
      <p v-if="battalionBoost.favorite_boost_pct > 0" class="bb-fav">
        主队助威额外 <b>+{{ battalionBoost.favorite_boost_pct }}%</b>
      </p>
      <div class="bb-list">
        <div v-for="t in battalionBoost.teams" :key="t.team_id" class="bb-item">
          <span class="bb-team">{{ t.team_name }}</span>
          <span class="bb-pct">+{{ t.boost_pct }}%</span>
        </div>
      </div>
      <router-link class="bb-link" to="/collection">去收藏册持有/质押 →</router-link>
    </section>

    <!-- 质押 -->
    <section id="stakes" class="block glass-inner">
      <h3>质押中 <span class="muted">持有产被动收益 + 竞猜加成</span></h3>
      <div v-if="!stakes.length" class="empty">暂无质押。前往收藏册质押球星卡获取被动可用积分。</div>
      <div v-else class="stake-list">
        <div v-for="s in stakes" :key="s.stake_id" class="stake-item">
          <div class="si-img" :style="s.image_url ? { backgroundImage: `url(${s.image_url})` } : {}" />
          <div class="si-info">
            <div class="si-name">{{ s.card_name }}</div>
            <div class="si-yield">{{ s.daily_yield }} 积分/天 · 待领 <b>{{ s.pending }}</b></div>
          </div>
          <div class="si-actions">
            <el-button size="small" type="primary" plain :disabled="s.pending <= 0" @click="claim(s.stake_id)">领取</el-button>
            <el-button size="small" plain @click="unstake(s.stake_id)">赎回</el-button>
          </div>
        </div>
      </div>
    </section>

    <!-- 我的挂牌 -->
    <section class="block glass-inner">
      <h3>我的挂牌</h3>
      <div v-if="!listings.length" class="empty">暂无挂牌</div>
      <div v-else class="listing-list">
        <div v-for="l in listings" :key="l.listing_id" class="listing-item">
          <div class="li-img" :style="l.image_url ? { backgroundImage: `url(${l.image_url})` } : {}" />
          <div class="li-info">
            <div class="li-name">{{ l.card_name }} <span v-if="l.serial_no">#{{ l.serial_no }}</span></div>
            <div class="li-price">{{ l.current_price }} 积分 · {{ l.list_type === 'auction' ? '竞拍' : '一口价' }}</div>
          </div>
          <el-button size="small" plain @click="doCancel(l.listing_id)">下架</el-button>
        </div>
      </div>
    </section>

    <!-- 成就 -->
    <section class="block glass-inner">
      <h3>资产成就</h3>
      <div class="achv-grid">
        <div v-for="a in achievements" :key="a.code" class="achv" :class="{ unlocked: a.unlocked }">
          <span class="achv-name">{{ a.name }}</span>
          <span class="achv-desc">{{ a.desc }}</span>
        </div>
      </div>
    </section>

    <!-- 流转记录 -->
    <section class="block glass-inner">
      <h3>流转记录</h3>
      <div v-if="!history.length" class="empty">暂无记录</div>
      <ul v-else class="history">
        <li v-for="h in history" :key="h.id">
          <span class="h-kind" :class="h.kind">{{ kindLabel(h.kind, h.direction) }}</span>
          <span class="h-name">{{ h.card_name }}</span>
          <span class="h-amount" :class="h.direction">
            <template v-if="h.points_amount">{{ h.direction === 'in' && h.kind !== 'trade' ? '+' : '' }}{{ h.points_amount }} 积分</template>
            <template v-else>—</template>
          </span>
        </li>
      </ul>
    </section>

    <!-- 实名弹窗 -->
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
import AssetHubBar from '@/components/asset/AssetHubBar.vue'
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
const hubBarRef = ref<InstanceType<typeof AssetHubBar> | null>(null)

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

function onHubLoaded(s: AssetHubSummary | null) {
  hubSummary.value = s
}

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
  } finally {
    pageLoading.value = false
  }
}

async function claim(id: number) {
  try {
    const res = await claimStake(id)
    ElMessage.success(`领取 ${res.points_gained} 可用积分`)
    await Promise.all([loadAll(), fetchMe()])
    hubBarRef.value?.refresh()
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
.action-alerts {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 14px;
}
.action-alert {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border-radius: 10px;
  text-decoration: none;
  color: var(--wc-text-secondary);
  transition: transform 0.12s;
}
.action-alert:active {
  transform: scale(0.99);
}
.action-alert.duel {
  border-left: 3px solid #e85d5d;
}
.action-alert.stake {
  border-left: 3px solid var(--wc-accent-gold);
}
.action-alert.mint {
  border-left: 3px solid #7dd3a8;
}
.aa-icon {
  font-size: 1.1rem;
}
.aa-text {
  flex: 1;
  font-size: 0.82rem;
  font-weight: 500;
}
.aa-go {
  color: var(--wc-text-muted);
  font-size: 0.9rem;
}
.admin-link {
  text-align: right;
  margin: -6px 0 12px;
  font-size: 0.72rem;
}
.admin-link a {
  color: var(--wc-text-muted);
  text-decoration: none;
}
.admin-link a:hover {
  color: var(--wc-accent-gold);
}
.glass-inner {
  border-radius: 14px;
  padding: 16px;
  margin-bottom: 14px;
}
.overview {
  background: linear-gradient(135deg, rgba(60, 45, 25, 0.5), rgba(25, 20, 35, 0.7));
}
.ov-main {
  display: flex;
  flex-direction: column;
}
.ov-main .label {
  font-size: 0.74rem;
  color: var(--wc-text-muted);
}
.ov-main .value {
  font-size: 2rem;
  font-weight: 800;
  color: var(--wc-accent-gold);
  font-variant-numeric: tabular-nums;
}
.ov-stats {
  display: flex;
  gap: 24px;
  margin-top: 10px;
}
.ov-stat span {
  font-size: 0.7rem;
  color: var(--wc-text-muted);
}
.ov-stat b {
  display: block;
  font-size: 1rem;
  color: var(--wc-text-secondary);
}
.ov-disclaimer {
  margin: 10px 0 0;
  font-size: 0.64rem;
  color: var(--wc-text-muted);
  line-height: 1.4;
}
.realname.verified {
  opacity: 0.85;
}
.rn-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.rn-title {
  font-size: 0.95rem;
  color: var(--wc-text-secondary);
  font-weight: 600;
}
.rn-badge {
  font-size: 0.66rem;
  padding: 2px 8px;
  border-radius: 6px;
  background: rgba(160, 70, 70, 0.2);
  color: #e07a7a;
}
.rn-badge.ok {
  background: rgba(46, 160, 100, 0.18);
  color: #5fc88f;
}
.rn-desc {
  margin: 8px 0 10px;
  font-size: 0.76rem;
  color: var(--wc-text-muted);
}
.rn-note {
  font-size: 0.66rem;
  color: var(--wc-text-muted);
  margin: 4px 0 0;
}
.quick-nav {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  margin-bottom: 14px;
}
.qn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 12px 6px;
  text-decoration: none;
  text-align: center;
}
.qn span {
  font-size: 0.82rem;
  color: var(--wc-accent-gold);
  font-weight: 600;
}
.qn small {
  font-size: 0.6rem;
  color: var(--wc-text-muted);
}
.block h3 {
  margin: 0 0 12px;
  font-size: 0.95rem;
  color: var(--wc-text-secondary);
}
.muted {
  font-size: 0.68rem;
  color: var(--wc-text-muted);
  font-weight: 400;
}
.empty {
  font-size: 0.78rem;
  color: var(--wc-text-muted);
  padding: 6px 0;
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
}
.si-img,
.li-img {
  width: 42px;
  height: 56px;
  border-radius: 6px;
  background: linear-gradient(160deg, rgba(40, 30, 20, 0.6), rgba(20, 16, 30, 0.9));
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
  color: var(--wc-text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.si-yield,
.li-price {
  font-size: 0.7rem;
  color: var(--wc-text-muted);
}
.battalion-boost .bb-fav {
  margin: 0 0 10px;
  font-size: 0.82rem;
  color: var(--wc-text-secondary);
}
.battalion-boost .bb-fav b {
  color: #7dd3a8;
}
.bb-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 10px;
}
.bb-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  border-radius: 8px;
  background: rgba(125, 211, 168, 0.08);
  font-size: 0.78rem;
}
.bb-pct {
  color: #7dd3a8;
  font-weight: 700;
}
.bb-link {
  font-size: 0.72rem;
  color: var(--wc-accent-gold);
  text-decoration: none;
}
.si-yield b {
  color: var(--wc-accent-gold);
}
.si-actions {
  display: flex;
  gap: 4px;
}
.achv-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 8px;
}
.achv {
  padding: 10px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.03);
  opacity: 0.5;
}
.achv.unlocked {
  opacity: 1;
  background: linear-gradient(135deg, rgba(80, 60, 30, 0.4), rgba(40, 30, 50, 0.4));
  border: 1px solid rgba(231, 175, 92, 0.3);
}
.achv-name {
  display: block;
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--wc-accent-gold);
}
.achv-desc {
  font-size: 0.66rem;
  color: var(--wc-text-muted);
}
.history {
  margin: 0;
  padding: 0;
  list-style: none;
}
.history li {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}
.h-kind {
  font-size: 0.66rem;
  padding: 2px 8px;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.06);
  color: var(--wc-text-muted);
  white-space: nowrap;
}
.h-name {
  flex: 1;
  font-size: 0.8rem;
  color: var(--wc-text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.h-amount {
  font-size: 0.78rem;
  font-variant-numeric: tabular-nums;
  color: var(--wc-text-muted);
}
.h-amount.in {
  color: #5fc88f;
}
.h-amount.out {
  color: #e07a7a;
}
</style>
