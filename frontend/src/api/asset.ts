import { apiClient } from './client'

// ===================== 实名 / 资产组合 / 成就 =====================
export interface RealNameStatus {
  verified: boolean
  verified_at?: string | null
}

export interface PortfolioSummary {
  portfolio_value: number
  redeem_points: number
  fan_coins: number
  currency_label: string
  newly_unlocked: string[]
  real_name_verified: boolean
  disclaimer: string
}

export interface Achievement {
  code: string
  name: string
  desc: string
  unlocked: boolean
  unlocked_at?: string | null
}

export async function getRealNameStatus(): Promise<RealNameStatus> {
  const { data } = await apiClient.get('/api/asset/realname/status')
  return data
}

export async function verifyRealName(real_name: string, id_no: string): Promise<RealNameStatus> {
  const { data } = await apiClient.post('/api/asset/realname/verify', { real_name, id_no })
  return data
}

export async function getPortfolio(): Promise<PortfolioSummary> {
  const { data } = await apiClient.get('/api/asset/portfolio')
  return data
}

export async function getAchievements(): Promise<Achievement[]> {
  const { data } = await apiClient.get('/api/asset/achievements')
  return data.items
}

export interface AssetHubSummary {
  redeem_points: number
  fan_coins: number
  portfolio_value: number
  real_name_verified: boolean
  claimable_stake_points: number
  active_stakes: number
  active_listings: number
  duel_pending_incoming: number
  duel_pending_outgoing: number
  live_mint_events: number
  fantasy_score: number
  fantasy_rank: number | null
  achievements_unlocked: number
  achievements_total: number
  action_count: number
}

export async function getAssetHubSummary(): Promise<AssetHubSummary> {
  const { data } = await apiClient.get('/api/asset/hub-summary')
  return data
}

export interface ListingHint {
  user_card_id: number
  card_name: string
  estimated_value: number
  floor_price: number | null
  last_trade_price: number | null
  buyback_floor: number
  suggested_price: number
  price_range: { min: number; max: number }
  active_listings: number
  fee_pct: number
  net_after_fee: number
  disclaimer: string
}

export async function getListingHint(user_card_id: number): Promise<ListingHint> {
  const { data } = await apiClient.get('/api/asset/listing-hint', { params: { user_card_id } })
  return data
}

export interface BattalionBoostTeam {
  team_id: number
  team_name: string
  boost_pct: number
}

export interface BattalionBoostSummary {
  favorite_boost_pct: number
  teams: BattalionBoostTeam[]
}

export async function getBattalionBoost(): Promise<BattalionBoostSummary> {
  const { data } = await apiClient.get('/api/asset/battalion-boost')
  return data
}

// ===================== 转赠 / 回购 =====================
export async function giftCard(user_card_id: number, to_invite_code: string) {
  const { data } = await apiClient.post('/api/asset/gift', { user_card_id, to_invite_code })
  return data
}

export async function buybackCard(user_card_id: number) {
  const { data } = await apiClient.post('/api/asset/buyback', { user_card_id })
  return data
}

export async function splitCard(user_card_id: number, amount = 1) {
  const { data } = await apiClient.post('/api/asset/split', { user_card_id, amount })
  return data as {
    ok: boolean
    split_count: number
    remaining_stack: number
    new_user_card_ids: number[]
    notice: string
  }
}

export interface TransferLogItem {
  id: number
  kind: string
  direction: 'in' | 'out'
  card_name: string
  rarity: string
  points_amount: number
  fee_points: number
  at?: string | null
}

export async function getTransferHistory(limit = 30): Promise<TransferLogItem[]> {
  const { data } = await apiClient.get('/api/asset/transfer-history', { params: { limit } })
  return data.items
}

// ===================== 质押 =====================
export interface StakeItem {
  stake_id: number
  user_card_id: number
  card_name: string
  rarity: string
  image_url: string | null
  daily_yield: number
  pending: number
  total_claimed: number
  staked_at?: string | null
}

export async function getStakes(): Promise<StakeItem[]> {
  const { data } = await apiClient.get('/api/asset/stakes')
  return data.items
}

export async function stakeCard(user_card_id: number) {
  const { data } = await apiClient.post('/api/asset/stake', { user_card_id })
  return data
}

export async function claimStake(stake_id: number) {
  const { data } = await apiClient.post(`/api/asset/stake/${stake_id}/claim`)
  return data
}

