<template>
  <div class="market-page page-shell mobile-page">
    <!-- 顶栏：与商城页一致的 glass-panel 风格 -->
    <header class="market-header glass-panel">
      <div class="header-row">
        <div class="header-copy">
          <span class="eyebrow">数字资产 · 二级流通</span>
          <h1>球星卡交易行</h1>
        </div>
        <button type="button" class="icon-refresh" :disabled="loading" aria-label="刷新" @click="reload">
          <span :class="{ spin: loading }">↻</span>
        </button>
      </div>

      <div class="stat-row">
        <div class="stat-pill primary">
          <span class="stat-label">可用积分</span>
          <strong class="stat-val tabular-nums">{{ redeemBalance != null ? redeemBalance.toLocaleString() : '—' }}</strong>
        </div>
        <div class="stat-pill">
          <span class="stat-label">当前在售</span>
          <strong class="stat-val tabular-nums">{{ loading ? '…' : listings.length }}</strong>
        </div>
      </div>

      <p class="header-note">以可用积分买卖球星卡 · 站内虚拟收藏 · 不可提现</p>

      <nav class="quick-links" aria-label="快捷入口">
        <router-link to="/collection" class="qlink">📋 去挂牌</router-link>
        <router-link to="/mint" class="qlink">✨ 首发打新</router-link>
        <router-link to="/me/assets" class="qlink">💎 我的资产</router-link>
      </nav>
    </header>

    <!-- 吸顶筛选条 -->
    <div class="sticky-tools">
      <div class="scope-segment" role="tablist">
        <button
          v-for="tab in scopeTabs"
          :key="tab.value"
          type="button"
          role="tab"
          class="seg-btn"
          :class="{ active: filters.scope === tab.value, mine: tab.value === 'mine' }"
          :aria-selected="filters.scope === tab.value"
          @click="setScope(tab.value)"
        >
          <span class="seg-icon" aria-hidden="true">{{ tab.icon }}</span>
          {{ tab.label }}
        </button>
      </div>

      <div class="sort-strip">
        <button
          v-for="chip in sortChips"
          :key="chip.value"
          type="button"
          class="sort-chip"
          :class="{ active: filters.sort === chip.value }"
          @click="toggleFilter('sort', chip.value)"
        >
          {{ chip.label }}
        </button>
        <button
          type="button"
          class="filter-toggle"
          :class="{ active: filtersExpanded || activeFilterCount > 0 }"
          @click="filtersExpanded = !filtersExpanded"
        >
          筛选
          <span v-if="activeFilterCount" class="filter-badge">{{ activeFilterCount }}</span>
          <span class="chev" :class="{ up: filtersExpanded }">▾</span>
        </button>
      </div>

      <Transition name="filter-slide">
        <div v-if="filtersExpanded" class="filter-drawer">
          <div class="drawer-group">
            <span class="drawer-label">稀有度</span>
            <div class="drawer-chips">
              <button
                v-for="chip in rarityChips"
                :key="chip.value"
                type="button"
                class="dchip"
                :class="{ active: filters.rarity === chip.value }"
                @click="toggleFilter('rarity', chip.value)"
              >
                {{ chip.label }}
              </button>
            </div>
          </div>
          <div class="drawer-group">
            <span class="drawer-label">类型</span>
            <div class="drawer-chips">
              <button
                v-for="chip in typeChips"
                :key="chip.value"
                type="button"
                class="dchip"
                :class="{ active: filters.list_type === chip.value }"
                @click="toggleFilter('list_type', chip.value)"
              >
                {{ chip.label }}
              </button>
            </div>
          </div>
          <button v-if="activeFilterCount" type="button" class="clear-filters" @click="clearFilters">清除筛选</button>
        </div>
      </Transition>
    </div>

    <!-- 列表 -->
    <main class="market-main">
      <div v-if="loading" class="market-grid">
        <div v-for="i in 6" :key="i" class="sk-card">
          <el-skeleton animated />
        </div>
      </div>

      <div v-else-if="!listings.length" class="empty-state glass-panel">
        <div class="empty-art">🏪</div>
        <h2>{{ emptyTitle }}</h2>
        <p>{{ emptyHint }}</p>
        <div class="empty-actions">
          <template v-if="filters.scope === 'mine'">
            <router-link to="/collection" class="cta-btn">去收藏册挂牌</router-link>
            <button type="button" class="cta-btn ghost" @click="setScope('all')">浏览全部</button>
          </template>
          <template v-else>
            <router-link to="/collection" class="cta-btn">去收藏册挂牌</router-link>
            <router-link to="/mint" class="cta-btn ghost">首发打新</router-link>
          </template>
        </div>
      </div>

      <div v-else class="market-grid">
        <article
          v-for="item in listings"
          :key="item.listing_id"
          class="listing-card"
          :class="[
            `rarity-${item.rarity}`,
            {
              mine: item.is_mine,
              auction: item.list_type === 'auction',
              'ending-soon': isEndingSoon(item.expires_at),
            },
          ]"
          @click="openDetail(item)"
        >
          <div class="card-frame">
            <div class="frame-top">
              <span class="pill rarity" :class="item.rarity">{{ rarityLabel(item.rarity) }}</span>
              <span class="pill mode">{{ item.list_type === 'auction' ? '竞拍' : '一口价' }}</span>
              <span v-if="item.is_mine" class="pill owner">我的</span>
              <span v-if="item.serial_no" class="pill serial">
                #{{ item.serial_no }}<template v-if="item.mint_total">/{{ item.mint_total }}</template>
              </span>
            </div>

            <div class="frame-art">
              <img
                v-if="item.image_url"
                :src="item.image_url"
                :alt="item.card_name"
                class="art-img"
                loading="lazy"
              />
              <div v-else class="art-img placeholder">{{ item.card_name.slice(0, 1) }}</div>
            </div>

            <div class="frame-bottom">
              <div class="name-block">
                <h3 class="card-name">
                  {{ item.card_name }}
                  <span v-if="item.star > 1" class="star">★{{ item.star }}</span>
                </h3>
                <p v-if="item.is_mine" class="sub-hint mine">点击管理 · 不可自购</p>
                <p v-else-if="item.list_type === 'auction'" class="sub-hint" :class="{ urgent: isEndingSoon(item.expires_at) }">
                  {{ countdown(item.expires_at) }}
                </p>
              </div>
              <div class="price-tag" :class="{ mine: item.is_mine }">
                <strong class="tabular-nums">{{ item.current_price }}</strong>
                <span>积分</span>
              </div>
            </div>
          </div>
        </article>
      </div>

      <div v-if="hasMore && !loading" class="load-more">
        <button type="button" class="load-btn" :disabled="loadingMore" @click="loadMore">
          {{ loadingMore ? '加载中…' : '加载更多' }}
        </button>
      </div>

      <p v-if="disclaimer" class="disclaimer">{{ disclaimer }}</p>
    </main>

    <!-- 详情弹窗 -->
    <el-dialog
      v-model="detailOpen"
      width="min(420px, 92vw)"
      align-center
      append-to-body
      class="market-detail-dialog"
      :show-close="true"
      @closed="onDetailClosed"
    >
      <template #header>
        <div v-if="detail" class="dialog-head">
          <h2>{{ detail.card_name }}</h2>
          <div class="dialog-tags">
            <span class="tag rarity" :class="detail.rarity">{{ rarityLabel(detail.rarity) }}</span>
            <span v-if="detail.is_mine" class="tag mine">我的挂牌</span>
          </div>
        </div>
      </template>

      <div v-if="detail" class="detail-body">
        <div class="detail-visual" :class="{ mine: detail.is_mine }">
          <img v-if="detail.image_url" :src="detail.image_url" :alt="detail.card_name" class="detail-photo" />
          <div v-else class="detail-photo placeholder">{{ detail.card_name.slice(0, 1) }}</div>
        </div>

        <div v-if="detail.is_mine" class="own-banner">
          <strong>这是你的挂牌</strong>
          <p>无法购买自己的卡牌，可下架或前往「我的资产」管理</p>
        </div>

        <div class="price-hero">
          <span class="ph-label">{{ detail.list_type === 'auction' ? '当前价' : '一口价' }}</span>
          <strong class="ph-val tabular-nums">{{ detail.current_price }}</strong>
          <span class="ph-unit">可用积分</span>
        </div>

        <dl class="detail-meta">
          <div class="meta-item">
            <dt>卖家</dt>
            <dd :class="{ mine: detail.is_mine }">{{ detail.is_mine ? '我' : '其他球迷' }}</dd>
          </div>
          <div class="meta-item">
            <dt>类型</dt>
            <dd>{{ detail.list_type === 'auction' ? '英式竞拍' : '一口价' }}</dd>
          </div>
          <div v-if="detail.list_type === 'auction'" class="meta-item">
            <dt>最小加价</dt>
            <dd>{{ detail.min_increment }}</dd>
          </div>
          <div v-if="detail.expires_at" class="meta-item">
            <dt>剩余</dt>
            <dd>{{ countdown(detail.expires_at) }}</dd>
          </div>
        </dl>

        <div v-if="detail.market" class="market-stats">
          <div class="stat"><span>地板价</span><b>{{ detail.market.floor_price ?? '—' }}</b></div>
          <div class="stat"><span>24h成交</span><b>{{ detail.market.trades_24h }}</b></div>
          <div class="stat"><span>24h额</span><b>{{ detail.market.volume_24h }}</b></div>
          <div class="stat"><span>回购价</span><b>{{ detail.market.buyback_floor }}</b></div>
        </div>
        <PriceSparkline v-if="detail.market?.history?.length" :points="detail.market.history.map(h => h.price)" />

        <div class="action-area">
          <template v-if="detail.is_mine">
            <el-button type="warning" :loading="acting" @click="doCancel">下架挂牌</el-button>
            <el-button plain @click="goMyListings">我的资产</el-button>
          </template>
          <template v-else-if="detail.list_type === 'fixed'">
            <el-button type="primary" size="large" :loading="acting" @click="doBuy">
              立即购买 · {{ detail.current_price }} 积分
            </el-button>
          </template>
          <template v-else>
            <el-input-number v-model="bidAmount" :min="minBid" :step="detail.min_increment || 10" size="large" />
            <el-button type="primary" size="large" :loading="acting" @click="doBid">出价</el-button>
          </template>
        </div>
        <p class="dialog-disclaimer">{{ detail.disclaimer }}</p>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRouter } from 'vue-router'
