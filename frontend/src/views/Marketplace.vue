<template>
  <div class="market-page">
    <div class="page-header">
      <h1>球星卡交易行</h1>
      <p class="subtitle">以可用积分流通你的球星资产 · 站内虚拟收藏，无现金价值、不可提现</p>
    </div>

    <AssetHubBar compact :show-balance="false" />

    <div class="market-toolbar glass-inner">
      <el-select v-model="filters.rarity" placeholder="稀有度" clearable size="small" @change="reload">
        <el-option label="普通" value="common" />
        <el-option label="稀有" value="rare" />
        <el-option label="史诗" value="epic" />
        <el-option label="传奇" value="legend" />
      </el-select>
      <el-select v-model="filters.list_type" placeholder="类型" clearable size="small" @change="reload">
        <el-option label="一口价" value="fixed" />
        <el-option label="竞拍" value="auction" />
      </el-select>
      <el-select v-model="filters.sort" size="small" @change="reload">
        <el-option label="最新" value="recent" />
        <el-option label="价格低→高" value="price_asc" />
        <el-option label="价格高→低" value="price_desc" />
        <el-option label="即将结束" value="ending" />
      </el-select>
      <div class="spacer" />
      <span v-if="redeemBalance != null" class="balance-chip">
        可用 <b>{{ redeemBalance.toLocaleString() }}</b> 积分
      </span>
      <el-button size="small" plain :loading="loading" @click="reload">刷新</el-button>
      <el-button size="small" plain @click="goMyListings">我的挂牌</el-button>
    </div>

    <div v-if="loading" class="market-grid">
      <el-skeleton v-for="i in 6" :key="i" :rows="3" animated class="sk-card" />
    </div>
    <div v-else-if="!listings.length" class="empty-state glass-inner">
      <p>暂无在售卡牌</p>
      <span>去图鉴挂牌你的第一张资产，或参与首发打新</span>
      <div class="empty-actions">
        <router-link to="/collection" class="empty-btn">去收藏册挂牌</router-link>
        <router-link to="/mint" class="empty-btn secondary">首发打新</router-link>
      </div>
    </div>
    <div v-else class="market-grid">
      <div
        v-for="item in listings"
        :key="item.listing_id"
        class="market-card glass-inner"
        :class="[item.rarity, { 'ending-soon': isEndingSoon(item.expires_at) }]"
        @click="openDetail(item)"
      >
        <div class="card-img" :style="item.image_url ? { backgroundImage: `url(${item.image_url})` } : {}">
          <span class="rarity-badge" :class="item.rarity">{{ rarityLabel(item.rarity) }}</span>
          <span v-if="item.serial_no" class="serial">#{{ item.serial_no }}<template v-if="item.mint_total">/{{ item.mint_total }}</template></span>
          <span class="type-badge" :class="item.list_type">{{ item.list_type === 'auction' ? '竞拍' : '一口价' }}</span>
        </div>
        <div class="card-body">
          <div class="name">{{ item.card_name }} <span v-if="item.star > 1" class="star">★{{ item.star }}</span></div>
          <div class="price-row">
            <span class="price">{{ item.current_price }}</span>
            <span class="unit">可用积分</span>
          </div>
          <div v-if="item.list_type === 'auction'" class="countdown" :class="{ urgent: isEndingSoon(item.expires_at) }">
            {{ countdown(item.expires_at) }}
          </div>
        </div>
      </div>
    </div>

    <div v-if="hasMore && !loading" class="load-more">
      <el-button plain :loading="loadingMore" @click="loadMore">加载更多</el-button>
    </div>

    <p class="disclaimer">{{ disclaimer }}</p>

    <!-- 挂牌详情 -->
    <el-dialog v-model="detailOpen" :title="detail?.card_name" width="min(440px, 94vw)" align-center append-to-body class="market-detail-dialog">
      <div v-if="detail" class="detail-body">
        <div class="detail-img" :style="detail.image_url ? { backgroundImage: `url(${detail.image_url})` } : {}">
          <span class="rarity-badge" :class="detail.rarity">{{ rarityLabel(detail.rarity) }}</span>
          <span v-if="detail.serial_no" class="serial">#{{ detail.serial_no }}<template v-if="detail.mint_total">/{{ detail.mint_total }}</template></span>
        </div>
        <div class="detail-meta">
          <div class="meta-row"><span>类型</span><strong>{{ detail.list_type === 'auction' ? '英式竞拍' : '一口价' }}</strong></div>
          <div class="meta-row"><span>{{ detail.list_type === 'auction' ? '当前价' : '价格' }}</span><strong class="gold">{{ detail.current_price }} 可用积分</strong></div>
          <div v-if="detail.list_type === 'auction'" class="meta-row"><span>最小加价</span><strong>{{ detail.min_increment }}</strong></div>
          <div v-if="detail.expires_at" class="meta-row"><span>剩余</span><strong>{{ countdown(detail.expires_at) }}</strong></div>
        </div>

        <div v-if="detail.market" class="market-stats">
          <div class="stat"><span>地板价</span><b>{{ detail.market.floor_price ?? '—' }}</b></div>
          <div class="stat"><span>24h成交</span><b>{{ detail.market.trades_24h }}</b></div>
          <div class="stat"><span>24h额</span><b>{{ detail.market.volume_24h }}</b></div>
          <div class="stat"><span>回购价</span><b>{{ detail.market.buyback_floor }}</b></div>
        </div>
        <PriceSparkline v-if="detail.market?.history?.length" :points="detail.market.history.map(h => h.price)" />

        <div class="action-area">
          <template v-if="detail.list_type === 'fixed'">
            <el-button type="primary" :loading="acting" @click="doBuy">立即购买 · {{ detail.current_price }} 积分</el-button>
          </template>
          <template v-else>
            <el-input-number v-model="bidAmount" :min="minBid" :step="detail.min_increment || 10" size="large" />
            <el-button type="primary" :loading="acting" @click="doBid">出价</el-button>
          </template>
        </div>
        <p class="dialog-disclaimer">{{ detail.disclaimer }}</p>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import {
  browseMarket,
  buyListing,
  bidListing,
  getListingDetail,
  getAssetHubSummary,
  type MarketListing,
} from '@/api/asset'
import AssetHubBar from '@/components/asset/AssetHubBar.vue'
import { fetchMe } from '@/stores/authStore'
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
const filters = reactive({ rarity: '', list_type: '', sort: 'recent' })