export async function unstakeCard(stake_id: number) {
  const { data } = await apiClient.post(`/api/asset/stake/${stake_id}/unstake`)
  return data
}

// ===================== 数字阵容 Fantasy =====================
export interface FantasyEligibleCard {
  user_card_id: number
  card_code: string
  name: string
  rarity: string
  image_url: string | null
  position?: string
  rating?: number
  star: number
}

export interface FantasySlotCard {
  user_card_id: number
  name: string
  rarity: string
  image_url: string | null
  star: number
}

export interface FantasyLineup {
  period_key: string
  size: number
  slots: FantasySlotCard[]
  score: number
  weekly_reward_coins: number
  reward_tiers?: { rank: number; coins: number }[]
  my_rank?: { rank: number | null; score: number; on_board: boolean }
}

export interface FantasyScoreLogItem {
  match_id: number
  match_label?: string | null
  points: number
  detail: Record<string, unknown>
  at?: string | null
}

export async function getFantasy(): Promise<{
  lineup: FantasyLineup
  eligible: FantasyEligibleCard[]
  score_logs?: FantasyScoreLogItem[]
}> {
  const { data } = await apiClient.get('/api/asset/fantasy')
  return data
}

export async function saveFantasy(user_card_ids: number[]): Promise<FantasyLineup> {
  const { data } = await apiClient.post('/api/asset/fantasy', { user_card_ids })
  return data
}

export async function getFantasyLeaderboard(): Promise<{
  items: { rank: number; nickname: string; score: number }[]
  my_rank?: { rank: number | null; score: number; on_board: boolean }
  reward_tiers?: { rank: number; coins: number }[]
}> {
  const { data } = await apiClient.get('/api/asset/fantasy/leaderboard')
  return data
}

// ===================== 卡牌对决 =====================
export interface DuelEligibleCard {
  user_card_id: number
  name: string
  rarity: string
  image_url: string | null
  star: number
  rating?: number
  position?: string
  power: number
  bp?: number
  combat_stats?: Record<string, number>
}

export interface DuelHistoryItem {
  duel_id: number
  mode: string
  won: boolean
  role?: string
  opponent_nickname?: string
  challenger_power: number
  defender_power: number
  stake_points: number
  elo_delta?: number
  at?: string | null
}

export interface DuelPendingItem {
  duel_id: number
  challenger_id: number
  challenger_nickname: string
  stake_points: number
  created_at?: string | null
}

export interface DuelConfig {
  stake_min: number
  stake_max: number
  fee_pct: number
  mode: string
  win_battalion: number
  quick_match_enabled?: boolean
  match_window_sec?: number
}

export interface DuelRoundCard {
  name: string
  rarity?: string
  image_url?: string | null
  position?: string
  star?: number
  bp?: number
  stats?: Record<string, number>
}

export interface DuelRound {
  round: number
  challenger_card: DuelRoundCard
  defender_card: DuelRoundCard
  challenger_score: number
  defender_score: number
  winner_side: 'challenger' | 'defender'
  narrative: string
  stat_comparison?: { key: string; label: string; a: number; b: number; winner: string }[]
  modifiers?: { type: string; label: string; factor: number }[]
}

export interface DuelDetail {
  duel_id: number
  mode: string
  status: string
  won: boolean | null
  role: string
  challenger_nickname: string
  defender_nickname: string
  challenger_power: number
  defender_power: number
  winner_id?: number | null
  stake_points: number
  rounds: DuelRound[]
  replay?: { rounds?: DuelRound[]; winner_side?: string }
  settled_at?: string | null
  your_elo_delta?: number | null
}

export interface DuelSettleResult {
  ok: boolean
  duel_id: number
  won: boolean
  elo_delta?: number
  duel_elo?: number
  notice: string
  payout_notice?: string
  battalion_added?: number
  challenger_power: number
  defender_power: number
  rounds?: DuelRound[]
  replay?: { rounds?: DuelRound[] }
}

export async function getDuelConfig(): Promise<DuelConfig> {
  const { data } = await apiClient.get('/api/card-duel/config')
  return data
}

export async function getDuelEligible(): Promise<DuelEligibleCard[]> {
  const { data } = await apiClient.get('/api/card-duel/eligible')
  return data.items
}

export async function getDuelPending(): Promise<DuelPendingItem[]> {
  const { data } = await apiClient.get('/api/card-duel/pending')
  return data.items
}