import {
  browseMarket,
  buyListing,
  bidListing,
  cancelListing,
  getListingDetail,
  getAssetHubSummary,
  type MarketListing,
} from '@/api/asset'
import { authState, fetchMe } from '@/stores/authStore'
import { extractApiError } from '@/utils/apiError'
import PriceSparkline from '@/components/asset/PriceSparkline.vue'
import { usePageMeta } from '@/composables/usePageMeta'
import { useCountdownTick, formatCountdown } from '@/composables/useCountdown'
import { useAssetRealname } from '@/composables/useAssetRealname'

usePageMeta({
  title: '球星卡交易行 — 最后一舞',
  description: '以可用积分合规流通球星卡资产，行情仅供站内收藏体验。',
  path: '/market',
  noIndex: true,
})

const router = useRouter()
const { ensureVerified } = useAssetRealname()
const tick = useCountdownTick()
const loading = ref(false)
const loadingMore = ref(false)
const listings = ref<MarketListing[]>([])
const page = ref(1)
const hasMore = ref(false)
const disclaimer = ref('')
const filters = reactive({
  rarity: '',
  list_type: '',
  sort: 'recent',
  scope: 'all' as 'all' | 'mine' | 'others',
})

const scopeTabs = [
  { value: 'all' as const, label: '全部', icon: '🌐' },
  { value: 'others' as const, label: '淘货', icon: '🛒' },
  { value: 'mine' as const, label: '我的', icon: '📌' },
]

