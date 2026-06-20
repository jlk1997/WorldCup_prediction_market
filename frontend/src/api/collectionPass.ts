import { apiClient } from './client'
import type { CollectibleDropResult } from './collectible'

export type PassReward = {
  fan_coins?: number
  redeem_points?: number
  shards?: Record<string, number>
  card_code?: string
  avatar_frame?: string
  theme_key?: string
  badge_code?: string
  badge_title?: string
}

export type PassTrackLevel = {
  level: number
  threshold_xp: number
  free: PassReward
  premium: PassReward
  free_claimed: boolean
  premium_claimed: boolean
  free_claimable: boolean
  premium_claimable: boolean
}

export type PassTrackCatalogLevel = Omit<
  PassTrackLevel,
  'free_claimed' | 'premium_claimed' | 'free_claimable' | 'premium_claimable'
>

export type PassQuest = {
  key: string
  title: string
  target: number
  progress: number
  completed: boolean
  xp: number
}

export type CollectibleEventBrief = {
  code: string
  name: string
  description?: string
  starts_at?: string
  ends_at?: string
  event_series: string
  coin_action_cost: number
  boost_json?: Record<string, unknown>
}

export type CollectionPassSummaryLite = {
  season: {
    code: string
    name: string
    starts_at?: string
    ends_at?: string
    max_level: number
  }
  xp: number
  level: number
  xp_to_next: number
  xp_level_progress_pct?: number
  next_level: number | null
  premium_unlocked: boolean
  xp_boost_active: boolean
  xp_boost_until?: string | null
  claimable_count?: number
  claimed_free_levels: number[]
  claimed_premium_levels: number[]
  quests: { daily: PassQuest[]; weekly: PassQuest[] }
  events?: CollectibleEventBrief[]
  compliance_notice: string
  premium_sku: string
  premium_price_fen: number
  premium_plus_sku?: string | null
  premium_plus_price_fen?: number | null
}

export type CollectionPassSummary = CollectionPassSummaryLite & {
  tracks: PassTrackLevel[]
}

export type PassTrackCatalog = {
  season_code: string
  max_level: number
  tracks: PassTrackCatalogLevel[]
}

let cachedLite: CollectionPassSummaryLite | null = null
let cachedLiteAt = 0
let inflightLite: Promise<CollectionPassSummaryLite> | null = null

let cachedCatalog: PassTrackCatalog | null = null
let cachedCatalogAt = 0
let inflightCatalog: Promise<PassTrackCatalog> | null = null

let cachedFull: CollectionPassSummary | null = null
let cachedFullAt = 0

const LITE_CACHE_MS = 12_000
const CATALOG_CACHE_MS = 3_600_000

export function invalidatePassSummaryCache() {
  cachedLite = null
  cachedLiteAt = 0
  cachedFull = null
  cachedFullAt = 0
}

export function mergePassSummary(
  lite: CollectionPassSummaryLite,
  catalog: PassTrackCatalog,
): CollectionPassSummary {
  const claimedFree = new Set(lite.claimed_free_levels ?? [])
  const claimedPremium = new Set(lite.claimed_premium_levels ?? [])
  const tracks: PassTrackLevel[] = catalog.tracks.map((t) => ({
    ...t,
    free_claimed: claimedFree.has(t.level),
    premium_claimed: claimedPremium.has(t.level),
    free_claimable: lite.level >= t.level && !claimedFree.has(t.level),
    premium_claimable:
      lite.premium_unlocked && lite.level >= t.level && !claimedPremium.has(t.level),
  }))
  return { ...lite, tracks }
}

export async function getPassTrackCatalog(force = false) {
  const now = Date.now()
  if (!force && cachedCatalog && now - cachedCatalogAt < CATALOG_CACHE_MS) {
    return cachedCatalog
  }
  if (inflightCatalog && !force) return inflightCatalog

  inflightCatalog = (async () => {
    try {
      const { data } = await apiClient.get<PassTrackCatalog>('/api/collection-pass/track-catalog')
      cachedCatalog = data
      cachedCatalogAt = Date.now()
      return data
    } finally {
      inflightCatalog = null
    }
  })()

  return inflightCatalog
}

export async function getCollectionPassSummaryLite(force = false) {
  const now = Date.now()
  if (!force && cachedLite && now - cachedLiteAt < LITE_CACHE_MS) {
    return cachedLite
  }
  if (inflightLite && !force) return inflightLite

  inflightLite = (async () => {
    try {
      const { data } = await apiClient.get<CollectionPassSummaryLite>(
        '/api/collection-pass/summary/lite',
      )
      cachedLite = data
      cachedLiteAt = Date.now()
      cachedFull = null
      cachedFullAt = 0
      return data
    } finally {
      inflightLite = null
    }
  })()

  return inflightLite
}

export async function getCollectionPassSummary(force = false) {
  const now = Date.now()
  if (!force && cachedFull && now - cachedFullAt < LITE_CACHE_MS) {
    return cachedFull
  }

  const [lite, catalog] = await Promise.all([
    getCollectionPassSummaryLite(force),
    getPassTrackCatalog(false),
  ])
  const merged = mergePassSummary(lite, catalog)
  cachedFull = merged
  cachedFullAt = now
  return merged
}

export async function claimPassReward(level: number, track: 'free' | 'premium') {
  const { data } = await apiClient.post<{ level: number; track: string; grants: Record<string, unknown> }>(
    '/api/collection-pass/claim',
    { level, track },
  )
  invalidatePassSummaryCache()
  return data
}

export type PassClaimBatchItem = {
  level: number
  track: string
  grants: Record<string, unknown>
}

export async function claimAllPassRewards() {
  const { data } = await apiClient.post<{ claimed_count: number; claims: PassClaimBatchItem[] }>(
    '/api/collection-pass/claim-all',
  )
  invalidatePassSummaryCache()
  return data
}

export async function buyPassXpBoost() {
  const { data } = await apiClient.post<{ cost: number; xp_boost_until: string; multiplier: number }>(
    '/api/collection-pass/xp-boost',
  )
  invalidatePassSummaryCache()
  return data
}

export async function eventCheerDrop(teamId: number) {
  const { data } = await apiClient.post<{ collectible_drop: CollectibleDropResult }>(
    '/api/collection-pass/event-cheer',
    { team_id: teamId },
  )
  invalidatePassSummaryCache()
  return data
}
