import type { PassReward } from '@/api/collectionPass'

const CARD_NAMES: Record<string, string> = {
  pass_limited_rookie: '手册 · 新秀徽章',
  pass_limited_veteran: '手册 · 老将勋章',
  pass_limited_champion: '手册 · 冠军奖杯',
  event_limited_spotlight: '活动 · 黑马之夜',
  event_limited_golden_boot: '活动 · 金靴候选',
}

const RARITY_SHARD: Record<string, string> = {
  common: '普通',
  rare: '稀有',
  epic: '史诗',
  legend: '传奇',
}

const MILESTONE_LEVELS = new Set([5, 10, 20, 30, 40])

export function isPassMilestone(level: number): boolean {
  return MILESTONE_LEVELS.has(level)
}

export function formatPassReward(r: PassReward): { primary: string; secondary?: string; isCard?: boolean } {
  if (r.card_code) {
    return {
      primary: CARD_NAMES[r.card_code] || r.card_code,
      secondary: '手册限定卡',
      isCard: true,
    }
  }
  const parts: string[] = []
  if (r.fan_coins) parts.push(`+${r.fan_coins} 球迷币`)
  if (r.redeem_points) parts.push(`+${r.redeem_points} 可用积分`)
  if (r.shards) {
    const s = Object.entries(r.shards)
      .map(([k, v]) => `${RARITY_SHARD[k] || k}碎片 ×${v}`)
      .join(' · ')
    if (s) parts.push(s)
  }
  if (r.avatar_frame) parts.push('专属头像框')
  if (r.theme_key) parts.push('全站主题')
  if (r.badge_title) parts.push(`徽章「${r.badge_title}」`)
  return { primary: parts.join(' · ') || '—' }
}

export const PASS_MILESTONE_CARDS = [
  { level: 5, code: 'pass_limited_rookie', label: '新秀徽章' },
  { level: 20, code: 'pass_limited_veteran', label: '老将勋章' },
  { level: 40, code: 'pass_limited_champion', label: '冠军奖杯' },
] as const

export function formatSeasonEnds(iso?: string | null): string | null {
  if (!iso) return null
  try {
    return new Date(iso).toLocaleDateString('zh-CN', { month: 'long', day: 'numeric' })
  } catch {
    return null
  }
}
