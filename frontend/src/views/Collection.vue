<template>
  <div class="collection-page page-shell mobile-page">
    <header class="page-header">
      <h1>球星收藏册</h1>
      <p class="subtitle">猜中 · 签到 · 比赛日获得数字藏品</p>
    </header>

    <div v-if="album" class="stats-bar glass-panel">
      <div class="stat">
        <strong>{{ album.owned_count }}/{{ album.total }}</strong>
        <span>已收集</span>
      </div>
      <div class="stat">
        <strong>{{ album.completion_pct }}%</strong>
        <span>完成度</span>
      </div>
      <div class="stat">
        <strong>{{ album.redeem_points }}</strong>
        <span>可用积分</span>
      </div>
    </div>

    <p class="compliance">{{ album?.compliance_notice }}</p>
    <p v-if="chainStatus?.enabled" class="chain-line">
      {{ chainStatus.chain_name }}数字藏品
      <span v-if="chainStatus.pending_mints"> · {{ chainStatus.pending_mints }} 张上链中</span>
      <span v-if="chainStatus.minted_count"> · 已铸造 {{ chainStatus.minted_count }} 张</span>
    </p>

    <el-tabs v-model="activeTab" class="collection-tabs">
      <el-tab-pane label="图鉴" name="album">
        <div class="filters">
          <el-radio-group v-model="rarityFilter" size="small" @change="onFilterChange">
            <el-radio-button label="">全部</el-radio-button>
            <el-radio-button v-for="r in rarities" :key="r" :label="r">
              {{ RARITY_LABELS[r] }}
            </el-radio-button>
          </el-radio-group>
          <el-select
            v-if="album?.series_options?.length"
            v-model="seriesFilter"
            size="small"
            clearable
            placeholder="系列"
            class="series-select"
            @change="onFilterChange"
          >
            <el-option
              v-for="s in album.series_options"
              :key="s.value"
              :label="s.label"
              :value="s.value"
            />
          </el-select>
          <el-checkbox v-model="ownedOnly" size="small" @change="onFilterChange">仅已拥有</el-checkbox>
        </div>
        <div v-loading="albumLoading" class="album-wrap">
          <AlbumGrid
            v-if="album"
            :cards="album.cards"
            :has-more="albumHasMore"
            :loading-more="albumLoadingMore"
            @select="openCardDetail"
            @load-more="loadMoreAlbum"
          />
        </div>
      </el-tab-pane>

      <el-tab-pane label="套组" name="sets">
        <div v-loading="setsLoading" class="sets-list">
          <SetProgressCard
            v-for="s in sets"
            :key="s.code"
            :set="s"
            :claiming="claimingSet === s.code"
            @claim="onClaimSet"
          />
        </div>
      </el-tab-pane>

      <el-tab-pane label="合成" name="synth">
        <div v-loading="synthLoadingTab">
          <SynthesizePanel
            :options="synthOptions"
            :shards="album?.shards ?? {}"
            :redeem-points="album?.redeem_points ?? 0"
            :loading-code="synthLoading"
            @synthesize="onSynthesize"
          />
        </div>
      </el-tab-pane>

      <el-tab-pane label="动态" name="activity">
        <div v-loading="activityLoading">
          <div v-if="!activity.length" class="activity-empty">暂无获得记录，去猜一场或签到吧</div>
          <div v-else class="activity-list">
            <div v-for="(item, idx) in activity" :key="idx" class="activity-row glass-inner">
              <span class="activity-source">{{ sourceLabel(item.source) }}</span>
              <span class="activity-cards">
                {{ item.cards.map((c) => c.name).join('、') }}
              </span>
              <span v-if="item.at" class="activity-at">{{ formatAt(item.at) }}</span>
            </div>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>

    <el-drawer v-model="detailOpen" :title="selectedCard?.name" size="88%" direction="btt">
      <div v-if="selectedCard" class="card-detail">
        <CardItem :card="selectedCard" />
        <div class="detail-meta">
          <p><strong>稀有度</strong> {{ RARITY_LABELS[selectedCard.rarity] }}</p>
          <p v-if="selectedCard.attributes?.overall_rating">
            <strong>评分</strong> {{ selectedCard.attributes.overall_rating }}
          </p>
          <p v-if="selectedCard.attributes?.position">
            <strong>位置</strong> {{ selectedCard.attributes.position }}
          </p>
          <p v-if="(selectedCard.star ?? 0) > 0"><strong>星级</strong> ★{{ selectedCard.star }}</p>
          <div v-if="selectedCard.highlights?.length" class="highlights">
            <strong>高光印记</strong>
            <ul>
              <li v-for="(h, i) in selectedCard.highlights" :key="i">
                {{ h.team1 }} vs {{ h.team2 }} · {{ h.score }}
              </li>
            </ul>
          </div>
          <div v-if="selectedCard.chain" class="chain-cert glass-inner">
            <strong>文昌链凭证</strong>
            <p>状态：{{ chainStatusLabel(selectedCard.chain.status) }}</p>
            <p v-if="selectedCard.chain.nft_id">NFT ID：{{ selectedCard.chain.nft_id }}</p>
            <p v-if="selectedCard.chain.tx_hash">Tx：{{ shortHash(selectedCard.chain.tx_hash) }}</p>
            <p v-if="selectedCard.chain.error" class="chain-error">{{ selectedCard.chain.error }}</p>
            <el-button
              v-if="selectedCard.chain.status === 'failed' && selectedCard.user_card_id"
              size="small"
              type="warning"
              :loading="retryLoading"
              @click="onRetryMint"
            >
              重新排队铸造
            </el-button>
            <p class="chain-note">由 AVATA 平台托管，不可转赠交易</p>
          </div>
        </div>
        <div v-if="selectedCard.owned && (selectedCard.star ?? 0) < 3" class="detail-actions">
          <el-button
            type="primary"
            :loading="upgradeLoading"
            :disabled="selectedCard.can_upgrade === false"
            @click="onUpgrade"
          >
            升星至 ★{{ (selectedCard.star ?? 1) + 1 }}
            <span v-if="selectedCard.upgrade_cost" class="upgrade-cost">
              （{{ selectedCard.upgrade_cost.shards }}碎片 · {{ selectedCard.upgrade_cost.redeem_points }}分）
            </span>
          </el-button>
        </div>
        <el-button plain @click="shareSelectedCard">分享卡牌</el-button>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import AlbumGrid from '@/components/collectible/AlbumGrid.vue'
