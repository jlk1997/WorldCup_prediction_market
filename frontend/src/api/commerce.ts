import { apiClient } from './client'
import type { AuthUser } from '../stores/authStore'
import type { PayChannel } from '../utils/payEnv'
import { PENDING_ORDER_KEY } from '../utils/payEnv'

export interface GameMatch {
  id: number
  group: string | null
  date: string | null
  time: string | null
  team1: string | null
  team2: string | null
  stadium: string | null
  can_predict?: boolean
  can_cheer?: boolean
  is_main_team?: boolean
  is_sub_team?: boolean
  has_star_player?: boolean
  user_predicted?: boolean
  user_pick?: string | null
  user_prediction_status?: string | null
  user_stake_coins?: number | null
  user_is_free?: boolean
  pick_stats?: PickStats | null
}

export interface GamePrediction {
  id: number
  match_id: number
  pick: string
  pick_label?: string | null
  stake_coins: number
  is_free: boolean
  status: string
  status_label?: string | null
  points_awarded: number
  redeem_points_awarded?: number
  coins_returned: number
  team1?: string | null
  team2?: string | null
  match_date?: string | null
  match_time?: string | null
  final_score?: string | null
  settled_at?: string | null
  created_at?: string | null
}

export interface Product {
  id: number
  sku: string
  name: string
  description: string | null
  price_fen: number
  coins_grant: number
  grant_season_pass_days: number
  product_type: string
  pay_currency?: string
  redeem_price?: number | null
  grant_payload?: Record<string, unknown> | null
  per_user_limit?: number
  featured?: boolean
}

export interface RedeemProduct extends Product {
  stock_total?: number
  stock_sold?: number
  stock_remaining?: number | null
  is_unlimited_stock?: boolean
  is_out_of_stock?: boolean
  user_purchased_count?: number
  can_purchase?: boolean
  purchase_blocked_reason?:
    | 'login_required'
    | 'limit_reached'
    | 'insufficient_points'
    | 'out_of_stock'
    | null
}

export interface RedeemPurchaseResult {
  order: RedeemOrder
  redeem_points_after: number
  stock_remaining: number | null
}

export interface RedeemOrder {
  id: number
  product_id: number
  redeem_price: number
  status: string
  created_at?: string | null
  product_name?: string | null
}

export interface LeaderboardEntry {
  user_id: number
  nickname: string
  season_points?: number
  redeem_points?: number
  points?: number
  rank?: number
  win_streak: number
  win_rate?: number
  wins?: number
  settled?: number
  predict_points?: number
  battalion_points?: number
  tier_label?: string
  is_me?: boolean
}

export interface LeaderboardBoard {
  board: string
  period: string
  period_label: string
  metric: string
  description: string
  min_samples?: number
  rows: LeaderboardEntry[]
}

export interface MyLeaderboardSummary {
  user_id: number
  nickname: string
  season_points: number
  season_rank: number | null
  redeem_points: number
  redeem_rank: number | null
  daily_points: number
  daily_rank: number | null
  redeem_daily_points: number
  redeem_daily_rank: number | null
  weekly_points: number
  weekly_rank: number | null
  redeem_weekly_points: number
  redeem_weekly_rank: number | null
  win_streak: number
  season_gap_to_prev?: number | null
  redeem_gap_to_prev?: number | null
  battalion_points: number
  battalion_rank: number | null
  battalion_team: string | null
  arena_tier: string
  tier_label: string
  predict: { won: number; lost: number; void: number; settled: number; win_rate: number }
  predict_accuracy_rank: number | null
}

export async function getPredictableMatches() {
  const { data } = await apiClient.get<GameMatch[]>('/api/game/matches')
  return data
}

export async function submitPrediction(payload: {
  match_id: number
  pick: string
  stake_coins?: number
  use_free?: boolean
}) {
  const { data } = await apiClient.post<GamePrediction>('/api/game/predict', payload)
  return data
}

export async function raisePredictionStake(matchId: number, additionalStakeCoins: number) {
  const { data } = await apiClient.post<GamePrediction>('/api/game/predict/raise-stake', {
    match_id: matchId,
    additional_stake_coins: additionalStakeCoins,
  })
  return data
}

export async function getMyPredictions() {
  const { data } = await apiClient.get<GamePrediction[]>('/api/game/my-predictions')
  return data
}

export async function signin() {
  const { data } = await apiClient.post<{
    fan_coins: number
    added: number
    match_day_bonus?: boolean
    signin_streak?: number
    streak_bonus?: number
  }>('/api/game/signin')
  return data
}

