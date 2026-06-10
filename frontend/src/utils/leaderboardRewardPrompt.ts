const STORAGE_KEY = 'wc_leaderboard_reward_dismiss_date'

function localDateKey(d = new Date()): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

export function shouldShowLeaderboardRewardPrompt(): boolean {
  try {
    return localStorage.getItem(STORAGE_KEY) !== localDateKey()
  } catch {
    return true
  }
}

export function dismissLeaderboardRewardForToday(): void {
  try {
    localStorage.setItem(STORAGE_KEY, localDateKey())
  } catch {
    /* ignore quota / private mode */
  }
}
