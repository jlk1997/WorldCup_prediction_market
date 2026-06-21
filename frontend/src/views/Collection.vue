<template>
  <div class="collection-page page-shell mobile-page">
    <header class="page-header">
      <div class="header-row">
        <div>
          <h1>球星收藏册</h1>
          <p class="subtitle">猜中 · 签到 · 比赛日获得数字藏品</p>
        </div>
        <button
          v-if="passSummary && authState.accessToken"
          type="button"
          class="pass-quick-chip"
          @click="goPassTab"
        >
          <span class="chip-lv">Lv.{{ passSummary.level }}</span>
          <span class="chip-label">手册</span>
          <span v-if="passClaimableCount" class="chip-badge">{{ passClaimableCount }}</span>
        </button>
      </div>
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

    <CollectibleEventBanner
      v-if="passSummary?.events?.length && activeTab !== 'pass'"
      :events="passSummary.events"
      :loading="eventCheerLoading"
      class="page-event-banner"
      @cheer="onEventCheer"
    />

    <el-tabs v-model="activeTab" class="collection-tabs">
      <el-tab-pane label="图鉴" name="album">
        <div class="filters">
          <el-radio-group v-model="rarityFilter" size="small" class="rarity-filter" @change="onFilterChange">
            <el-radio-button value="">全部</el-radio-button>
            <el-radio-button v-for="r in rarities" :key="r" :value="r">
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
          <button
            type="button"
            class="owned-toggle"
            :class="{ active: ownedOnly }"
            :aria-pressed="ownedOnly"
            @click="toggleOwnedOnly"
          >
            <span class="owned-toggle-box" aria-hidden="true">
              <svg v-if="ownedOnly" viewBox="0 0 12 12" class="owned-toggle-check">
                <path d="M2 6.2 L5 9.2 L10 3.2" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
              </svg>
            </span>
            仅已拥有
          </button>
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
            @synthesize="(code, useCoin) => onSynthesize(code, useCoin)"
          />
        </div>
      </el-tab-pane>

      <el-tab-pane name="pass">
        <template #label>
          <span class="pass-tab-label">
            手册
            <el-badge v-if="passClaimableCount" :value="passClaimableCount" class="pass-tab-badge" />
          </span>
        </template>
        <div v-loading="passLoading">
          <p class="pass-compliance">{{ passSummary?.compliance_notice }}</p>
          <div v-if="passSummary" class="pass-xp-tips glass-inner">
            <span class="tips-label">获得经验</span>
            <div class="tips-chips">
              <span>竞猜 +10/猜中 +25</span>
              <span>签到 +15</span>
              <span>助威 +5</span>
              <span>任务 +50</span>
            </div>
          </div>
          <CollectibleEventBanner
            :events="passSummary?.events"
            :loading="eventCheerLoading"
            @cheer="onEventCheer"
          />
          <CollectionPassTrack
            v-if="passSummary"
            :summary="passSummary"
            :claiming="passClaiming"
            :claiming-all="passClaimAllLoading"
            @claim="onPassClaim"
            @claim-all="onPassClaimAll"
            @buy-premium="goBuyPass"
            @buy-premium-plus="goBuyPassPlus"
            @buy-xp-boost="onXpBoost"
          />
          <CollectionQuestList
            v-if="passSummary"
            :daily="passSummary.quests.daily"
            :weekly="passSummary.quests.weekly"
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

    <CollectionPassStickyBar
      :claimable-count="passClaimableCount"
      :level="passSummary?.level"
      :active-tab="activeTab"
      @open-pass="goPassTab"
    />

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
            v-if="selectedCard.can_upgrade !== false"
            type="primary"
            :loading="upgradeLoading"
            @click="onUpgrade(false)"
          >
            升星至 ★{{ (selectedCard.star ?? 1) + 1 }}
            <span v-if="selectedCard.upgrade_cost" class="upgrade-cost">
              （{{ selectedCard.upgrade_cost.shards }}碎片 · {{ selectedCard.upgrade_cost.redeem_points }}分）
            </span>
          </el-button>
          <el-button
            v-else
            type="warning"
            plain
            :loading="upgradeLoading"
            @click="onUpgrade(true)"
          >
            球迷币补碎片升星
          </el-button>
        </div>
        <el-button plain @click="shareSelectedCard">分享卡牌</el-button>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import AlbumGrid from '@/components/collectible/AlbumGrid.vue'
