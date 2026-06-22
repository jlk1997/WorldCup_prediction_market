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

    <AssetHubBar compact :show-balance="!!authState.accessToken" />

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
      :cheer-status="passSummary.event_cheer_status"
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
            :cheer-status="passSummary?.event_cheer_status"
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

    <el-drawer v-model="detailOpen" :title="selectedCard?.name" size="88%" direction="btt" append-to-body>
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
          <div v-if="selectedCard.owned && selectedCard.asset" class="asset-panel glass-inner">
            <div class="asset-row">
              <span>序列号</span>
              <strong v-if="selectedCard.asset.serial_no">
                #{{ selectedCard.asset.serial_no }}<template v-if="selectedCard.asset.mint_total">/{{ selectedCard.asset.mint_total }}</template>
              </strong>
              <strong v-else>—</strong>
            </div>
            <div class="asset-row">
              <span>估值</span>
              <strong class="gold">{{ selectedCard.asset.estimated_value }} 可用积分</strong>
            </div>
            <div class="asset-row">
              <span>官方回购价</span>
              <strong>{{ selectedCard.asset.buyback_quote }} 可用积分</strong>
            </div>
            <div v-if="selectedCard.asset.cooling_down" class="asset-cooling">
              新获卡牌冷却中，冷却期后可流通
            </div>
            <div v-else-if="isStacked(selectedCard)" class="asset-cooling stack-hint">
              <p>叠卡 ×{{ stackCount(selectedCard) }}，暂不可整堆流通</p>
              <el-button
                v-if="maxSplitAmount(selectedCard) > 0"
                size="small"
                type="primary"
                plain
                :loading="assetActing"
                @click="openSplitDialog"
              >
                拆分 {{ maxSplitAmount(selectedCard) }} 张可流通
              </el-button>
              <span v-else class="stack-tip">或合成升星消耗叠卡</span>
            </div>
            <div v-else-if="selectedCard.asset.lock_state !== 'none'" class="asset-cooling">
              当前{{ lockStateLabel(selectedCard.asset.lock_state) }}
            </div>
            <p class="asset-note">资产以可用积分计价，为站内虚拟权益，无现金价值、不可提现。</p>
          </div>
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
            <p class="chain-note">由 AVATA 平台托管，经合规校验后可转赠/交易行流通</p>
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
        <div
          v-if="selectedCard.owned && selectedCard.asset && canCirculate(selectedCard)"
          class="asset-actions"
        >
          <el-button size="small" type="primary" plain @click="openListDialog">挂牌出售</el-button>
          <el-button size="small" plain @click="openGiftDialog">转赠</el-button>
          <el-button size="small" plain @click="onStake">质押</el-button>
          <el-button size="small" plain @click="onBuyback">官方回购</el-button>
        </div>
        <el-button plain @click="shareSelectedCard">分享卡牌</el-button>
      </div>
    </el-drawer>

    <el-dialog v-model="listDialog" title="挂牌出售" width="min(400px, 94vw)" align-center append-to-body class="wc-dialog">
      <div v-if="listHint" class="list-hint glass-inner">
        <div class="lh-row">
          <span>建议价</span>
          <strong class="gold">{{ listHint.suggested_price }} 积分</strong>
          <el-button size="small" text type="primary" @click="applySuggestedPrice">采用</el-button>
        </div>
        <div class="lh-meta">
          <span v-if="listHint.floor_price">地板 {{ listHint.floor_price }}</span>
          <span v-if="listHint.last_trade_price">最近 {{ listHint.last_trade_price }}</span>
          <span>估值 {{ listHint.estimated_value }}</span>
          <span>回购 {{ listHint.buyback_floor }}</span>
        </div>
        <p class="lh-net">成交后约到手 {{ listHint.net_after_fee }} 积分（手续费 {{ listHint.fee_pct }}%）</p>
      </div>
      <el-form label-position="top">
        <el-form-item label="挂牌类型">
          <el-radio-group v-model="listForm.type">
            <el-radio-button label="fixed">一口价</el-radio-button>
            <el-radio-button label="auction">竞拍</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item :label="listForm.type === 'auction' ? '起拍价（可用积分）' : '价格（可用积分）'">
          <el-input-number
            v-model="listForm.price"
            :min="listHint?.price_range.min ?? 10"
            :max="listHint?.price_range.max ?? 1000000"
            :step="10"
          />
        </el-form-item>
      </el-form>
      <p class="dialog-note">{{ listHint?.disclaimer || '资产仅站内流通，无现金价值。' }}</p>
      <template #footer>
        <el-button @click="listDialog = false">取消</el-button>
        <el-button type="primary" :loading="assetActing" @click="doList">确认挂牌</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="splitDialog" title="拆分叠卡" width="min(380px, 94vw)" align-center append-to-body class="wc-dialog">
      <p class="dialog-note">
        从叠卡堆中拆出独立卡牌，每张获得新序列号。拆分后新卡进入 7 天冷却，之后可挂牌/转赠/质押。
      </p>
      <el-form label-position="top">
        <el-form-item :label="`拆分数量（最多 ${splitMax} 张，堆中至少保留 1 张）`">
          <el-input-number v-model="splitAmount" :min="1" :max="splitMax" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="splitDialog = false">取消</el-button>
        <el-button type="primary" :loading="assetActing" @click="doSplit">确认拆分</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="giftDialog" title="转赠球星卡" width="min(380px, 94vw)" align-center append-to-body class="wc-dialog">
      <el-form label-position="top">
        <el-form-item label="对方邀请码">
          <el-input v-model="giftForm.code" placeholder="输入好友的邀请码" maxlength="12" />
        </el-form-item>
      </el-form>
      <p class="dialog-note">转赠需双方完成实名认证；转赠后对方需冷却期后方可再次流通。</p>
      <template #footer>
        <el-button @click="giftDialog = false">取消</el-button>
        <el-button type="primary" :loading="assetActing" @click="doGift">确认转赠</el-button>
      </template>
    </el-dialog>
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
import { createListing, giftCard, buybackCard, stakeCard, splitCard, getListingHint, type ListingHint } from '@/api/asset'
import AssetHubBar from '@/components/asset/AssetHubBar.vue'
import { extractApiError } from '@/utils/apiError'
import { useAssetRealname } from '@/composables/useAssetRealname'
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
  description: '猜中掉落球星卡，收集套组赢奖励。可用积分二级流通，无现金价值、不可提现。',
  path: '/collection',
  noIndex: true,
})