import CardItem from '@/components/collectible/CardItem.vue'
import SetProgressCard from '@/components/collectible/SetProgressCard.vue'
import SynthesizePanel from '@/components/collectible/SynthesizePanel.vue'
import {
  claimCollectibleSet,
  getCollectibleActivity,
  getCollectibleAlbum,
  getCollectibleCard,
  getCollectibleChainStatus,
  getCollectibleSets,
  getSynthesisOptions,
  retryCollectibleChainMint,
  synthesizeCard,
  upgradeCollectibleCard,
  type CardRarity,
  type CollectibleAlbum,
  type CollectibleCardBrief,
  type CardSetProgress,
  type SynthesisOption,
  type CollectibleChainStatus,
  type CollectibleActivityItem,
  RARITY_LABELS,
  SOURCE_LABELS,
} from '@/api/collectible'
import { fetchMe } from '@/stores/authStore'
import { downloadSharePoster } from '@/utils/sharePoster'
import { authState } from '@/stores/authStore'
import { usePageMeta } from '@/composables/usePageMeta'

usePageMeta({
  title: '球星收藏册 — 最后一舞',
  description: '猜中掉落球星卡，收集套组赢奖励。数字藏品无金钱价值，不可交易。',
  path: '/collection',
  noIndex: true,
})

const albumLoading = ref(false)
const albumLoadingMore = ref(false)
const setsLoading = ref(false)
const synthLoadingTab = ref(false)
const activityLoading = ref(false)
const album = ref<CollectibleAlbum | null>(null)
const albumPage = ref(1)
const albumHasMore = ref(false)
const chainStatus = ref<CollectibleChainStatus | null>(null)
const sets = ref<CardSetProgress[]>([])
const synthOptions = ref<SynthesisOption[]>([])
const activeTab = ref('album')
const rarityFilter = ref('')
const seriesFilter = ref('')
const ownedOnly = ref(true)
const activity = ref<CollectibleActivityItem[]>([])
const detailOpen = ref(false)
const selectedCard = ref<CollectibleCardBrief | null>(null)
const claimingSet = ref<string | null>(null)
const synthLoading = ref<string | null>(null)
const upgradeLoading = ref(false)
const retryLoading = ref(false)

const loadedTabs = new Set<string>()
let filterDebounce: ReturnType<typeof setTimeout> | null = null

const rarities: CardRarity[] = ['common', 'rare', 'epic', 'legend']

function albumParams(page = 1) {
  return {
    rarity: rarityFilter.value || undefined,
    series: seriesFilter.value || undefined,
    ownedOnly: ownedOnly.value,
    page,
    limit: 60,
    brief: true,
  }
}