import CardItem from '@/components/collectible/CardItem.vue'
import SetProgressCard from '@/components/collectible/SetProgressCard.vue'
import SynthesizePanel from '@/components/collectible/SynthesizePanel.vue'
import CollectionPassStickyBar from '@/components/collectible/CollectionPassStickyBar.vue'
import CollectionPassTrack from '@/components/collectible/CollectionPassTrack.vue'
import CollectionQuestList from '@/components/collectible/CollectionQuestList.vue'
import CollectibleEventBanner from '@/components/collectible/CollectibleEventBanner.vue'
import {
  buyPassXpBoost,
  claimAllPassRewards,
  claimPassReward,
  eventCheerDrop,
  getCollectionPassSummary,
  getCollectionPassSummaryLite,
  type CollectionPassSummary,
} from '@/api/collectionPass'
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
import { buildSynthesisDrop, openCollectibleReveal } from '@/stores/collectibleRevealStore'
import { openCollectibleShare } from '@/composables/useCollectibleShareSheet'
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
const router = useRouter()
const route = useRoute()
const activeTab = ref('album')
const rarityFilter = ref('')
const seriesFilter = ref('')
const ownedOnly = ref(false)
const activity = ref<CollectibleActivityItem[]>([])
const detailOpen = ref(false)
const selectedCard = ref<CollectibleCardBrief | null>(null)
const claimingSet = ref<string | null>(null)
const synthLoading = ref<string | null>(null)
const upgradeLoading = ref(false)
const retryLoading = ref(false)
const passLoading = ref(false)
const passSummary = ref<CollectionPassSummary | null>(null)
const passClaimableCount = computed(() => passSummary.value?.claimable_count ?? 0)

async function ensurePassSummary(force = false, needFull = false) {
  const wantFull = needFull || activeTab.value === 'pass'
  if (!force && passSummary.value) {
    if (!wantFull || (passSummary.value.tracks?.length ?? 0) > 0) {
      return passSummary.value
    }
  }
  passLoading.value = wantFull && activeTab.value === 'pass'
  try {
    if (wantFull) {
      passSummary.value = await getCollectionPassSummary(force)
      loadedTabs.add('pass')
    } else {
      const lite = await getCollectionPassSummaryLite(force)
      passSummary.value = {
        ...lite,
        tracks: passSummary.value?.tracks?.length ? passSummary.value.tracks : [],
      }
    }
    return passSummary.value
  } catch (e: unknown) {
    if (activeTab.value === 'pass') {
      ElMessage.error((e as Error)?.message || '手册加载失败')
    }
    return null
  } finally {
    passLoading.value = false
  }
}

function patchPassClaimLocal(level: number, track: 'free' | 'premium') {
  if (!passSummary.value) return
  const row = passSummary.value.tracks.find((t) => t.level === level)
  if (row) {
    if (track === 'free') {
      row.free_claimed = true
      row.free_claimable = false
    } else {
      row.premium_claimed = true
      row.premium_claimable = false
    }
  }
  if (track === 'free') {
    if (!passSummary.value.claimed_free_levels.includes(level)) {
      passSummary.value.claimed_free_levels.push(level)
    }
  } else if (!passSummary.value.claimed_premium_levels.includes(level)) {
    passSummary.value.claimed_premium_levels.push(level)
  }
  passSummary.value.claimable_count = Math.max(0, (passSummary.value.claimable_count ?? 1) - 1)
}
const passClaiming = ref<string | null>(null)
const passClaimAllLoading = ref(false)
const eventCheerLoading = ref(false)

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

