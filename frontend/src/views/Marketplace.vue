<template>
  <div class="market-page page-shell mobile-page">
    <!-- 不透明内容区，避免背景人像干扰阅读 -->
    <div class="market-shell">
      <header class="market-hero">
        <div class="hero-row">
          <div>
            <h1>球星卡交易行</h1>
            <p class="hero-sub">站内积分流通 · 虚拟收藏 · 不可提现</p>
          </div>
          <div v-if="redeemBalance != null" class="hero-balance">
            <span class="hb-label">可用积分</span>
            <strong class="hb-val tabular-nums">{{ redeemBalance.toLocaleString() }}</strong>
          </div>
        </div>
      </header>

      <AssetHubBar compact :show-balance="false" />

      <!-- 筛选区：Tab + 芯片，合并为一块 -->
      <section class="filter-panel" aria-label="筛选与范围">
        <div class="scope-row" role="tablist">
          <button
            v-for="tab in scopeTabs"
            :key="tab.value"
            type="button"
            role="tab"
            class="scope-pill"
            :class="{ active: filters.scope === tab.value, mine: tab.value === 'mine' }"
            :aria-selected="filters.scope === tab.value"
            @click="setScope(tab.value)"
          >
            {{ tab.label }}
          </button>
        </div>

        <div class="chip-scroll" aria-label="筛选条件">
          <button
            v-for="chip in rarityChips"
            :key="chip.value"
            type="button"
            class="filter-chip"
            :class="{ active: filters.rarity === chip.value }"
            @click="toggleFilter('rarity', chip.value)"
          >
            {{ chip.label }}
          </button>
          <span class="chip-divider" aria-hidden="true" />
          <button
            v-for="chip in typeChips"
            :key="chip.value"
            type="button"
            class="filter-chip"
            :class="{ active: filters.list_type === chip.value }"
            @click="toggleFilter('list_type', chip.value)"
          >
            {{ chip.label }}
          </button>
          <span class="chip-divider" aria-hidden="true" />
          <button
            v-for="chip in sortChips"
            :key="chip.value"
            type="button"
            class="filter-chip"
            :class="{ active: filters.sort === chip.value }"
            @click="toggleFilter('sort', chip.value)"
          >
            {{ chip.label }}
          </button>
        </div>

        <div class="filter-actions">
          <span v-if="listings.length" class="result-count">{{ listings.length }} 件在售</span>
          <button type="button" class="icon-btn" :disabled="loading" aria-label="刷新" @click="reload">
            <span :class="{ spin: loading }">↻</span>
          </button>
          <button type="button" class="text-btn" @click="goMyListings">资产管理</button>
        </div>
      </section>

      <!-- 列表 -->
      <div v-if="loading" class="market-grid">
        <div v-for="i in 6" :key="i" class="sk-card">
          <el-skeleton :rows="0" animated />
          <el-skeleton :rows="2" animated />
        </div>
      </div>
      <div v-else-if="!listings.length" class="empty-state">
        <div class="empty-icon">🏪</div>
        <p>{{ emptyTitle }}</p>
        <span>{{ emptyHint }}</span>
        <div class="empty-actions">
          <template v-if="filters.scope === 'mine'">
            <router-link to="/collection" class="empty-btn">去收藏册挂牌</router-link>
            <button type="button" class="empty-btn secondary" @click="setScope('all')">浏览全部</button>
          </template>
          <template v-else>
            <router-link to="/collection" class="empty-btn">去收藏册挂牌</router-link>
            <router-link to="/mint" class="empty-btn secondary">首发打新</router-link>
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
          <div v-if="item.is_mine" class="mine-ribbon">我的</div>

          <div class="card-visual">
            <img
              v-if="item.image_url"
              :src="item.image_url"
              :alt="item.card_name"
              class="card-photo"
              loading="lazy"
            />
            <div v-else class="card-photo placeholder">{{ item.card_name.slice(0, 1) }}</div>
            <div class="card-scrim" aria-hidden="true" />

            <div class="tag-row">
              <span class="tag rarity" :class="item.rarity">{{ rarityLabel(item.rarity) }}</span>
              <span class="tag type">{{ item.list_type === 'auction' ? '竞拍' : '一口价' }}</span>
              <span v-if="item.serial_no" class="tag serial">
                #{{ item.serial_no }}<template v-if="item.mint_total">/{{ item.mint_total }}</template>
              </span>
            </div>
          </div>

          <div class="card-foot">
            <div class="foot-main">
              <h3 class="card-title">
                {{ item.card_name }}
                <span v-if="item.star > 1" class="star">★{{ item.star }}</span>
              </h3>
              <div class="price-line">
                <strong class="price tabular-nums">{{ item.current_price }}</strong>
                <span class="unit">积分</span>
              </div>
            </div>
            <div class="foot-action" :class="{ mine: item.is_mine }">
              <template v-if="item.is_mine">管理</template>
              <template v-else-if="item.list_type === 'auction'">
                {{ isEndingSoon(item.expires_at) ? '抢拍' : '出价' }}
              </template>
              <template v-else>购买</template>
            </div>
          </div>

          <div v-if="item.is_mine" class="mine-footnote">不可自购</div>
          <div
            v-else-if="item.list_type === 'auction'"
            class="auction-footnote"
            :class="{ urgent: isEndingSoon(item.expires_at) }"
          >
            {{ countdown(item.expires_at) }}
          </div>
        </article>
      </div>

      <div v-if="hasMore && !loading" class="load-more">
        <button type="button" class="load-btn" :disabled="loadingMore" @click="loadMore">
          {{ loadingMore ? '加载中…' : '加载更多' }}
        </button>
      </div>

      <p class="disclaimer">{{ disclaimer }}</p>
    </div>

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
import AssetHubBar from '@/components/asset/AssetHubBar.vue'
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
  { value: 'all' as const, label: '全部' },
  { value: 'others' as const, label: '淘货' },
  { value: 'mine' as const, label: '我的' },
]

