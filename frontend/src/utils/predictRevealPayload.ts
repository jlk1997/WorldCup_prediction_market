import type { UserNotification } from '@/api/notifications'
import type { CollectibleDropResult } from '@/api/collectible'

export interface ResolvedPredictPayload {
  status: string
  team1: string
  team2: string
  matchLabel: string
  finalScore: string | null
  userPickLabel: string | null
  resultPickLabel: string | null
  aiPickLabel: string | null
  userFollowedAi: boolean | null
  aiPickCorrect: boolean | null
  pointsAwarded: number
  redeemAwarded: number
  coinsReturned: number
  winStreak: number
  lossStreak: number
  nextMatchId?: number
  voidReason?: string
  seasonRank?: number
  detailLine: string
  collectibleDrop?: CollectibleDropResult | null
}

const MATCH_BODY = /^(.+?)\s+vs\s+(.+?)\s+比分\s*(\d+:\d+)/i
const SCORE_IN_BODY = /比分\s*(\d+:\d+)/i

function str(v: unknown): string {
  return v == null ? '' : String(v).trim()
}

function num(v: unknown): number {
  const n = Number(v)
  return Number.isFinite(n) ? n : 0
}

export function enrichNotificationPayload(note: UserNotification): Record<string, unknown> {
  const payload = { ...(note.payload || {}) } as Record<string, unknown>
  let team1 = str(payload.team1 || payload.team1_name)
  let team2 = str(payload.team2 || payload.team2_name)

  if (!team1 || !team2) {
    const label = str(payload.match_label)
    const labelMatch = label.match(/^(.+?)\s+vs\s+(.+)$/i)
    if (labelMatch) {
      team1 = labelMatch[1].trim()
      team2 = labelMatch[2].trim()
    }
  }

  if (!team1 || !team2) {
    const bodyMatch = note.body.match(MATCH_BODY)
    if (bodyMatch) {
      team1 = bodyMatch[1].trim()
      team2 = bodyMatch[2].trim()
      if (!payload.final_score) payload.final_score = bodyMatch[3]
    }
  }

  if (!payload.final_score) {
    const scoreMatch = note.body.match(SCORE_IN_BODY)
    if (scoreMatch) payload.final_score = scoreMatch[1]
  }

  if (team1) payload.team1 = team1
  if (team2) payload.team2 = team2
  if (team1 && team2 && !payload.match_label) {
    payload.match_label = `${team1} vs ${team2}`
  }
  return payload
}

export function resolvePredictPayload(note: UserNotification | null): ResolvedPredictPayload | null {
  if (!note) return null
  const payload = enrichNotificationPayload(note)
  const team1 = str(payload.team1) || '?'
  const team2 = str(payload.team2) || '?'
  const pick = str(payload.user_pick_label || payload.user_pick) || null

  return {
    status: str(payload.status) || 'lost',
    team1,
    team2,
    matchLabel: `${team1} vs ${team2}`,
    finalScore: str(payload.final_score) || null,
    userPickLabel: pick,
    resultPickLabel: str(payload.result_pick_label) || null,
    aiPickLabel: str(payload.ai_pick_label) || null,
    userFollowedAi:
      payload.user_followed_ai === true
        ? true
        : payload.user_followed_ai === false
          ? false
          : null,
    aiPickCorrect:
      payload.ai_pick_correct === true
        ? true
        : payload.ai_pick_correct === false
          ? false
          : null,
    pointsAwarded: num(payload.points_awarded),
    redeemAwarded: num(payload.redeem_points_awarded),
    coinsReturned: num(payload.coins_returned),
    winStreak: num(payload.win_streak_after),
    lossStreak: num(payload.loss_streak_after),
    nextMatchId: payload.next_match_id != null ? Number(payload.next_match_id) : undefined,
    voidReason: str(payload.void_reason) || undefined,
    seasonRank: payload.season_rank != null ? Number(payload.season_rank) : undefined,
    detailLine: note.body || '',
    collectibleDrop: (payload.collectible_drop as CollectibleDropResult | null | undefined) ?? null,
  }
}

export function formatTemplate(
  template: string,
  vars: Record<string, string | number | undefined | null>,
): string {
  return template.replace(/\{(\w+)\}/g, (_, key: string) => {
    const val = vars[key]
    return val == null || val === '' ? '' : String(val)
  })
}