function toggleOwnedOnly() {
  ownedOnly.value = !ownedOnly.value
  onFilterChange()
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

async function refreshAfterMutation(reloadPass = false) {
  loadedTabs.delete('sets')
  loadedTabs.delete('synth')
  loadedTabs.delete('activity')
  await loadAlbum(true)
  if (activeTab.value === 'sets') await loadSetsTab()
  if (activeTab.value === 'synth') await loadSynthTab()
  if (activeTab.value === 'activity') await loadActivityTab()
  if (reloadPass || activeTab.value === 'pass') {
    await ensurePassSummary(true)
  }
  chainStatus.value = await getCollectibleChainStatus().catch(() => null)
}

watch(activeTab, (tab) => {
  if (tab === 'sets') void loadSetsTab()
  if (tab === 'synth') void loadSynthTab()
  if (tab === 'activity') void loadActivityTab()
  if (tab === 'pass') void loadPassTab()
})

async function loadPassTab() {
  if (loadedTabs.has('pass') && (passSummary.value?.tracks?.length ?? 0) > 0) {
    await maybeClaimAllFromQuery()
    return
  }
  await ensurePassSummary(false, true)
  await maybeClaimAllFromQuery()
}

async function maybeClaimAllFromQuery() {
  if (route.query.claim !== 'all') return
  if (!passSummary.value?.claimable_count) {
    router.replace({ path: '/collection', query: { tab: 'pass' } })
    return
  }
  router.replace({ path: '/collection', query: { tab: 'pass' } })
  if (!passClaimAllLoading.value) await onPassClaimAll()
}

async function onPassClaimAll() {
  passClaimAllLoading.value = true
  try {
    const res = await claimAllPassRewards()
    if (!res.claimed_count) {
      ElMessage.info('暂无可领取奖励')
      return
    }
    let cardShown = false
    let coinTotal = 0
    let pointTotal = 0
    for (const item of res.claims) {
      const g = item.grants as Record<string, unknown>
      if (typeof g.fan_coins === 'number') coinTotal += g.fan_coins
      if (typeof g.redeem_points === 'number') pointTotal += g.redeem_points
      const drop = g.collectible_drop as { dropped?: boolean; cards?: unknown[] } | undefined
      if (!cardShown && drop?.dropped && drop.cards?.length) {
        openCollectibleReveal(drop as import('@/api/collectible').CollectibleDropResult, {
          subtitle: item.track === 'premium' ? '手册尊享奖励' : '手册免费奖励',
        })
        cardShown = true
      }
    }
    const parts: string[] = [`已领取 ${res.claimed_count} 项`]
    if (coinTotal) parts.push(`+${coinTotal} 球迷币`)
    if (pointTotal) parts.push(`+${pointTotal} 可用积分`)
    if (!cardShown) ElMessage.success(parts.join(' · '))
    await fetchMe()
    await ensurePassSummary(true, true)
  } catch (e: unknown) {
    ElMessage.error((e as Error)?.message || '一键领取失败')
  } finally {
    passClaimAllLoading.value = false
    passClaiming.value = null
  }
}

async function onPassClaim(level: number, track: 'free' | 'premium') {
  passClaiming.value = `${level}-${track}`
  try {
    const res = await claimPassReward(level, track)
    const drop = res.grants?.collectible_drop as { dropped?: boolean; cards?: unknown[] } | undefined
    if (drop?.dropped && drop.cards?.length) {
      openCollectibleReveal(drop as import('@/api/collectible').CollectibleDropResult, {
        subtitle: track === 'premium' ? '手册尊享奖励' : '手册免费奖励',
      })
    } else {
      const parts: string[] = []
      const g = res.grants as Record<string, unknown>
      if (g.fan_coins) parts.push(`+${g.fan_coins} 球迷币`)
      if (g.redeem_points) parts.push(`+${g.redeem_points} 可用积分`)
      if (g.badge) parts.push('徽章已发放')
      ElMessage.success(parts.length ? `已领取 · ${parts.join(' · ')}` : '奖励已领取')
    }
    patchPassClaimLocal(level, track)
    await fetchMe()
    void ensurePassSummary(true)
  } catch (e: unknown) {
    ElMessage.error((e as Error)?.message || '领取失败')
  } finally {
    passClaiming.value = null
  }
}

function goPassTab() {
  activeTab.value = 'pass'
  void loadPassTab()
}

function goBuyPass() {
  router.push('/shop?highlight=collection_pass')
}

function goBuyPassPlus() {
  router.push('/shop?highlight=collection_pass_plus')
}

async function onXpBoost() {
  try {
    await ElMessageBox.confirm(
      '消耗 30 球迷币激活 24 小时手册经验 +50%？',
      '经验加成',
      { confirmButtonText: '确认购买', cancelButtonText: '取消', type: 'info' },
    )
    await buyPassXpBoost()
    ElMessage.success('经验加成已激活（24h · XP +50%）')
    await ensurePassSummary(true)
  } catch (e: unknown) {
    if (e === 'cancel' || (e as { message?: string })?.message === 'cancel') return
    ElMessage.error((e as Error)?.message || '购买失败')
  }
}

async function onEventCheer(teamId: number) {
  eventCheerLoading.value = true
  try {
    const res = await eventCheerDrop(teamId)
    if (res.collectible_drop?.dropped) {
      openCollectibleReveal(res.collectible_drop, { subtitle: '活动应援掉落' })
    } else {
      ElMessage.info('本次未掉落，继续加油')
    }
    await fetchMe()
    await ensurePassSummary(true)
  } catch (e: unknown) {
    ElMessage.error((e as Error)?.message || '活动应援失败')
  } finally {
    eventCheerLoading.value = false
  }
}

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
      const repCode = setInfo.owned_codes?.[0] || setInfo.card_codes[0]
      const repCard = album.value?.cards.find((c) => c.code === repCode) || {
        code: repCode,
        name: setInfo.name,
        rarity: 'rare' as const,
        series: 'set',
        image_url: null,
        attributes: {},
        player_id: null,
        team_id: null,
        owned: true,
      }
      openCollectibleShare({
        card: repCard,
        variant: 'set_complete',
        setName: setInfo.name,
        subtitleOverride: `集齐 ${setInfo.total_count} 张 · 套组成就`,
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

async function onSynthesize(code: string, useCoinFill = false) {
  if (useCoinFill) {
    try {
      await ElMessageBox.confirm(
        '将使用球迷币按上限补足缺口碎片（确定性消耗，非随机抽卡）。确认继续？',
        '球迷币补碎片',
        { confirmButtonText: '确认合成', cancelButtonText: '取消', type: 'warning' },
      )
    } catch {
      return
    }
  }
  synthLoading.value = code
  try {
    const result = await synthesizeCard(code, useCoinFill) as { card: CollectibleCardBrief; coins_spent?: number }
    await fetchMe()
    await refreshAfterMutation()
    openCollectibleReveal(buildSynthesisDrop(result.card), { subtitle: '碎片合成' })
  } catch (e: unknown) {
    ElMessage.error((e as Error)?.message || '合成失败')
  } finally {
    synthLoading.value = null
  }
}

async function onUpgrade(useCoinFill = false) {
  if (!selectedCard.value?.code) return
  if (useCoinFill) {
    try {
      await ElMessageBox.confirm(
        '将使用球迷币按上限补足缺口碎片（确定性消耗）。确认升星？',
        '球迷币补碎片升星',
        { confirmButtonText: '确认升星', cancelButtonText: '取消', type: 'warning' },
      )
    } catch {
      return
    }
  }
  upgradeLoading.value = true
  try {
    const result = await upgradeCollectibleCard(selectedCard.value.code, useCoinFill)
    selectedCard.value = result.card
    const coinNote = result.coins_spent ? ` · 消耗 ${result.coins_spent} 球迷币补碎片` : ''
    ElMessage.success(`升星成功 · ★${result.new_star}${coinNote}`)
    await fetchMe()
    await refreshAfterMutation()
  } catch (e: unknown) {
    ElMessage.error((e as Error)?.message || '升星失败')
  } finally {
    upgradeLoading.value = false
  }
}

function shareSelectedCard() {
  const card = selectedCard.value
  if (!card) return
  openCollectibleShare({ card })
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
  const tab = route.query.tab
  if (typeof tab === 'string' && ['album', 'sets', 'synth', 'activity', 'pass'].includes(tab)) {
    activeTab.value = tab
  }
  await loadAlbum(true)
  if (activeTab.value === 'pass') {
    await ensurePassSummary(false, true)
    await maybeClaimAllFromQuery()
  } else {
    void ensurePassSummary(false, false)
  }
  getCollectibleChainStatus().then((s) => { chainStatus.value = s }).catch(() => {})
})
</script>

<style scoped>
.pass-compliance {
  font-size: 0.72rem;
  color: var(--wc-text-muted);
  line-height: 1.45;
  margin: 0 0 10px;
}
.pass-xp-tips {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 12px;
  padding: 10px 12px;
  margin-bottom: 12px;
  border-radius: 10px;
}
.tips-label {
  font-size: 0.72rem;
  font-weight: 600;
  color: var(--wc-gold);
  flex-shrink: 0;
}
.tips-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.tips-chips span {
  font-size: 0.68rem;
  padding: 3px 8px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.06);
  color: var(--wc-text-muted);
}
.page-event-banner {
  margin-bottom: 12px;
}
.pass-tab-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.pass-tab-badge :deep(.el-badge__content) {
  transform: none;
  position: static;
}
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
.header-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}
.pass-quick-chip {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border-radius: 999px;
  border: 1px solid rgba(212, 165, 116, 0.35);
  background: rgba(212, 165, 116, 0.1);
  color: var(--wc-gold);
  font-size: 0.82rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s, border-color 0.2s;
}
.pass-quick-chip:hover {
  background: rgba(212, 165, 116, 0.18);
  border-color: rgba(212, 165, 116, 0.55);
}
.pass-quick-chip :deep(.el-badge__content) {
  transform: none;
  position: static;
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
  gap: 10px 12px;
  margin-bottom: 16px;
}