const rarityChips = [
  { value: '', label: '全部' },
  { value: 'common', label: '普通' },
  { value: 'rare', label: '稀有' },
  { value: 'epic', label: '史诗' },
  { value: 'legend', label: '传奇' },
]

const typeChips = [
  { value: '', label: '全部' },
  { value: 'fixed', label: '一口价' },
  { value: 'auction', label: '竞拍' },
]

const sortChips = [
  { value: 'recent', label: '最新' },
  { value: 'price_asc', label: '价↑' },
  { value: 'price_desc', label: '价↓' },
  { value: 'ending', label: '将结束' },
]

const detailOpen = ref(false)
const detail = ref<Awaited<ReturnType<typeof getListingDetail>> | null>(null)
const bidAmount = ref(0)
const minBid = ref(0)
const acting = ref(false)
const redeemBalance = ref<number | null>(null)
const filtersExpanded = ref(false)

const activeFilterCount = computed(() => {
  let n = 0
  if (filters.rarity) n += 1
  if (filters.list_type) n += 1
  return n
})

const emptyTitle = computed(() => {
  if (filters.scope === 'mine') return '你还没有在售挂牌'
  if (filters.scope === 'others') return '暂无可购买的卡牌'
  return '暂无在售卡牌'
})

const emptyHint = computed(() => {
  if (filters.scope === 'mine') return '去收藏册选择卡牌挂牌出售'
  return '去图鉴挂牌，或参与首发打新'
})