async function loadAlbum(reset = true) {
  if (reset) {
    albumLoading.value = true
    albumPage.value = 1
  } else {
    albumLoadingMore.value = true
  }
  try {
    const page = reset ? 1 : albumPage.value + 1
    const data = await getCollectibleAlbum(albumParams(page))
    if (reset || !album.value) {
      album.value = data
    } else {
      album.value = {
        ...data,
        cards: [...album.value.cards, ...data.cards],
      }
    }
    albumPage.value = page
    albumHasMore.value = data.has_more ?? false
  } catch (e: unknown) {
    ElMessage.error((e as Error)?.message || '加载图鉴失败')
  } finally {
    albumLoading.value = false
    albumLoadingMore.value = false
  }
}

function loadMoreAlbum() {
  if (albumLoading.value || albumLoadingMore.value || !albumHasMore.value) return
  void loadAlbum(false)
}

function onFilterChange() {
  if (filterDebounce) clearTimeout(filterDebounce)
  filterDebounce = setTimeout(() => void loadAlbum(true), 300)
}

async function loadSetsTab() {
  if (loadedTabs.has('sets')) return
  setsLoading.value = true
  try {
    sets.value = await getCollectibleSets()
    loadedTabs.add('sets')
  } catch (e: unknown) {
    ElMessage.error((e as Error)?.message || '加载套组失败')
  } finally {
    setsLoading.value = false
  }
}

async function loadSynthTab() {
  if (loadedTabs.has('synth')) return
  synthLoadingTab.value = true
  try {
    if (!album.value) await loadAlbum(true)
    synthOptions.value = await getSynthesisOptions()
    loadedTabs.add('synth')
  } catch (e: unknown) {
    ElMessage.error((e as Error)?.message || '加载合成选项失败')
  } finally {
    synthLoadingTab.value = false
  }
}

async function loadActivityTab() {
  if (loadedTabs.has('activity')) return
  activityLoading.value = true
  try {
    activity.value = await getCollectibleActivity()
    loadedTabs.add('activity')
  } catch {
    activity.value = []
    loadedTabs.add('activity')
  } finally {
    activityLoading.value = false
  }
}

async function refreshAfterMutation() {
  loadedTabs.delete('sets')
  loadedTabs.delete('synth')
  loadedTabs.delete('activity')
  await loadAlbum(true)
  if (activeTab.value === 'sets') await loadSetsTab()
  if (activeTab.value === 'synth') await loadSynthTab()
  if (activeTab.value === 'activity') await loadActivityTab()
  chainStatus.value = await getCollectibleChainStatus().catch(() => null)
}

watch(activeTab, (tab) => {
  if (tab === 'sets') void loadSetsTab()
  if (tab === 'synth') void loadSynthTab()
  if (tab === 'activity') void loadActivityTab()
})

async function openCardDetail(card: CollectibleCardBrief) {
  try {
    selectedCard.value = await getCollectibleCard(card.code)
    detailOpen.value = true
  } catch {
    selectedCard.value = card
    detailOpen.value = true
  }
}

async function onClaimSet(code: string) {
  const setInfo = sets.value.find((s) => s.code === code)
  claimingSet.value = code
  try {
    await claimCollectibleSet(code)
    ElMessage.success('套组奖励已领取')
    if (setInfo) {
      await downloadSharePoster({
        variant: 'set_complete',
        displayName: authState.user?.nickname,
        title: `集齐「${setInfo.name}」`,
        subtitle: '最后一舞 · 球星收藏册成就',
        statsLine: `${setInfo.total_count}/${setInfo.total_count} 张 · 虚拟数字藏品`,
        badge: '套组成就',
      })
    }
    await fetchMe()
    await refreshAfterMutation()
  } catch (e: unknown) {
    ElMessage.error((e as Error)?.message || '领取失败')
  } finally {
    claimingSet.value = null
  }
}

async function onSynthesize(code: string) {
  synthLoading.value = code
  try {
    await synthesizeCard(code)
    ElMessage.success('合成成功')
    await fetchMe()
    await refreshAfterMutation()
  } catch (e: unknown) {
    ElMessage.error((e as Error)?.message || '合成失败')
  } finally {
    synthLoading.value = null
  }
}

