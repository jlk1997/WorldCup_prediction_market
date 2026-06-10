import type { AuthUser } from '../stores/authStore'

export interface PredictPreviewResult {
  season_points: number
  redeem_points: number
  coins_returned: number
  free_win_coins: number
  streak_bonus: number
}

const REDEEM_RATIO = 0.5
const LOSS_PROTECT_AFTER = 3
const LOSS_MULTIPLIER = 1.2

export function calcPredictPreview(
  user: AuthUser | null | undefined,
  pick: string,
  stakeCoins: number,
  useFree: boolean,
  opts?: {
    lossStreak?: number
    lossProtectAfter?: number
    lossMultiplier?: number
    redeemRatio?: number
    referralTierGranted?: number
  }
): PredictPreviewResult {
  const lossStreak = opts?.lossStreak ?? 0
  const lossProtectAfter = opts?.lossProtectAfter ?? LOSS_PROTECT_AFTER
  const lossMultiplier = opts?.lossMultiplier ?? LOSS_MULTIPLIER
  const redeemRatio = opts?.redeemRatio ?? REDEEM_RATIO
  const referralTier = opts?.referralTierGranted ?? 0

  let basePoints = pick === 'draw' ? 20 : 30
  if (user?.has_season_pass) {
    basePoints = Math.floor(basePoints * 1.2)
  }
  const streakBonus = Math.min(user?.win_streak ?? 0, 5) * 10
  let totalSeason = basePoints + streakBonus
  if (lossStreak >= lossProtectAfter) {
    totalSeason = Math.floor(totalSeason * lossMultiplier)
  }
  if (referralTier >= 10) {
    totalSeason = Math.floor(totalSeason * 1.05)
  }
  const totalRedeem = Math.floor(totalSeason * redeemRatio)
  let coinsReturn = 0
  let freeWinCoins = 0
  if (useFree) {
    freeWinCoins = 15
  } else if (stakeCoins > 0) {
    coinsReturn = stakeCoins * 2
  }
  return {
    season_points: totalSeason,
    redeem_points: totalRedeem,
    coins_returned: coinsReturn,
    free_win_coins: freeWinCoins,
    streak_bonus: streakBonus,
  }
}

export function formatPredictPreviewText(w: PredictPreviewResult): string {
  const parts = [`猜中 +${w.season_points} 累计分`, `+${w.redeem_points} 可用分`]
  if (w.coins_returned) parts.push(`返 ${w.coins_returned} 币`)
  if (w.free_win_coins) parts.push(`+${w.free_win_coins} 币`)
  if (w.streak_bonus) parts.push(`(含连胜 +${w.streak_bonus})`)
  return parts.join(' · ')
}