const RARITY: Record<string, string> = { common: '普通', rare: '稀有', epic: '史诗', legend: '传奇' }
function rarityLabel(r: string) {
  return RARITY[r] || r
}

function toast(type: 'success' | 'warning' | 'error', message: string) {
  ElMessage({ type, message, appendTo: document.body, zIndex: 9999, grouping: true })
}

function countdown(iso?: string | null) {
  void tick.value
  return formatCountdown(iso)
}

function isEndingSoon(iso?: string | null): boolean {
  if (!iso) return false
  const end = new Date(iso).getTime()
  if (Number.isNaN(end)) return false
  return end - Date.now() < 24 * 60 * 60 * 1000 && end > Date.now()
}

function setScope(scope: 'all' | 'mine' | 'others') {
  if (filters.scope === scope) return
  filters.scope = scope
  reload()
}

function toggleFilter(key: 'rarity' | 'list_type' | 'sort', value: string) {
  if (key === 'sort') {
    filters.sort = value
  } else if (filters[key] === value) {
    filters[key] = ''
  } else {
    filters[key] = value
  }
  reload()
}

function clearFilters() {
  filters.rarity = ''
  filters.list_type = ''
  reload()
}

async function loadBalance() {
  try {
    const s = await getAssetHubSummary()
    redeemBalance.value = s.redeem_points
  } catch {
    redeemBalance.value = null
  }
}

function isMineListing(item: Pick<MarketListing, 'seller_id' | 'is_mine'>) {
  if (typeof item.is_mine === 'boolean') return item.is_mine
  return authState.user?.id != null && item.seller_id === authState.user.id
}

async function reload() {
  page.value = 1
  loading.value = true
  try {
    const res = await browseMarket({ ...cleanFilters(), page: 1, limit: 24 })
    listings.value = res.items.map((item) => ({ ...item, is_mine: isMineListing(item) }))
    hasMore.value = res.has_more
    disclaimer.value = res.disclaimer
    await loadBalance()
  } finally {
    loading.value = false
  }
}

function cleanFilters() {
  const f: Record<string, string> = { sort: filters.sort, scope: filters.scope }
  if (filters.rarity) f.rarity = filters.rarity
  if (filters.list_type) f.list_type = filters.list_type
  return f
}

async function loadMore() {
  loadingMore.value = true
  try {
    page.value += 1
    const res = await browseMarket({ ...cleanFilters(), page: page.value, limit: 24 })
    listings.value.push(...res.items.map((item) => ({ ...item, is_mine: isMineListing(item) })))
    hasMore.value = res.has_more
  } finally {
    loadingMore.value = false
  }
}

async function openDetail(item: MarketListing) {
  try {
    detail.value = await getListingDetail(item.listing_id)
    detail.value.is_mine = isMineListing(detail.value)
    minBid.value =
      (detail.value.current_bid || detail.value.price_points) +
      (detail.value.current_bid ? detail.value.min_increment : 0)
    bidAmount.value = minBid.value
    detailOpen.value = true
  } catch (e: unknown) {
    toast('error', extractApiError(e, '加载失败'))
  }
}

function onDetailClosed() {
  detail.value = null
}

function guardOwnListing(action: string): boolean {
  if (!detail.value?.is_mine) return true
  toast('warning', `这是你的挂牌，无法${action}`)
  return false
}

async function doBuy() {
  if (!detail.value) return
  if (!guardOwnListing('购买')) return
  if (!(await ensureVerified('购买卡牌'))) return
  acting.value = true
  try {
    const res = await buyListing(detail.value.listing_id)
    toast('success', res.notice || '购买成功')
    detailOpen.value = false
    await fetchMe()
    await reload()
  } catch (e: unknown) {
    toast('error', extractApiError(e, '购买失败'))
  } finally {
    acting.value = false
  }
}

async function doBid() {
  if (!detail.value) return
  if (!guardOwnListing('对自己的挂牌出价')) return
  if (!(await ensureVerified('竞拍出价'))) return
  acting.value = true
  try {
    const res = await bidListing(detail.value.listing_id, bidAmount.value)
    toast('success', `出价成功 · 当前 ${res.current_bid} 积分`)
    detailOpen.value = false
    await fetchMe()
    await reload()
  } catch (e: unknown) {
    toast('error', extractApiError(e, '出价失败'))
  } finally {
    acting.value = false
  }
}