async function confirmCollectibleAction(
  message: string,
  title: string,
  confirmButtonText: string,
  type: 'warning' | 'info' = 'warning',
) {
  await ElMessageBox.confirm(message, title, {
    customClass: 'wc-message-box',
    roundButton: true,
    confirmButtonText,
    cancelButtonText: '取消',
    type,
  })
}

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

// ===== 资产流通（挂牌/转赠/质押/回购/拆分）=====
const { ensureVerified } = useAssetRealname()
const listDialog = ref(false)
const giftDialog = ref(false)
const splitDialog = ref(false)
const assetActing = ref(false)
const listForm = ref<{ type: string; price: number }>({ type: 'fixed', price: 100 })
const giftForm = ref<{ code: string }>({ code: '' })
const splitAmount = ref(1)
const splitMax = ref(1)
const listHint = ref<ListingHint | null>(null)

const LOCK_LABELS: Record<string, string> = {
  listed: '已挂牌',
  staked: '已质押',
  duel: '对决中',
}
function lockStateLabel(state: string) {
  return LOCK_LABELS[state] || '锁定中'
}

function stackCount(card: CollectibleCardBrief): number {
  return card.asset?.stack_count ?? card.count ?? 1
}

function isStacked(card: CollectibleCardBrief): boolean {
  return stackCount(card) > 1
}

function maxSplitAmount(card: CollectibleCardBrief): number {
  return Math.max(0, stackCount(card) - 1)
}