export interface DailyStatus {
  signed_today: boolean
  last_signin_date?: string | null
  signin_streak: number
  signin_streak_bonus_next?: number | null
  free_predict: { used: number; limit: number; remaining: number }
  quiz: { answered: boolean }
  pending_predictions: number
  next_pending_match?: { match_id: number; label: string; hours_until?: number | null } | null
  streak_risk?: {
    match_id?: number | null
    label?: string | null
    hours_until?: number | null
    win_streak: number
    streak_bonus_next: number
    message: string
  } | null
  win_streak: number
  loss_streak?: number
  redeem_progress?: {
    next_sku: string
    next_name: string
    need: number
    have: number
    gap: number
    pct: number
  } | null
  match_day: boolean
  match_day_message?: string | null
  free_cheer_tickets?: number
  loss_streak_protect_after?: number
  loss_streak_multiplier?: number
  checklist?: Array<{
    key: string
    label: string
    done: boolean
    reward: string
    optional?: boolean
  }>
  next_action?: {
    key: string
    label: string
    path?: string | null
    hint?: string | null
  }
  ritual_progress?: { done: number; total: number; pct: number }
}

export interface PickStats {
  match_id: number
  total: number
  distribution: Record<string, { count: number; pct: number }>
}

export interface PredictPreview {
  pick: string
  use_free: boolean
  stake_coins: number
  on_win: {
    season_points: number
    redeem_points: number
    coins_returned: number
    free_win_coins: number
    streak_bonus: number
  }
}

export interface WinFeedItem {
  nickname: string
  team1: string
  team2: string
  points_awarded: number
  settled_at?: string | null
}

export async function getDailyStatus() {
  const { data } = await apiClient.get<DailyStatus>('/api/game/daily-status')
  return data
}

export async function getMatchPickStats(matchId: number) {
  const { data } = await apiClient.get<PickStats>(`/api/game/matches/${matchId}/pick-stats`)
  return data
}

export async function getPredictPreview(params: {
  pick: string
  stake_coins?: number
  use_free?: boolean
}) {
  const { data } = await apiClient.get<PredictPreview>('/api/game/predict/preview', { params })
  return data
}

export async function getWinFeed(limit = 15) {
  const { data } = await apiClient.get<WinFeedItem[]>('/api/game/win-feed', { params: { limit } })
  return data
}

export async function getLeaderboard(period: string) {
  const { data } = await apiClient.get<LeaderboardEntry[]>('/api/game/leaderboard', { params: { period } })
  return data
}

export async function getLeaderboardBoard(params: {
  board?: string
  period?: string
  team_id?: number
  limit?: number
}) {
  const { data } = await apiClient.get<LeaderboardBoard>('/api/game/leaderboard/board', { params })
  return data
}

export async function getMyLeaderboardSummary() {
  const { data } = await apiClient.get<MyLeaderboardSummary>('/api/game/leaderboard/me')
  return data
}

export async function getLeaderboardRules() {
  const { data } = await apiClient.get('/api/game/leaderboard/rules')
  return data
}

export async function getFanRank() {
  const { data } = await apiClient.get<{ team: string; fans: number }[]>('/api/game/fan-rank')
  return data
}

export async function getProducts() {
  const { data } = await apiClient.get<Product[]>('/api/shop/products')
  return data
}

export async function getRedeemProducts() {
  const { data } = await apiClient.get<RedeemProduct[]>('/api/shop/redeem/products')
  return data
}

export async function redeemPurchase(productId: number, idempotencyKey?: string) {
  const key =
    idempotencyKey ??
    (typeof crypto !== 'undefined' && crypto.randomUUID
      ? crypto.randomUUID()
      : `redeem-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`)
  const { data } = await apiClient.post<RedeemPurchaseResult>('/api/shop/redeem/purchase', {
    product_id: productId,
    idempotency_key: key,
  })
  return data
}

export async function getRedeemOrders() {
  const { data } = await apiClient.get<RedeemOrder[]>('/api/shop/redeem/orders')
  return data
}

export interface RedeemShopRules {
  economy: {
    season_points_label: string
    redeem_points_label: string
    season_points_desc: string
    redeem_points_desc: string
    predict_win_redeem_ratio: number
    no_loss_reward: boolean
  }
  products: Array<{
    sku: string
    name: string
    redeem_price: number | null
    per_user_limit: number
    grant_payload: Record<string, unknown> | null
  }>
  grant_payload_schema?: Record<
    string,
    { type: string; description: string; example: string; values: string[] | null }
  >
  catalog_source?: string
  sync_cli?: string
  sync_api?: string
  catalog_preview?: Array<Record<string, unknown>>
}

export async function getRedeemRules() {
  const { data } = await apiClient.get<RedeemShopRules>('/api/shop/redeem/rules')
  return data
}

export interface PointLedgerEntry {
  id: number
  delta: number
  balance_after: number
  reason: string
  point_bucket: string
  ref_type: string | null
  ref_id: number | null
  created_at: string | null
}