async function doCancel() {
  if (!detail.value?.is_mine) return
  try {
    await ElMessageBox.confirm('确定下架该挂牌？卡牌将解锁并回到你的收藏册。', '下架挂牌', {
      customClass: 'wc-message-box',
      roundButton: true,
      confirmButtonText: '确认下架',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return
  }
  acting.value = true
  try {
    await cancelListing(detail.value.listing_id)
    toast('success', '已下架挂牌')
    detailOpen.value = false
    await reload()
  } catch (e: unknown) {
    toast('error', extractApiError(e, '下架失败'))
  } finally {
    acting.value = false
  }
}

function goMyListings() {
  router.push('/me/assets')
}

onMounted(reload)
</script>

<style scoped>
/* ===== 页面 ===== */
.market-page {
  max-width: 720px;
  margin: 0 auto;
}

/* ===== 顶栏 ===== */
.market-header {
  padding: 16px 16px 14px;
  margin-bottom: 12px;
  border-radius: 16px;
}
.header-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}
.eyebrow {
  display: block;
  font-size: 0.65rem;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: rgba(212, 165, 116, 0.75);
  margin-bottom: 4px;
}
.market-header h1 {
  margin: 0;
  font-size: 1.45rem;
  font-weight: 800;
  font-family: var(--wc-font-serif, inherit);
  color: var(--wc-text-primary, #f0ece4);
  line-height: 1.2;
}
.icon-refresh {
  flex-shrink: 0;
  width: 38px;
  height: 38px;
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.05);
  color: rgba(255, 255, 255, 0.75);
  font-size: 1.15rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}
.icon-refresh:disabled { opacity: 0.45; }
.icon-refresh .spin {
  display: inline-block;
  animation: spin 0.75s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.stat-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-bottom: 10px;
}
.stat-pill {
  padding: 10px 12px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.07);
}
.stat-pill.primary {
  background: linear-gradient(135deg, rgba(212, 165, 116, 0.14), rgba(180, 120, 60, 0.08));
  border-color: rgba(212, 165, 116, 0.25);
}
.stat-label {
  display: block;
  font-size: 0.65rem;
  color: rgba(255, 255, 255, 0.5);
  margin-bottom: 2px;
}
.stat-val {
  font-size: 1.25rem;
  font-weight: 800;
  color: var(--wc-text-primary, #f0ece4);
  line-height: 1.1;
}
.stat-pill.primary .stat-val {
  color: var(--wc-accent-gold, #e7af5c);
}
.header-note {
  margin: 0 0 12px;
  font-size: 0.72rem;
  color: rgba(255, 255, 255, 0.45);
  line-height: 1.45;
}
.quick-links {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.qlink {
  flex: 1;
  min-width: 0;
  text-align: center;
  padding: 8px 6px;
  border-radius: 10px;
  font-size: 0.72rem;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.75);
  text-decoration: none;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  transition: background 0.15s, border-color 0.15s;
}
.qlink:hover {
  background: rgba(212, 165, 116, 0.1);
  border-color: rgba(212, 165, 116, 0.25);
  color: var(--wc-accent-gold);
}

/* ===== 吸顶筛选 ===== */
.sticky-tools {
  position: sticky;
  top: calc(var(--wc-mobile-header-height, 52px) + 4px);
  z-index: 40;
  margin-bottom: 14px;
  padding: 8px;
  border-radius: 14px;
  background: rgba(10, 12, 26, 0.94);
  border: 1px solid rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(14px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
}
.scope-segment {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 4px;
  padding: 3px;
  margin-bottom: 8px;
  border-radius: 11px;
  background: rgba(0, 0, 0, 0.35);
}
.seg-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 9px 4px;
  border: none;
  border-radius: 9px;
  background: transparent;
  color: rgba(255, 255, 255, 0.5);
  font-size: 0.78rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
}
.seg-icon { font-size: 0.85rem; }
.seg-btn.active {
  background: rgba(212, 165, 116, 0.22);
  color: var(--wc-accent-gold);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.25);
}
.seg-btn.active.mine {
  background: rgba(70, 140, 220, 0.28);
  color: #a8d4ff;
}

.sort-strip {
  display: flex;
  gap: 5px;
  overflow-x: auto;
  scrollbar-width: none;
  -webkit-overflow-scrolling: touch;
}
.sort-strip::-webkit-scrollbar { display: none; }
.sort-chip {
  flex-shrink: 0;
  padding: 6px 12px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.03);
  color: rgba(255, 255, 255, 0.6);
  font-size: 0.72rem;
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
}
.sort-chip.active {
  border-color: rgba(212, 165, 116, 0.45);
  background: rgba(212, 165, 116, 0.14);
  color: var(--wc-accent-gold);
  font-weight: 600;
}
.filter-toggle {
  flex-shrink: 0;
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.04);
  color: rgba(255, 255, 255, 0.65);
  font-size: 0.72rem;
  font-weight: 600;
  cursor: pointer;
}
.filter-toggle.active {
  border-color: rgba(126, 184, 255, 0.4);
  color: #9fd0ff;
}
.filter-badge {
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  border-radius: 999px;
  background: #5a9ef0;
  color: #fff;
  font-size: 0.6rem;
  font-weight: 700;
  line-height: 16px;
  text-align: center;
}
.chev {
  font-size: 0.65rem;
  transition: transform 0.2s;
}
.chev.up { transform: rotate(180deg); }