function canCirculate(card: CollectibleCardBrief): boolean {
  const a = card.asset
  if (!a) return false
  return a.tradable && !isStacked(card) && a.lock_state === 'none' && !a.cooling_down
}

async function refreshSelectedCard() {
  const code = selectedCard.value?.code
  const id = selectedCard.value?.user_card_id
  if (!code) return
  try {
    selectedCard.value = await getCollectibleCard(code, id)
  } catch {
    /* keep current */
  }
}

function openSplitDialog() {
  if (!selectedCard.value) return
  splitMax.value = maxSplitAmount(selectedCard.value)
  splitAmount.value = 1
  splitDialog.value = true
}

async function doSplit() {
  const id = selectedCard.value?.user_card_id
  if (!id) return
  assetActing.value = true
  try {
    const res = await splitCard(id, splitAmount.value)
    ElMessage.success(res.notice)
    splitDialog.value = false
    await refreshAfterMutation()
    await refreshSelectedCard()
  } catch (e: unknown) {
    ElMessage.error(assetErr(e) || '拆分失败')
  } finally {
    assetActing.value = false
  }
}

async function openListDialog() {
  if (!(await ensureVerified('挂牌出售'))) return
  listHint.value = null
  if (selectedCard.value?.asset) {
    listForm.value.price = Math.max(10, selectedCard.value.asset.estimated_value)
  }
  listDialog.value = true
  const id = selectedCard.value?.user_card_id
  if (id) {
    try {
      listHint.value = await getListingHint(id)
      listForm.value.price = listHint.value.suggested_price
    } catch {
      /* fallback to estimated */
    }
  }
}

function applySuggestedPrice() {
  if (listHint.value) listForm.value.price = listHint.value.suggested_price
}

async function openGiftDialog() {
  if (!(await ensureVerified('转赠'))) return
  giftForm.value.code = ''
  giftDialog.value = true
}

async function doList() {
  const id = selectedCard.value?.user_card_id
  if (!id) return
  assetActing.value = true
  try {
    await createListing({
      user_card_id: id,
      list_type: listForm.value.type,
      price_points: listForm.value.price,
    })
    ElMessage.success('挂牌成功，已在交易行展示')
    listDialog.value = false
    await refreshAfterMutation()
    await refreshSelectedCard()
  } catch (e: unknown) {
    ElMessage.error(assetErr(e) || '挂牌失败')
  } finally {
    assetActing.value = false
  }
}

async function doGift() {
  const id = selectedCard.value?.user_card_id
  if (!id) return
  if (!giftForm.value.code.trim()) {
    ElMessage.warning('请输入对方邀请码')
    return
  }
  assetActing.value = true
  try {
    const res = await giftCard(id, giftForm.value.code.trim())
    ElMessage.success(res.notice || '转赠成功')
    giftDialog.value = false
    detailOpen.value = false
    await refreshAfterMutation()
  } catch (e: unknown) {
    ElMessage.error(assetErr(e) || '转赠失败')
  } finally {
    assetActing.value = false
  }
}

async function onStake() {
  const id = selectedCard.value?.user_card_id
  if (!id) return
  if (!(await ensureVerified('质押'))) return
  try {
    await confirmCollectibleAction(
      '质押该卡可产被动可用积分并为该球队竞猜加成，质押期间不可流通。确认质押？',
      '质押球星卡',
      '确认质押',
      'info',
    )
  } catch {
    return
  }
  try {
    const res = await stakeCard(id)
    ElMessage.success(`质押成功 · 每日 ${res.daily_yield} 可用积分`)
    await refreshAfterMutation()
    await refreshSelectedCard()
  } catch (e: unknown) {
    ElMessage.error(assetErr(e) || '质押失败')
  }
}