export async function getPointLedger(bucket: 'season' | 'redeem', limit = 30) {
  const { data } = await apiClient.get<{ status: string; bucket: string; data: PointLedgerEntry[] }>(
    '/api/wallet/point-ledger',
    { params: { bucket, limit } },
  )
  return data.data
}

export interface OrderDetail {
  id: number
  out_trade_no: string
  amount_fen: number
  status: string
  paid_at: string | null
  product_name: string
  product_type: string
  coins_grant: number
  grant_season_pass_days: number
  grant_summary?: string[]
  alipay_trade_no: string | null
}

export async function createOrder(
  productId: number,
  ageConfirmed = true,
  payChannel: 'auto' | PayChannel = 'auto',
) {
  const { data } = await apiClient.post<{
    order: { id: number; out_trade_no: string; status: string }
    pay_url: string
    pay_channel: PayChannel
  }>('/api/pay/alipay/create', {
    product_id: productId,
    age_confirmed: ageConfirmed,
    pay_channel: payChannel,
  })
  return data
}

export async function mockPay(outTradeNo: string): Promise<OrderDetail> {
  const { data } = await apiClient.post<OrderDetail>(
    `/api/pay/alipay/mock-pay?out_trade_no=${encodeURIComponent(outTradeNo)}`,
  )
  return data
}

export async function getOrderByTradeNo(outTradeNo: string): Promise<OrderDetail> {
  const { data } = await apiClient.get<OrderDetail>(
    `/api/pay/orders/by-no/${encodeURIComponent(outTradeNo)}`,
  )
  return data
}

/** Ask backend to query Alipay when async notify may have failed. */
export async function syncAlipayOrder(outTradeNo: string): Promise<OrderDetail> {
  const { data } = await apiClient.post<OrderDetail>(
    `/api/pay/alipay/sync?out_trade_no=${encodeURIComponent(outTradeNo)}`,
  )
  return data
}

/** Read cached pending order and return detail if already paid. */
export async function fetchPaidPendingOrder(): Promise<OrderDetail | null> {
  if (typeof sessionStorage === 'undefined') return null
  const pendingNo = sessionStorage.getItem(PENDING_ORDER_KEY)
  if (!pendingNo) return null
  return resolvePaidOrder(pendingNo)
}

/** Try sync + DB read until we know the order is paid (post-Alipay return). */
export async function resolvePaidOrder(outTradeNo: string): Promise<OrderDetail | null> {
  try {
    const synced = await syncAlipayOrder(outTradeNo)
    if (synced.status === 'paid') return synced
  } catch {
    /* notify may still be in flight */
  }
  try {
    const detail = await getOrderByTradeNo(outTradeNo)
    if (detail.status === 'paid') return detail
  } catch {
    /* ignore */
  }
  return null
}

export type PollOrderResult =
  | { ok: true; order: OrderDetail }
  | { ok: false; reason: 'timeout' | 'failed'; order?: OrderDetail }

export async function pollOrderUntilPaid(
  outTradeNo: string,
  opts: { intervalMs?: number; timeoutMs?: number } = {},
): Promise<PollOrderResult> {
  const intervalMs = opts.intervalMs ?? 1500
  const timeoutMs = opts.timeoutMs ?? 45_000
  const deadline = Date.now() + timeoutMs
  let last: OrderDetail | undefined
  let polls = 0

  const paid = await resolvePaidOrder(outTradeNo)
  if (paid) return { ok: true, order: paid }

  while (Date.now() < deadline) {
    if (polls > 0 && polls % 4 === 0) {
      const synced = await resolvePaidOrder(outTradeNo)
      if (synced) return { ok: true, order: synced }
    }
    polls += 1
    last = await getOrderByTradeNo(outTradeNo)
    if (last.status === 'paid') return { ok: true, order: last }
    if (last.status === 'failed' || last.status === 'cancelled') {
      return { ok: false, reason: 'failed', order: last }
    }
    await new Promise((r) => setTimeout(r, intervalMs))
  }

  const final = await resolvePaidOrder(outTradeNo)
  if (final) return { ok: true, order: final }

  if (last?.status === 'pending') return { ok: false, reason: 'timeout', order: last }
  return { ok: false, reason: 'timeout', order: last }
}

export async function getOrder(orderId: number) {
  const { data } = await apiClient.get(`/api/pay/orders/${orderId}`)
  return data
}

export async function updateProfile(payload: { nickname?: string; favorite_team_id?: number | null }) {
  const { data } = await apiClient.patch<AuthUser>('/api/auth/me', payload)
  return data
}

export interface CoinLedgerEntry {
  id: number
  delta: number
  balance_after: number
  reason: string
  ref_type: string | null
  ref_id: number | null
  created_at: string | null
}

export async function getWalletLedger(limit = 50) {
  const { data } = await apiClient.get<{ status: string; data: CoinLedgerEntry[] }>(
    '/api/wallet/ledger',
    { params: { limit } },
  )
  return data.data
}