const rarityChips = [
  { value: '', label: '全部稀有度' },
  { value: 'common', label: '普通' },
  { value: 'rare', label: '稀有' },
  { value: 'epic', label: '史诗' },
  { value: 'legend', label: '传奇' },
]

const typeChips = [
  { value: '', label: '全部类型' },
  { value: 'fixed', label: '一口价' },
  { value: 'auction', label: '竞拍' },
]

const sortChips = [
  { value: 'recent', label: '最新' },
  { value: 'price_asc', label: '价低→高' },
  { value: 'price_desc', label: '价高→低' },
  { value: 'ending', label: '将结束' },
]

const detailOpen = ref(false)
const detail = ref<Awaited<ReturnType<typeof getListingDetail>> | null>(null)
const bidAmount = ref(0)
const minBid = ref(0)
const acting = ref(false)
const redeemBalance = ref<number | null>(null)

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
/* ===== 页面容器：不透明底板 ===== */
.market-page {
  max-width: 960px;
  margin: 0 auto;
}

.market-shell {
  background: rgba(8, 10, 22, 0.92);
  border: 1px solid rgba(212, 165, 116, 0.12);
  border-radius: 16px;
  padding: 14px 14px 20px;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.45);
  backdrop-filter: blur(12px);
}

/* ===== Hero ===== */
.market-hero {
  margin-bottom: 12px;
}
.hero-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}
.market-hero h1 {
  margin: 0;
  font-size: 1.35rem;
  font-weight: 800;
  color: var(--wc-accent-gold);
  letter-spacing: 0.02em;
}
.hero-sub {
  margin: 4px 0 0;
  font-size: 0.72rem;
  color: rgba(255, 255, 255, 0.55);
  line-height: 1.4;
}
.hero-balance {
  flex-shrink: 0;
  text-align: right;
  padding: 8px 12px;
  border-radius: 10px;
  background: rgba(212, 165, 116, 0.1);
  border: 1px solid rgba(212, 165, 116, 0.22);
}
.hb-label {
  display: block;
  font-size: 0.62rem;
  color: rgba(255, 255, 255, 0.5);
}
.hb-val {
  font-size: 1.1rem;
  font-weight: 800;
  color: var(--wc-accent-gold);
}