.rarity-filter :deep(.el-radio-button__inner) {
  border-color: rgba(212, 165, 116, 0.25) !important;
  background: rgba(255, 255, 255, 0.04);
  color: rgba(255, 255, 255, 0.72);
  box-shadow: none !important;
}

.rarity-filter :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background: rgba(212, 165, 116, 0.22) !important;
  border-color: rgba(212, 165, 116, 0.55) !important;
  color: var(--wc-gold) !important;
}

.owned-toggle {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px 6px 8px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.14);
  background: rgba(255, 255, 255, 0.05);
  color: rgba(255, 255, 255, 0.68);
  font-size: 0.78rem;
  font-weight: 600;
  cursor: pointer;
  transition: border-color 0.2s, background 0.2s, color 0.2s, box-shadow 0.2s;
  min-height: 32px;
}

.owned-toggle:hover {
  border-color: rgba(212, 165, 116, 0.4);
  color: rgba(255, 255, 255, 0.88);
}

.owned-toggle.active {
  border-color: rgba(212, 165, 116, 0.55);
  background: rgba(212, 165, 116, 0.16);
  color: var(--wc-gold);
  box-shadow: 0 0 0 1px rgba(212, 165, 116, 0.15);
}

.owned-toggle-box {
  width: 18px;
  height: 18px;
  border-radius: 5px;
  border: 1.5px solid rgba(255, 255, 255, 0.28);
  background: rgba(8, 10, 18, 0.55);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: border-color 0.2s, background 0.2s;
}

.owned-toggle.active .owned-toggle-box {
  border-color: var(--wc-gold);
  background: rgba(212, 165, 116, 0.35);
}

.owned-toggle-check {
  width: 12px;
  height: 12px;
  color: #fff7e8;
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