async function onUpgrade() {
  if (!selectedCard.value?.code) return
  upgradeLoading.value = true
  try {
    const result = await upgradeCollectibleCard(selectedCard.value.code)
    selectedCard.value = result.card
    ElMessage.success(`升星成功 · ★${result.new_star}`)
    await fetchMe()
    await refreshAfterMutation()
  } catch (e: unknown) {
    ElMessage.error((e as Error)?.message || '升星失败')
  } finally {
    upgradeLoading.value = false
  }
}

async function shareSelectedCard() {
  const card = selectedCard.value
  if (!card) return
  await downloadSharePoster({
    variant: 'card',
    displayName: authState.user?.nickname,
    title: `我的 ${card.name}`,
    subtitle: `${RARITY_LABELS[card.rarity]} · 最后一舞收藏册`,
    statsLine: `★${card.star ?? 1} · 虚拟数字藏品`,
    badge: '收藏册',
  })
}

function chainStatusLabel(status: string) {
  const map: Record<string, string> = {
    none: '未上链',
    pending: '排队中',
    minting: '铸造中',
    minted: '已铸造',
    failed: '失败',
  }
  return map[status] || status
}

function shortHash(hash: string) {
  if (hash.length <= 16) return hash
  return `${hash.slice(0, 8)}…${hash.slice(-6)}`
}

function sourceLabel(source: string) {
  return SOURCE_LABELS[source] || source
}

function formatAt(iso: string) {
  try {
    return new Date(iso).toLocaleString('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' })
  } catch {
    return iso
  }
}

async function onRetryMint() {
  const id = selectedCard.value?.user_card_id
  if (!id) return
  retryLoading.value = true
  try {
    const chain = await retryCollectibleChainMint(id)
    if (selectedCard.value) selectedCard.value.chain = chain
    ElMessage.success('已重新排队铸造')
    chainStatus.value = await getCollectibleChainStatus().catch(() => null)
  } catch (e: unknown) {
    ElMessage.error((e as Error)?.message || '重试失败')
  } finally {
    retryLoading.value = false
  }
}

onMounted(async () => {
  await loadAlbum(true)
  getCollectibleChainStatus().then((s) => { chainStatus.value = s }).catch(() => {})
})
</script>

<style scoped>
.collection-page {
  max-width: 960px;
  margin: 0 auto;
  padding-bottom: calc(var(--wc-bottom-nav-height, 56px) + 24px);
}
.page-header h1 {
  margin: 0 0 4px;
  font-size: 1.5rem;
  color: var(--wc-gold);
}
.subtitle {
  margin: 0 0 16px;
  color: var(--wc-text-muted);
  font-size: 0.85rem;
}
.stats-bar {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  padding: 12px;
  margin-bottom: 12px;
  border-radius: 12px;
}
.stat {
  text-align: center;
}
.stat strong {
  display: block;
  font-size: 1.1rem;
  color: var(--wc-gold);
}
.stat span {
  font-size: 0.72rem;
  color: var(--wc-text-muted);
}
.compliance {
  font-size: 0.68rem;
  color: var(--wc-text-muted);
  line-height: 1.4;
  margin-bottom: 8px;
}
.chain-line {
  font-size: 0.72rem;
  color: #3dd68c;
  margin-bottom: 12px;
}
.chain-cert {
  margin-top: 12px;
  padding: 10px 12px;
  border-radius: 10px;
  font-size: 0.78rem;
}
.chain-cert p {
  margin: 4px 0;
  color: var(--wc-text-muted);
}
.chain-note {
  font-size: 0.65rem !important;
}
.album-wrap {
  min-height: 200px;
}
.filters {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
}
.series-select {
  width: 110px;
}
.activity-empty {
  font-size: 0.85rem;
  color: var(--wc-text-muted);
  padding: 24px 0;
  text-align: center;
}
.activity-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.activity-row {
  padding: 10px 12px;
  border-radius: 10px;
  font-size: 0.78rem;
}
.activity-source {
  color: var(--wc-gold);
  margin-right: 8px;
}
.activity-at {
  display: block;
  margin-top: 4px;
  color: var(--wc-text-muted);
  font-size: 0.68rem;
}
.chain-error {
  color: #f56c6c !important;
}
.upgrade-cost {
  font-size: 0.72rem;
  opacity: 0.85;
}
.sets-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.card-detail {
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-width: 280px;
  margin: 0 auto;
}
.detail-meta p {
  margin: 4px 0;
  font-size: 0.85rem;
}
.highlights ul {
  margin: 6px 0 0;
  padding-left: 18px;
  font-size: 0.78rem;
  color: var(--wc-text-muted);
}
.detail-actions {
  display: flex;
  gap: 8px;
}
</style>