/* ===== 筛选面板 ===== */
.filter-panel {
  background: rgba(16, 18, 34, 0.95);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 12px;
  padding: 10px;
  margin-bottom: 14px;
}
.scope-row {
  display: flex;
  gap: 6px;
  margin-bottom: 10px;
  padding: 3px;
  background: rgba(0, 0, 0, 0.25);
  border-radius: 10px;
}
.scope-pill {
  flex: 1;
  padding: 8px 4px;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: rgba(255, 255, 255, 0.55);
  font-size: 0.82rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}
.scope-pill.active {
  background: rgba(212, 165, 116, 0.2);
  color: var(--wc-accent-gold);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}
.scope-pill.active.mine {
  background: rgba(80, 150, 230, 0.22);
  color: #9fd0ff;
}
.chip-scroll {
  display: flex;
  gap: 6px;
  overflow-x: auto;
  padding-bottom: 4px;
  margin-bottom: 8px;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: none;
}
.chip-scroll::-webkit-scrollbar {
  display: none;
}
.filter-chip {
  flex-shrink: 0;
  padding: 5px 11px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.04);
  color: rgba(255, 255, 255, 0.65);
  font-size: 0.72rem;
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
  transition: border-color 0.15s, background 0.15s, color 0.15s;
}
.filter-chip.active {
  border-color: rgba(212, 165, 116, 0.5);
  background: rgba(212, 165, 116, 0.15);
  color: var(--wc-accent-gold);
}
.chip-divider {
  width: 1px;
  flex-shrink: 0;
  align-self: stretch;
  margin: 4px 2px;
  background: rgba(255, 255, 255, 0.08);
}
.filter-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.result-count {
  flex: 1;
  font-size: 0.72rem;
  color: rgba(255, 255, 255, 0.45);
}
.icon-btn {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.05);
  color: rgba(255, 255, 255, 0.7);
  cursor: pointer;
  font-size: 1rem;
  display: flex;
  align-items: center;
  justify-content: center;
}
.icon-btn:disabled {
  opacity: 0.5;
}
.icon-btn .spin {
  display: inline-block;
  animation: spin 0.8s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
.text-btn {
  padding: 6px 12px;
  border-radius: 8px;
  border: 1px solid rgba(212, 165, 116, 0.3);
  background: rgba(212, 165, 116, 0.1);
  color: var(--wc-accent-gold);
  font-size: 0.72rem;
  font-weight: 600;
  cursor: pointer;
}

/* ===== 卡牌网格 ===== */
.market-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}
@media (min-width: 640px) {
  .market-grid {
    grid-template-columns: repeat(auto-fill, minmax(168px, 1fr));
  }
}

.listing-card {
  position: relative;
  border-radius: 14px;
  overflow: hidden;
  cursor: pointer;
  background: #12152a;
  border: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.35);
  transition: transform 0.18s ease, box-shadow 0.18s ease;
}
.listing-card:active {
  transform: scale(0.98);
}
.listing-card.rarity-legend {
  border-color: rgba(231, 175, 92, 0.45);
}
.listing-card.rarity-epic {
  border-color: rgba(168, 120, 224, 0.4);
}
.listing-card.rarity-rare {
  border-color: rgba(100, 160, 220, 0.3);
}
.listing-card.mine {
  border-color: rgba(90, 160, 240, 0.55);
  box-shadow: 0 0 0 1px rgba(90, 160, 240, 0.15), 0 4px 20px rgba(40, 100, 180, 0.15);
}
.listing-card.ending-soon {
  outline: 1px solid rgba(255, 140, 80, 0.4);
}

