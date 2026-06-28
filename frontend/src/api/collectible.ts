import { apiClient } from './client'

export type CardRarity = 'common' | 'rare' | 'epic' | 'legend'

export interface CollectibleCardBrief {
  code: string
  name: string
  rarity: CardRarity
  series: string
  image_url: string | null
  attributes: Record<string, unknown>
  player_id: number | null
  team_id: number | null
  owned?: boolean
  star?: number
  count?: number
  highlights?: CollectibleHighlight[]
  obtained_at?: string | null
  source?: string
  is_duplicate?: boolean
  shards_gained?: number
  user_card_id?: number
  chain?: CollectibleChainBrief | null
  upgrade_cost?: { shards: number; redeem_points: number }
  can_upgrade?: boolean
  asset?: CardAssetBrief | null
}

export interface CardAssetBrief {
  card_id: number
  serial_no: number | null
  mint_total: number | null
  tradable: boolean
  stack_count?: number
  lock_state: 'none' | 'listed' | 'staked' | 'duel'
  holding_until: string | null
  cooling_down: boolean
  estimated_value: number
  buyback_quote: number
  currency: string
  battle_power?: number
  combat_stats?: Record<string, number> | null
}

export interface CollectibleChainBrief {
  enabled: boolean
  chain_name: string
  status: string
  nft_id?: string | null
  class_id?: string | null
  tx_hash?: string | null
  minted_at?: string | null
  error?: string | null
}

export interface CollectibleChainStatus {
  enabled: boolean
  chain_name: string
  mock: boolean
  pending_mints: number
  minted_count: number
  failed_mints?: number
  first_failed_user_card_id?: number | null
  account: { native_address?: string; status?: string; chain_name?: string } | null
  compliance_notice: string
}

export interface CollectibleHighlight {
  match_id: number
  team1?: string
  team2?: string
  score?: string
  type?: string
  at?: string
}

export interface CollectibleDropResult {
  dropped: boolean
  cards: CollectibleCardBrief[]
  shards: Array<{ rarity: CardRarity; amount: number; reason?: string }>
  source: string
  chain_enabled?: boolean
}

export interface CollectibleAlbum {
  cards: CollectibleCardBrief[]
  total: number
  owned_count: number
  completion_pct: number
  shards: Record<CardRarity, number>
  redeem_points: number
  compliance_notice: string
  chain_enabled?: boolean
  series_options?: Array<{ value: string; label: string }>
  page?: number
  limit?: number
  page_total?: number
  has_more?: boolean
}

export interface CardSetProgress {
  code: string
  name: string
  description: string | null
  card_codes: string[]
  owned_codes?: string[]
  missing_codes?: string[]
  missing_names?: string[]
  owned_count: number
  total_count: number
  complete: boolean
  claimed: boolean
  reward: Record<string, unknown>
}

export interface CollectibleSummary {
  owned_count: number
  total_cards: number
  completion_pct: number
  shards: Record<CardRarity, number>
  redeem_points: number
  signin_streak: number
  next_signin_milestone: {
    day: number
    days_left: number
    rarity: CardRarity
    label: string
  } | null
  hooks: Record<string, string>
  chain_enabled?: boolean
  failed_mints?: number
  compliance_notice: string
}

export interface CollectibleActivityItem {
  source: string
  at: string | null
  cards: CollectibleCardBrief[]
  shards: Array<{ rarity: CardRarity; amount: number }>
}

export interface SynthesisOption extends CollectibleCardBrief {
  cost: { shards: number; redeem_points: number }
  can_synthesize: boolean
}

export async function getCollectibleSummary() {
  const { data } = await apiClient.get<CollectibleSummary>('/api/collectible/summary')
  return data
}

export async function getCollectibleActivity(limit = 15) {
  const { data } = await apiClient.get<{ items: CollectibleActivityItem[] }>('/api/collectible/activity', {
    params: { limit },
  })
  return data.items
}

export async function retryCollectibleChainMint(userCardId: number) {
  const { data } = await apiClient.post<{ chain: CollectibleChainBrief }>(
    `/api/collectible/chain/retry/${userCardId}`,
  )
  return data.chain
}