.filter-drawer {
  padding-top: 10px;
  margin-top: 8px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}
.drawer-group { margin-bottom: 10px; }
.drawer-label {
  display: block;
  font-size: 0.62rem;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.4);
  margin-bottom: 6px;
  letter-spacing: 0.04em;
}
.drawer-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.dchip {
  padding: 5px 12px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.03);
  color: rgba(255, 255, 255, 0.65);
  font-size: 0.72rem;
  cursor: pointer;
}
.dchip.active {
  border-color: rgba(212, 165, 116, 0.45);
  background: rgba(212, 165, 116, 0.12);
  color: var(--wc-accent-gold);
}
.clear-filters {
  width: 100%;
  padding: 7px;
  border: none;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.04);
  color: rgba(255, 255, 255, 0.5);
  font-size: 0.72rem;
  cursor: pointer;
}
.filter-slide-enter-active,
.filter-slide-leave-active {
  transition: opacity 0.2s, max-height 0.25s ease;
  overflow: hidden;
  max-height: 200px;
}
.filter-slide-enter-from,
.filter-slide-leave-to {
  opacity: 0;
  max-height: 0;
}

/* ===== 卡牌网格 ===== */
.market-main {
  padding-bottom: 8px;
}
.market-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 14px;
}
@media (min-width: 560px) {
  .market-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

.listing-card {
  cursor: pointer;
  transition: transform 0.2s ease;
}
.listing-card:active { transform: scale(0.97); }

.card-frame {
  position: relative;
  display: flex;
  flex-direction: column;
  aspect-ratio: 3 / 4.35;
  border-radius: 16px;
  overflow: hidden;
  background: linear-gradient(165deg, #161a32 0%, #0e1020 100%);
  border: 1.5px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.35);
}
.listing-card.rarity-rare .card-frame {
  border-color: rgba(126, 184, 255, 0.45);
  box-shadow: 0 6px 22px rgba(126, 184, 255, 0.12);
}
.listing-card.rarity-epic .card-frame {
  border-color: rgba(201, 120, 138, 0.5);
  box-shadow: 0 6px 22px rgba(201, 120, 138, 0.15);
}
.listing-card.rarity-legend .card-frame {
  border-color: rgba(232, 197, 71, 0.55);
  box-shadow: 0 8px 26px rgba(232, 197, 71, 0.18);
}
.listing-card.mine .card-frame {
  border-color: rgba(90, 160, 240, 0.55);
  box-shadow: 0 0 0 1px rgba(90, 160, 240, 0.12), 0 6px 22px rgba(50, 110, 200, 0.18);
}
.listing-card.ending-soon .card-frame {
  outline: 2px solid rgba(255, 140, 80, 0.35);
  outline-offset: -1px;
}

.frame-top {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  z-index: 2;
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  padding: 8px;
  pointer-events: none;
}
.pill {
  font-size: 0.58rem;
  font-weight: 700;
  padding: 3px 8px;
  border-radius: 999px;
  background: rgba(6, 8, 18, 0.75);
  color: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(6px);
  border: 1px solid rgba(255, 255, 255, 0.1);
}
.pill.rarity.legend {
  background: linear-gradient(90deg, #b8860b, #e7af5c);
  color: #1a1208;
  border: none;
}
.pill.rarity.epic {
  background: rgba(138, 80, 184, 0.9);
  border: none;
}
.pill.rarity.rare {
  background: rgba(50, 100, 180, 0.88);
  border: none;
}
.pill.mode { color: #f0d9b5; }
.pill.owner {
  background: rgba(60, 130, 210, 0.88);
  border: none;
  color: #fff;
}
.pill.serial {
  margin-left: auto;
  color: #e8c88a;
  font-variant-numeric: tabular-nums;
}

.frame-art {
  flex: 1;
  min-height: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 28px 12px 8px;
  background: radial-gradient(ellipse at 50% 30%, rgba(212, 165, 116, 0.08), transparent 65%);
}
.art-img {
  width: 100%;
  height: 100%;
  max-height: 100%;
  object-fit: contain;
  object-position: center;
  display: block;
  filter: drop-shadow(0 4px 12px rgba(0, 0, 0, 0.4));
}
.art-img.placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 2.8rem;
  font-weight: 800;
  color: rgba(212, 165, 116, 0.25);
}

.frame-bottom {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  padding: 10px 10px 11px;
  background: linear-gradient(180deg, rgba(14, 16, 32, 0) 0%, rgba(14, 16, 32, 0.97) 20%);
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}
.name-block {
  flex: 1;
  min-width: 0;
}
.card-name {
  margin: 0;
  font-size: 0.84rem;
  font-weight: 700;
  color: #f5f0e8;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.25;
}
.card-name .star {
  color: var(--wc-accent-gold);
  font-size: 0.7rem;
}
.sub-hint {
  margin: 3px 0 0;
  font-size: 0.6rem;
  color: rgba(255, 255, 255, 0.4);
}
.sub-hint.mine { color: #7eb8ff; font-weight: 600; }
.sub-hint.urgent { color: #ff9a6c; font-weight: 600; }

.price-tag {
  flex-shrink: 0;
  text-align: right;
  padding: 6px 9px;
  border-radius: 10px;
  background: linear-gradient(135deg, rgba(212, 165, 116, 0.28), rgba(140, 90, 40, 0.2));
  border: 1px solid rgba(212, 165, 116, 0.35);
}
.price-tag strong {
  display: block;
  font-size: 1.05rem;
  font-weight: 800;
  color: var(--wc-accent-gold);
  line-height: 1;
}
.price-tag span {
  font-size: 0.55rem;
  color: rgba(255, 255, 255, 0.5);
}
.price-tag.mine {
  background: rgba(60, 130, 210, 0.2);
  border-color: rgba(100, 170, 240, 0.35);
}
.price-tag.mine strong { color: #9fd0ff; }

/* ===== 空态 / 加载 ===== */
.empty-state {
  text-align: center;
  padding: 40px 20px;
  border-radius: 16px;
}
.empty-art {
  font-size: 2.5rem;
  margin-bottom: 10px;
  opacity: 0.8;
}
.empty-state h2 {
  margin: 0 0 8px;
  font-size: 1rem;
  font-weight: 700;
  color: var(--wc-text-primary);
}
.empty-state p {
  margin: 0;
  font-size: 0.78rem;
  color: rgba(255, 255, 255, 0.45);
}
.empty-actions {
  display: flex;
  justify-content: center;
  gap: 10px;
  margin-top: 18px;
  flex-wrap: wrap;
}
.cta-btn {
  padding: 9px 18px;
  border-radius: 10px;
  background: linear-gradient(135deg, rgba(231, 175, 92, 0.3), rgba(160, 110, 50, 0.2));
  color: var(--wc-accent-gold);
  font-size: 0.82rem;
  font-weight: 600;
  text-decoration: none;
  border: 1px solid rgba(212, 165, 116, 0.35);
  cursor: pointer;
}
.cta-btn.ghost {
  background: rgba(255, 255, 255, 0.05);
  border-color: rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.7);
}
.sk-card {
  aspect-ratio: 3 / 4.35;
  border-radius: 16px;
  padding: 12px;
  background: rgba(16, 18, 34, 0.85);
  border: 1px solid rgba(255, 255, 255, 0.06);
}
.load-more {
  text-align: center;
  margin-top: 18px;
}
.load-btn {
  padding: 10px 32px;
  border-radius: 999px;
  border: 1px solid rgba(212, 165, 116, 0.3);
  background: rgba(212, 165, 116, 0.08);
  color: var(--wc-accent-gold);
  font-size: 0.82rem;
  font-weight: 600;
  cursor: pointer;
}
.load-btn:disabled { opacity: 0.55; }
.disclaimer {
  margin-top: 18px;
  font-size: 0.65rem;
  color: rgba(255, 255, 255, 0.32);
  line-height: 1.5;
  text-align: center;
}

/* ===== 详情弹窗 ===== */
.dialog-head h2 {
  margin: 0 0 6px;
  font-size: 1.1rem;
  color: #f0ece4;
}
.dialog-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.dialog-tags .tag {
  font-size: 0.62rem;
  font-weight: 700;
  padding: 3px 8px;
  border-radius: 999px;
  background: rgba(0, 0, 0, 0.5);
  color: #fff;
}
.dialog-tags .tag.rarity.legend {
  background: linear-gradient(90deg, #b8860b, #e7af5c);
  color: #1a1208;
}
.dialog-tags .tag.mine {
  background: rgba(60, 130, 210, 0.85);
}
.detail-body {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.detail-visual {
  border-radius: 14px;
  overflow: hidden;
  aspect-ratio: 4 / 3;
  background: #12152a;
  border: 1px solid rgba(255, 255, 255, 0.08);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
}
.detail-visual.mine {
  border-color: rgba(90, 160, 240, 0.45);
}
.detail-photo {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  display: block;
}
.detail-photo.placeholder {
  font-size: 3rem;
  color: rgba(212, 165, 116, 0.25);
}
.own-banner {
  padding: 12px 14px;
  border-radius: 12px;
  background: rgba(40, 90, 160, 0.18);
  border: 1px solid rgba(100, 180, 255, 0.28);
}
.own-banner strong {
  display: block;
  font-size: 0.88rem;
  color: #9fd0ff;
  margin-bottom: 4px;
}
.own-banner p {
  margin: 0;
  font-size: 0.72rem;
  color: rgba(255, 255, 255, 0.5);
  line-height: 1.45;
}
.price-hero {
  text-align: center;
  padding: 16px;
  border-radius: 14px;
  background: linear-gradient(135deg, rgba(212, 165, 116, 0.1), rgba(120, 80, 40, 0.06));
  border: 1px solid rgba(212, 165, 116, 0.22);
}
.ph-label {
  display: block;
  font-size: 0.68rem;
  color: rgba(255, 255, 255, 0.45);
  margin-bottom: 4px;
}
.ph-val {
  font-size: 2.1rem;
  font-weight: 800;
  color: var(--wc-accent-gold);
  line-height: 1;
}
.ph-unit {
  display: block;
  margin-top: 4px;
  font-size: 0.72rem;
  color: rgba(255, 255, 255, 0.4);
}
.detail-meta {
  margin: 0;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
.meta-item {
  padding: 10px 12px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.05);
}
.meta-item dt {
  margin: 0;
  font-size: 0.62rem;
  color: rgba(255, 255, 255, 0.42);
}
.meta-item dd {
  margin: 3px 0 0;
  font-size: 0.9rem;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.9);
}
.meta-item dd.mine { color: #8ec8ff; }
.market-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 6px;
}
.market-stats .stat {
  text-align: center;
  padding: 8px 4px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.04);
}
.market-stats .stat span {
  display: block;
  font-size: 0.58rem;
  color: rgba(255, 255, 255, 0.42);
}
.market-stats .stat b {
  font-size: 0.88rem;
  color: rgba(255, 255, 255, 0.85);
  font-variant-numeric: tabular-nums;
}
.action-area {
  display: flex;
  gap: 8px;
  align-items: center;
}
.action-area .el-button { flex: 1; }
.dialog-disclaimer {
  font-size: 0.65rem;
  color: rgba(255, 255, 255, 0.35);
  line-height: 1.4;
  margin: 0;
  text-align: center;
}
.tabular-nums { font-variant-numeric: tabular-nums; }
</style>

<style>
/* 弹窗全局样式（非 scoped） */
.market-detail-dialog .el-dialog {
  background: #12152a !important;
  border: 1px solid rgba(212, 165, 116, 0.15);
  border-radius: 16px !important;
}
.market-detail-dialog .el-dialog__header {
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}
.market-detail-dialog .el-dialog__body {
  padding-top: 12px;
}
</style>