.mine-ribbon {
  position: absolute;
  top: 10px;
  right: -28px;
  z-index: 3;
  width: 96px;
  padding: 4px 0;
  text-align: center;
  font-size: 0.62rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  color: #fff;
  background: linear-gradient(90deg, #3a7bd5, #5a9ef0);
  transform: rotate(36deg);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

.card-visual {
  position: relative;
  aspect-ratio: 3 / 3.6;
  background: linear-gradient(165deg, #1a1e38 0%, #0d0f1c 100%);
  overflow: hidden;
}
.card-photo {
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center top;
  display: block;
}
.card-photo.placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 2.4rem;
  font-weight: 800;
  color: rgba(212, 165, 116, 0.35);
  background: linear-gradient(160deg, #222640, #141828);
}
.card-scrim {
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, rgba(0, 0, 0, 0.15) 0%, rgba(0, 0, 0, 0) 35%, rgba(0, 0, 0, 0.55) 100%);
  pointer-events: none;
}

.tag-row {
  position: absolute;
  top: 8px;
  left: 8px;
  right: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  z-index: 2;
}
.tag {
  font-size: 0.58rem;
  font-weight: 700;
  padding: 3px 7px;
  border-radius: 6px;
  background: rgba(0, 0, 0, 0.65);
  color: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(4px);
}
.tag.rarity.legend {
  background: linear-gradient(90deg, #b8860b, #e7af5c);
  color: #1a1208;
}
.tag.rarity.epic {
  background: rgba(138, 80, 184, 0.9);
}
.tag.rarity.rare {
  background: rgba(50, 100, 180, 0.85);
}
.tag.type {
  color: #f0d9b5;
}
.tag.serial {
  margin-left: auto;
  color: #e8c88a;
  font-variant-numeric: tabular-nums;
}
.tag.mine {
  background: rgba(60, 130, 210, 0.85);
  color: #fff;
}

.card-foot {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 10px 8px;
  background: #12152a;
}
.foot-main {
  flex: 1;
  min-width: 0;
}
.card-title {
  margin: 0;
  font-size: 0.84rem;
  font-weight: 700;
  color: #f0ece4;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.card-title .star {
  color: var(--wc-accent-gold);
  font-size: 0.72rem;
  margin-left: 2px;
}
.price-line {
  display: flex;
  align-items: baseline;
  gap: 3px;
  margin-top: 3px;
}
.price-line .price {
  font-size: 1.15rem;
  font-weight: 800;
  color: var(--wc-accent-gold);
  line-height: 1;
}
.price-line .unit {
  font-size: 0.62rem;
  color: rgba(255, 255, 255, 0.45);
}
.foot-action {
  flex-shrink: 0;
  padding: 6px 10px;
  border-radius: 8px;
  font-size: 0.72rem;
  font-weight: 700;
  background: linear-gradient(135deg, rgba(212, 165, 116, 0.35), rgba(160, 110, 50, 0.25));
  color: #fff8ee;
  border: 1px solid rgba(212, 165, 116, 0.4);
}
.foot-action.mine {
  background: rgba(60, 130, 210, 0.25);
  border-color: rgba(100, 170, 240, 0.45);
  color: #b8dcff;
}
.mine-footnote,
.auction-footnote {
  padding: 0 10px 8px;
  font-size: 0.62rem;
  font-weight: 600;
  text-align: center;
  background: #12152a;
}
.mine-footnote {
  color: #7eb8ff;
}
.auction-footnote {
  color: #f0b86c;
}
.auction-footnote.urgent {
  color: #ff9a6c;
}

/* ===== 空态 / 加载 ===== */
.empty-state {
  text-align: center;
  padding: 36px 16px;
  background: rgba(16, 18, 34, 0.8);
  border-radius: 12px;
  border: 1px dashed rgba(255, 255, 255, 0.08);
}
.empty-icon {
  font-size: 2rem;
  margin-bottom: 8px;
  opacity: 0.7;
}
.empty-state p {
  margin: 0 0 6px;
  font-size: 0.95rem;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.85);
}
.empty-state span {
  font-size: 0.78rem;
  color: rgba(255, 255, 255, 0.45);
}
.empty-actions {
  display: flex;
  justify-content: center;
  gap: 10px;
  margin-top: 16px;
  flex-wrap: wrap;
}
.empty-btn {
  padding: 8px 16px;
  border-radius: 8px;
  background: linear-gradient(135deg, rgba(231, 175, 92, 0.25), rgba(180, 130, 60, 0.15));
  color: var(--wc-accent-gold);
  font-size: 0.82rem;
  font-weight: 600;
  text-decoration: none;
  border: none;
  cursor: pointer;
}
.empty-btn.secondary {
  background: rgba(255, 255, 255, 0.06);
  color: rgba(255, 255, 255, 0.7);
}
.sk-card {
  border-radius: 14px;
  padding: 10px;
  background: rgba(16, 18, 34, 0.8);
}
.load-more {
  text-align: center;
  margin-top: 16px;
}
.load-btn {
  padding: 10px 28px;
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.05);
  color: rgba(255, 255, 255, 0.75);
  font-size: 0.82rem;
  font-weight: 600;
  cursor: pointer;
}
.load-btn:disabled {
  opacity: 0.6;
}
.disclaimer {
  margin-top: 16px;
  font-size: 0.65rem;
  color: rgba(255, 255, 255, 0.35);
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
}
.detail-body {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.detail-visual {
  border-radius: 12px;
  overflow: hidden;
  aspect-ratio: 16 / 10;
  background: #12152a;
  border: 1px solid rgba(255, 255, 255, 0.08);
}
.detail-visual.mine {
  border-color: rgba(90, 160, 240, 0.45);
}
.detail-photo {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.detail-photo.placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 3rem;
  color: rgba(212, 165, 116, 0.3);
}
.own-banner {
  padding: 12px 14px;
  border-radius: 10px;
  background: rgba(40, 90, 160, 0.2);
  border: 1px solid rgba(100, 180, 255, 0.3);
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
  color: rgba(255, 255, 255, 0.55);
  line-height: 1.45;
}
.price-hero {
  text-align: center;
  padding: 14px;
  border-radius: 12px;
  background: rgba(212, 165, 116, 0.08);
  border: 1px solid rgba(212, 165, 116, 0.2);
}
.ph-label {
  display: block;
  font-size: 0.68rem;
  color: rgba(255, 255, 255, 0.5);
  margin-bottom: 4px;
}
.ph-val {
  font-size: 2rem;
  font-weight: 800;
  color: var(--wc-accent-gold);
  line-height: 1;
}
.ph-unit {
  display: block;
  margin-top: 4px;
  font-size: 0.72rem;
  color: rgba(255, 255, 255, 0.45);
}
.detail-meta {
  margin: 0;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
.meta-item {
  padding: 8px 10px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.04);
}
.meta-item dt {
  margin: 0;
  font-size: 0.62rem;
  color: rgba(255, 255, 255, 0.45);
}
.meta-item dd {
  margin: 2px 0 0;
  font-size: 0.88rem;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.9);
}
.meta-item dd.mine {
  color: #8ec8ff;
}
.market-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 6px;
}
.market-stats .stat {
  text-align: center;
  padding: 8px 4px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.04);
}
.market-stats .stat span {
  display: block;
  font-size: 0.58rem;
  color: rgba(255, 255, 255, 0.45);
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
.action-area .el-button {
  flex: 1;
}
.dialog-disclaimer {
  font-size: 0.65rem;
  color: rgba(255, 255, 255, 0.4);
  line-height: 1.4;
  margin: 0;
  text-align: center;
}

.tabular-nums {
  font-variant-numeric: tabular-nums;
}
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
