import type { Product, OrderDetail } from '../api/commerce'

export interface EntitlementUserLike {
  has_season_pass?: boolean
  has_active_season_pass?: boolean
  season_pass_until?: string | null
  avatar_frame?: string | null
  theme_key?: string | null
  nickname?: string
}

const FRAME_LABELS: Record<string, string> = {
  gold_wc: '头像金框',
  silver_wc: '头像银框',
  referral_squad: '召友头像框',
}

const THEME_LABELS: Record<string, string> = {
  team_spirit: '全站主题色',
  gold_wc: '世界杯金主题',
}

export function avatarFrameLabel(frame: string | null | undefined): string | null {
  if (!frame) return null
  return FRAME_LABELS[frame] ?? '专属头像框'
}

export function themeKeyLabel(key: string | null | undefined): string | null {
  if (!key) return null
  return THEME_LABELS[key] ?? '全站主题'
}

export function avatarFrameClass(frame: string | null | undefined): string {
  if (frame === 'gold_wc') return 'frame-gold_wc'
  if (frame === 'silver_wc') return 'frame-silver_wc'
  if (frame === 'referral_squad') return 'frame-referral_squad'
  return frame ? 'frame-generic' : ''
}

export function hasActiveSeasonPass(user: EntitlementUserLike | null | undefined): boolean {
  if (!user) return false
  if (user.has_active_season_pass != null) return user.has_active_season_pass
  if (!user.has_season_pass || !user.season_pass_until) return false
  return new Date(user.season_pass_until).getTime() > Date.now()
}

export function seasonPassBenefitLines(): string[] {
  return [
    '竞猜累计积分 1.2 倍',
    '每日 +50 球迷币',
    '每日额外 3 次免费 AI 分析',
  ]
}

export function buildProductGrantPreview(product: Product): string[] {
  const lines: string[] = []
  if (product.coins_grant) lines.push(`+${product.coins_grant} 球迷币`)
  if (product.grant_season_pass_days) {
    lines.push(`赛季通行证 ${product.grant_season_pass_days} 天`)
    lines.push(...seasonPassBenefitLines())
  }
  if (product.product_type === 'cosmetic') {
    lines.push('头像金框', '全站主题色')
  }
  if (product.product_type === 'season_pass' && !product.grant_season_pass_days) {
    lines.push(...seasonPassBenefitLines())
  }
  return lines
}

export function cosmeticPreviewFromProduct(product: Product | null) {
  if (!product) return { avatarFrame: null as string | null, themeKey: null as string | null }
  if (product.product_type === 'cosmetic') {
    return { avatarFrame: 'gold_wc', themeKey: 'team_spirit' }
  }
  return { avatarFrame: null, themeKey: null }
}

export function buildOrderGrantSummary(order: OrderDetail): string[] {
  if (order.grant_summary?.length) return order.grant_summary
  const lines: string[] = []
  if (order.coins_grant) lines.push(`+${order.coins_grant} 球迷币`)
  if (order.grant_season_pass_days) {
    lines.push(`赛季通行证 ${order.grant_season_pass_days} 天`)
    lines.push(...seasonPassBenefitLines())
  }
  if (order.product_type === 'cosmetic') {
    lines.push('头像金框', '全站主题色')
  }
  return lines
}

export function formatPassUntil(iso: string | null | undefined): string {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleDateString('zh-CN')
  } catch {
    return iso
  }
}