export async function getCollectibleAlbum(
  opts?: {
    rarity?: string
    series?: string
    ownedOnly?: boolean
    page?: number
    limit?: number
    brief?: boolean
  },
) {
  const { data } = await apiClient.get<CollectibleAlbum>('/api/collectible/album', {
    params: {
      rarity: opts?.rarity || undefined,
      series: opts?.series || undefined,
      owned_only: opts?.ownedOnly || undefined,
      page: opts?.page ?? undefined,
      limit: opts?.limit ?? undefined,
      brief: opts?.brief ?? true,
    },
  })
  return data
}

export async function getCollectibleOwnedPreview(limit = 6, minRarity = 'rare') {
  const { data } = await apiClient.get<{ cards: CollectibleCardBrief[] }>('/api/collectible/owned-preview', {
    params: { limit, min_rarity: minRarity },
  })
  return data.cards
}

export async function getCollectibleSets() {
  const { data } = await apiClient.get<{ sets: CardSetProgress[] }>('/api/collectible/sets')
  return data.sets
}

export async function getCollectibleCard(code: string, user_card_id?: number) {
  const { data } = await apiClient.get<CollectibleCardBrief & { compliance_notice: string }>(
    `/api/collectible/card/${encodeURIComponent(code)}`,
    { params: user_card_id ? { user_card_id } : undefined },
  )
  return data
}

export async function getSynthesisOptions() {
  const { data } = await apiClient.get<{ options: SynthesisOption[] }>('/api/collectible/synthesis-options')
  return data.options
}

export async function synthesizeCard(cardCode: string, useCoinFill = false) {
  const { data } = await apiClient.post('/api/collectible/synthesize', {
    card_code: cardCode,
    use_coin_fill: useCoinFill,
  })
  return data
}

export async function upgradeCollectibleCard(cardCode: string, useCoinFill = false) {
  const { data } = await apiClient.post('/api/collectible/upgrade', {
    card_code: cardCode,
    use_coin_fill: useCoinFill,
  })
  return data
}

export async function claimCollectibleSet(setCode: string) {
  const { data } = await apiClient.post(`/api/collectible/sets/${encodeURIComponent(setCode)}/claim`)
  return data
}

export async function refreshCollectibleChainMint(userCardId: number) {
  const { data } = await apiClient.post<{ chain: CollectibleChainBrief }>(
    `/api/collectible/chain/refresh/${userCardId}`,
  )
  return data.chain
}

export interface ProvenanceEvent {
  kind: string
  at: string | null
  label: string
  detail?: string
  nft_id?: string | null
  tx_hash?: string | null
  chain_status?: string | null
  error?: string
  direction?: string
  points_amount?: number
}

export interface CollectibleProvenance {
  user_card_id: number
  card_name: string | null
  serial_no: number | null
  chain: CollectibleChainBrief | null
  events: ProvenanceEvent[]
  compliance_notice: string
}

export async function getCollectibleProvenance(userCardId: number) {
  const { data } = await apiClient.get<CollectibleProvenance>(
    `/api/collectible/user-card/${userCardId}/provenance`,
  )
  return data
}

export async function getCollectibleChainStatus() {
  const { data } = await apiClient.get<CollectibleChainStatus>('/api/collectible/chain/status')
  return data
}

export async function getUserCardChainStatus(userCardId: number) {
  const { data } = await apiClient.get<{
    user_card_id: number
    chain_status: string
    chain_nft_id: string | null
    chain_tx_hash: string | null
    serial_no: number | null
  }>(`/api/collectible/user-card/${userCardId}/chain`)
  return data
}

export interface CollectibleShareUrlResponse {
  url: string
  share_text: string
  owned: boolean
  card: {
    code: string
    name: string
    rarity: CardRarity
    star: number
    image_url: string | null
    chain_minted?: boolean
    chain_hash_short?: string | null
  }
}

export async function getCollectibleShareUrl(code: string) {
  const { data } = await apiClient.get<CollectibleShareUrlResponse>('/api/collectible/share-url', {
    params: { code },
  })
  return data
}

export const SOURCE_LABELS: Record<string, string> = {
  predict_win: '猜中',
  signin: '连签',
  matchday: '比赛日',
  referral: '召友',
  synthesis: '合成',
}

export const RARITY_LABELS: Record<CardRarity, string> = {
  common: '普通',
  rare: '稀有',
  epic: '史诗',
  legend: '传奇',
}

export const RARITY_COLORS: Record<CardRarity, string> = {
  common: '#9eb0c8',
  rare: '#7eb8ff',
  epic: '#c9788a',
  legend: '#e8c547',
}