export interface DuelOutgoingItem {
  duel_id: number
  defender_nickname: string
  stake_points: number
  created_at?: string | null
}

export async function getDuelOutgoing(): Promise<DuelOutgoingItem[]> {
  const { data } = await apiClient.get('/api/card-duel/outgoing')
  return data.items
}

export async function cancelDuel(duel_id: number) {
  const { data } = await apiClient.post(`/api/card-duel/${duel_id}/cancel`)
  return data
}

export async function challengeAiDuel(card_ids: number[], stake_points = 0) {
  const { data } = await apiClient.post('/api/card-duel/challenge-ai', { card_ids, stake_points })
  return data as DuelSettleResult
}

export async function challengeUserDuel(
  card_ids: number[],
  opts: { defender_id?: number; invite_code?: string; stake_points?: number },
) {
  const { data } = await apiClient.post('/api/card-duel/challenge', {
    card_ids,
    defender_id: opts.defender_id,
    invite_code: opts.invite_code,
    stake_points: opts.stake_points ?? 0,
  })
  return data
}

export async function acceptDuel(duel_id: number, card_ids: number[]) {
  const { data } = await apiClient.post(`/api/card-duel/${duel_id}/accept`, { card_ids })
  return data as DuelSettleResult
}

export async function getDuelDetail(duel_id: number): Promise<DuelDetail> {
  const { data } = await apiClient.get(`/api/card-duel/${duel_id}`)
  return data
}

export async function getDuelReplay(duel_id: number): Promise<DuelDetail> {
  const { data } = await apiClient.get(`/api/card-duel/${duel_id}/replay`)
  return data
}

export async function enterDuelMatch(card_ids: number[], stake_points = 0) {
  const { data } = await apiClient.post('/api/card-duel/match/enter', { card_ids, stake_points })
  return data as { ok: boolean; queue_id: number; deck_bp: number; notice: string; expires_at?: string }
}

export async function cancelDuelMatch() {
  const { data } = await apiClient.post('/api/card-duel/match/cancel')
  return data
}

export async function getDuelMatchStatus() {
  const { data } = await apiClient.get('/api/card-duel/match/status')
  return data as {
    in_queue: boolean
    matched?: boolean
    duel_id?: number
    deck_bp?: number
    expires_at?: string
  }
}

export interface DuelStats {
  total_duels: number
  wins: number
  losses: number
  win_rate: number
  current_streak: number
  streak_type: string | null
  ai_wins: number
  pvp_wins: number
  duel_elo: number
  elo_tier: { code: string; label: string }
  rank_tier: { code: string; label: string }
}

export interface DuelDeckPreview {
  count: number
  total_bp: number
  avg_bp: number
  tier: number
  chemistry: string[]
  positions: string[]
  matchup_hints?: string[]
}

export interface DuelRecommendDeck extends DuelDeckPreview {
  card_ids: number[]
  score: number
  reason: string
}

export async function getDuelStats(): Promise<DuelStats> {
  const { data } = await apiClient.get('/api/card-duel/stats')
  return data
}

export async function getDuelLeaderboard(limit = 10, by: 'wins' | 'elo' = 'wins') {
  const { data } = await apiClient.get('/api/card-duel/leaderboard', { params: { limit, by } })
  return data.items as Array<
    | { user_id: number; nickname: string; wins: number; duel_elo?: number }
    | { user_id: number; nickname: string; duel_elo: number; elo_tier: { code: string; label: string } }
  >
}

export async function previewDuelDeck(card_ids: number[]): Promise<DuelDeckPreview> {
  const { data } = await apiClient.post('/api/card-duel/deck-preview', { card_ids })
  return data
}

export async function recommendDuelDeck(): Promise<DuelRecommendDeck> {
  const { data } = await apiClient.get('/api/card-duel/recommend-deck')
  return data
}

export async function getDuelHistory(limit = 10): Promise<DuelHistoryItem[]> {
  const { data } = await apiClient.get('/api/card-duel/history', { params: { limit } })
  return data.items
}

// ===================== 交易行 Marketplace =====================
export interface MarketListing {
  listing_id: number
  list_type: 'fixed' | 'auction'
  card_code: string
  card_name: string
  rarity: string
  series: string
  image_url: string | null
  price_points: number
  current_bid: number
  current_price: number
  min_increment: number
  star: number
  serial_no?: number | null
  mint_total?: number | null
  expires_at?: string | null
  seller_id: number
  is_mine?: boolean
  status?: string
}