async function onBuyback() {
  const id = selectedCard.value?.user_card_id
  const quote = selectedCard.value?.asset?.buyback_quote ?? 0
  if (!id) return
  if (!(await ensureVerified('官方回购'))) return
  try {
    await confirmCollectibleAction(
      `官方将以 ${quote} 可用积分回购该卡（卡牌被平台回收，仅返还可用积分，无现金价值）。确认回购？`,
      '官方回购',
      '确认回购',
      'warning',
    )
  } catch {
    return
  }
  try {
    const res = await buybackCard(id)
    ElMessage.success(`回购完成，+${res.points_gained} 可用积分（累计积分不变，可用于商城兑换）`)
    detailOpen.value = false
    await refreshAfterMutation()
    await fetchMe()
  } catch (e: unknown) {
    ElMessage.error(assetErr(e) || '回购失败')
  }
}

function assetErr(e: unknown): string {
  return extractApiError(e)
}
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
    await confirmCollectibleAction(
      '消耗 30 球迷币激活 24 小时手册经验 +50%？',
      '经验加成',
      '确认购买',
      'info',
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
  if (passSummary.value?.event_cheer_status?.cheered_today) {
    ElMessage.info('今日已应援过，明日再来')
    return
  }
  eventCheerLoading.value = true
  try {
    const res = await eventCheerDrop(teamId)
    if (res.already_claimed || res.collectible_drop?.already_claimed) {
      ElMessage.info('今日已应援过，请勿重复点击')
      await ensurePassSummary(true)
      return
    }
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
    selectedCard.value = await getCollectibleCard(card.code, card.user_card_id)
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
      await confirmCollectibleAction(
        '将使用球迷币按上限补足缺口碎片（确定性消耗，非随机抽卡）。确认继续？',
        '球迷币补碎片',
        '确认合成',
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
      await confirmCollectibleAction(
        '将使用球迷币按上限补足缺口碎片（确定性消耗）。确认升星？',
        '球迷币补碎片升星',
        '确认升星',
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
.asset-nav {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  margin-bottom: 12px;
}
.asset-nav-item {
  text-align: center;
  padding: 10px 4px;
  border-radius: 10px;
  font-size: 0.78rem;
  font-weight: 600;
  text-decoration: none;
  color: var(--wc-accent-gold);
  background: linear-gradient(135deg, rgba(60, 45, 25, 0.35), rgba(25, 20, 35, 0.5));
  border: 1px solid rgba(212, 165, 116, 0.18);
  transition: transform 0.12s;
}
.asset-nav-item:active {
  transform: scale(0.96);
}
.asset-panel {
  margin: 10px 0;
  padding: 12px;
  border-radius: 10px;
  background: linear-gradient(135deg, rgba(60, 45, 25, 0.35), rgba(25, 20, 35, 0.5));
}
.asset-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.82rem;
  padding: 3px 0;
}
.asset-row span {
  color: var(--wc-text-muted);
}
.asset-row .gold {
  color: var(--wc-accent-gold);
}
.asset-cooling {
  margin-top: 6px;
  font-size: 0.72rem;
  color: #f0b86c;
}
.stack-hint p {
  margin: 0 0 8px;
}
.stack-hint .stack-tip {
  font-size: 0.68rem;
  color: var(--wc-text-muted);
}
.asset-note {
  margin: 8px 0 0;
  font-size: 0.64rem;
  color: var(--wc-text-muted);
  line-height: 1.4;
}
.asset-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 10px;
}
.dialog-note {
  font-size: 0.7rem;
  color: var(--wc-text-muted);
  line-height: 1.4;
  margin: 4px 0 0;
}
.list-hint {
  padding: 10px 12px;
  border-radius: 10px;
  margin-bottom: 12px;
}
.lh-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.82rem;
}
.lh-row .gold {
  color: var(--wc-accent-gold);
  font-size: 1.05rem;
  flex: 1;
}
.lh-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 6px;
  font-size: 0.66rem;
  color: var(--wc-text-muted);
}
.lh-net {
  margin: 6px 0 0;
  font-size: 0.66rem;
  color: var(--wc-text-muted);
}
</style>