const detailOpen = ref(false)
const detail = ref<Awaited<ReturnType<typeof getListingDetail>> | null>(null)
const bidAmount = ref(0)
const minBid = ref(0)
const acting = ref(false)
const redeemBalance = ref<number | null>(null)

const RARITY: Record<string, string> = { common: '普通', rare: '稀有', epic: '史诗', legend: '传奇' }
function rarityLabel(r: string) {
  return RARITY[r] || r
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

async function loadBalance() {
  try {
    const s = await getAssetHubSummary()
    redeemBalance.value = s.redeem_points
  } catch {
    redeemBalance.value = null
  }
}

async function reload() {
  page.value = 1
  loading.value = true
  try {
    const res = await browseMarket({ ...cleanFilters(), page: 1, limit: 24 })
    listings.value = res.items
    hasMore.value = res.has_more
    disclaimer.value = res.disclaimer
    await loadBalance()
  } finally {
    loading.value = false
  }
}

function cleanFilters() {
  const f: Record<string, string> = { sort: filters.sort }
  if (filters.rarity) f.rarity = filters.rarity
  if (filters.list_type) f.list_type = filters.list_type
  return f
}

async function loadMore() {
  loadingMore.value = true
  try {
    page.value += 1
    const res = await browseMarket({ ...cleanFilters(), page: page.value, limit: 24 })
    listings.value.push(...res.items)
    hasMore.value = res.has_more
  } finally {
    loadingMore.value = false
  }
}

async function openDetail(item: MarketListing) {
  try {
    detail.value = await getListingDetail(item.listing_id)
    minBid.value = (detail.value.current_bid || detail.value.price_points) + (detail.value.current_bid ? detail.value.min_increment : 0)
    bidAmount.value = minBid.value
    detailOpen.value = true
  } catch (e: unknown) {
    ElMessage.error(extractApiError(e, '加载失败'))
  }
}

async function doBuy() {
  if (!detail.value) return
  if (!(await ensureVerified('购买卡牌'))) return
  acting.value = true
  try {
    const res = await buyListing(detail.value.listing_id)
    ElMessage.success(res.notice || '购买成功')
    detailOpen.value = false
    await fetchMe()
    await reload()
  } catch (e: unknown) {
    ElMessage.error(extractApiError(e, '购买失败'))
  } finally {
    acting.value = false
  }
}

async function doBid() {
  if (!detail.value) return
  if (!(await ensureVerified('竞拍出价'))) return
  acting.value = true
  try {
    const res = await bidListing(detail.value.listing_id, bidAmount.value)
    ElMessage.success(`出价成功 · 当前 ${res.current_bid} 积分`)
    detailOpen.value = false
    await fetchMe()
    await reload()
  } catch (e: unknown) {
    ElMessage.error(extractApiError(e, '出价失败'))
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
.market-page {
  max-width: 960px;
  margin: 0 auto;
  padding-bottom: calc(var(--wc-bottom-nav-height, 56px) + 24px);
}
.page-header h1 {
  margin: 0 0 4px;
  font-size: 1.5rem;
  color: var(--wc-gold, var(--wc-accent-gold));
}
.subtitle {
  margin: 0 0 16px;
  font-size: 0.82rem;
  color: var(--wc-text-muted);
}
.market-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}
.market-toolbar .spacer {
  flex: 1;
}
.market-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 12px;
}
.market-card {
  border-radius: 12px;
  overflow: hidden;
  cursor: pointer;
  transition: transform 0.15s, box-shadow 0.2s;
  border: 1px solid rgba(212, 165, 116, 0.18);
}
.market-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 10px 28px rgba(0, 0, 0, 0.4);
}
.market-card.legend { border-color: rgba(231, 175, 92, 0.5); }
.market-card.epic { border-color: rgba(168, 120, 224, 0.45); }
.card-img {
  position: relative;
  aspect-ratio: 3 / 4;
  background: linear-gradient(160deg, rgba(40, 30, 20, 0.6), rgba(20, 16, 30, 0.9));
  background-size: cover;
  background-position: center;
}
.rarity-badge {
  position: absolute;
  top: 6px;
  left: 6px;
  font-size: 0.62rem;
  padding: 2px 6px;
  border-radius: 6px;
  background: rgba(0, 0, 0, 0.55);
  color: #f0d9b5;
}
.rarity-badge.legend { background: linear-gradient(90deg, #b8860b, #e7af5c); color: #1a1208; }
.rarity-badge.epic { background: rgba(138, 80, 184, 0.85); color: #fff; }
.serial {
  position: absolute;
  top: 6px;
  right: 6px;
  font-size: 0.6rem;
  padding: 2px 6px;
  border-radius: 6px;
  background: rgba(0, 0, 0, 0.6);
  color: #e8c88a;
  font-variant-numeric: tabular-nums;
}
.type-badge {
  position: absolute;
  bottom: 6px;
  right: 6px;
  font-size: 0.6rem;
  padding: 2px 6px;
  border-radius: 6px;
  background: rgba(20, 24, 42, 0.85);
  color: var(--wc-text-secondary);
}
.type-badge.auction { color: #f0b86c; }
.card-body {
  padding: 8px 10px 10px;
}
.card-body .name {
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--wc-text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.card-body .star {
  color: var(--wc-accent-gold);
  font-size: 0.72rem;
}
.price-row {
  display: flex;
  align-items: baseline;
  gap: 4px;
  margin-top: 4px;
}
.price-row .price {
  font-size: 1.05rem;
  font-weight: 800;
  color: var(--wc-accent-gold);
  font-variant-numeric: tabular-nums;
}
.price-row .unit {
  font-size: 0.62rem;
  color: var(--wc-text-muted);
}
.countdown {
  margin-top: 2px;
  font-size: 0.66rem;
  color: #f0b86c;
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
.empty-state span {
  font-size: 0.8rem;
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
}
.empty-btn.secondary {
  background: rgba(255, 255, 255, 0.06);
  color: var(--wc-text-secondary);
}
.balance-chip {
  font-size: 0.72rem;
  color: var(--wc-text-muted);
  white-space: nowrap;
}
.balance-chip b {
  color: var(--wc-accent-gold);
  font-variant-numeric: tabular-nums;
}
.market-card.ending-soon {
  outline: 1px solid rgba(240, 184, 108, 0.45);
  box-shadow: 0 0 12px rgba(240, 184, 108, 0.12);
}
.countdown.urgent {
  color: #ff8a65;
  font-weight: 600;
}
.load-more {
  text-align: center;
  margin-top: 18px;
}
.disclaimer {
  margin-top: 20px;
  font-size: 0.68rem;
  color: var(--wc-text-muted);
  line-height: 1.5;
  text-align: center;
}
.sk-card {
  padding: 12px;
  border-radius: 12px;
  background: rgba(20, 24, 42, 0.4);
}
.detail-body {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.detail-img {
  position: relative;
  aspect-ratio: 16 / 9;
  border-radius: 10px;
  background: linear-gradient(160deg, rgba(40, 30, 20, 0.6), rgba(20, 16, 30, 0.9));
  background-size: cover;
  background-position: center;
}
.detail-meta {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.meta-row {
  display: flex;
  justify-content: space-between;
  font-size: 0.85rem;
}
.meta-row span {
  color: var(--wc-text-muted);
}
.meta-row .gold {
  color: var(--wc-accent-gold);
}
.market-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
}
.market-stats .stat {
  text-align: center;
  padding: 8px 4px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.04);
}
.market-stats .stat span {
  display: block;
  font-size: 0.62rem;
  color: var(--wc-text-muted);
}
.market-stats .stat b {
  font-size: 0.9rem;
  color: var(--wc-text-secondary);
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
  font-size: 0.66rem;
  color: var(--wc-text-muted);
  line-height: 1.4;
  margin: 0;
}
</style>