export interface MarketData {
  floor_price: number | null
  active_listings: number
  volume_24h: number
  trades_24h: number
  last_price: number | null
  history: { price: number; at?: string | null }[]
  buyback_floor: number
  currency: string
}

export async function browseMarket(params: {
  rarity?: string
  series?: string
  list_type?: string
  sort?: string
  scope?: 'all' | 'mine' | 'others'
  page?: number
  limit?: number
}): Promise<{ items: MarketListing[]; total: number; page: number; has_more: boolean; disclaimer: string }> {
  const { data } = await apiClient.get('/api/marketplace/browse', { params })
  return data
}

export async function getMyListings(): Promise<MarketListing[]> {
  const { data } = await apiClient.get('/api/marketplace/my-listings')
  return data.items
}

export async function getListingDetail(listing_id: number): Promise<
  MarketListing & { market: MarketData; recent_bids: { amount: number; at?: string | null }[]; disclaimer: string }
> {
  const { data } = await apiClient.get(`/api/marketplace/listing/${listing_id}`)
  return data
}

export async function getCardMarket(card_id: number): Promise<MarketData> {
  const { data } = await apiClient.get(`/api/marketplace/card/${card_id}/market`)
  return data
}

export async function createListing(body: {
  user_card_id: number
  list_type: string
  price_points: number
  duration_hours?: number
}) {
  const { data } = await apiClient.post('/api/marketplace/list', body)
  return data
}

export async function cancelListing(listing_id: number) {
  const { data } = await apiClient.post(`/api/marketplace/listing/${listing_id}/cancel`)
  return data
}

export async function buyListing(listing_id: number) {
  const { data } = await apiClient.post(`/api/marketplace/listing/${listing_id}/buy`)
  return data
}

export async function bidListing(listing_id: number, amount: number) {
  const { data } = await apiClient.post(`/api/marketplace/listing/${listing_id}/bid`, { amount })
  return data
}

// ===================== 首发打新 Mint =====================
export interface MintEvent {
  id: number
  code: string
  name: string
  description?: string | null
  card_code: string
  image_url?: string | null
  rarity: string
  competition?: string | null
  total_supply: number
  issued: number
  remaining: number
  currency: 'coins' | 'rmb'
  price_coins: number
  price_fen: number
  per_user_limit: number
  sale_mode: 'public' | 'whitelist' | 'lottery'
  phase: string
  reserve_starts_at?: string | null
  starts_at?: string | null
  ends_at?: string | null
  reserved: boolean
  reservation_status?: string | null
  can_buy: boolean
  disclaimer: string
}

export async function getMintEvents(): Promise<MintEvent[]> {
  const { data } = await apiClient.get('/api/mint-events')
  return data.items
}

export async function reserveMint(event_id: number) {
  const { data } = await apiClient.post(`/api/mint-events/${event_id}/reserve`)
  return data
}

export async function purchaseMint(event_id: number) {
  const { data } = await apiClient.post(`/api/mint-events/${event_id}/purchase`)
  return data
}

// ===================== 运营经济看板（Admin） =====================
export interface EconomyDashboard {
  window_days: number
  redeem_points: {
    total_in: number
    total_out: number
    net_flow: number
    inflation_pct: number
    faucet: Record<string, { amount: number; count: number }>
    sink: Record<string, { amount: number; count: number }>
  }
  marketplace: {
    trade_volume: number
    trade_count: number
    fee_sink: number
    active_listings: number
  }
  buyback_spend: number
  gift_count: number
  staking: { active_stakes: number; total_yield_claimed: number }
  health_hint: string
}

const ADMIN_SECRET_KEY = 'wc_admin_secret'

export function getStoredAdminSecret(): string {
  try {
    return sessionStorage.getItem(ADMIN_SECRET_KEY) || ''
  } catch {
    return ''
  }
}

export function setStoredAdminSecret(secret: string) {
  try {
    sessionStorage.setItem(ADMIN_SECRET_KEY, secret)
  } catch {
    /* ignore */
  }
}

export async function getEconomyDashboard(days = 7, adminSecret?: string): Promise<EconomyDashboard> {
  const secret = adminSecret ?? getStoredAdminSecret()
  const { data } = await apiClient.get('/api/asset/admin/economy', {
    params: { days },
    headers: secret ? { 'X-Admin-Secret': secret } : undefined,
  })
  return data
}
