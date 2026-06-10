import type { ReferralMilestoneRule } from '../api/referral'

const FALLBACK_LABELS: Record<string, string> = {
  registered: '好友注册成功',
  profile_done: '好友完善球迷档案',
  first_action: '好友完成首次竞猜或助威',
  active_7d: '好友注册后第 7 天仍活跃签到',
  same_team: '好友与你选择相同主队',
}

function rewardParts(m: ReferralMilestoneRule): string[] {
  const parts: string[] = []
  if (m.inviter_coins > 0) parts.push(`你 +${m.inviter_coins} 球迷币`)
  if (m.invitee_coins > 0) parts.push(`好友 +${m.invitee_coins} 球迷币`)
  if (m.inviter_battalion > 0) parts.push(`你 +${m.inviter_battalion} 军团贡献`)
  if (m.invitee_battalion > 0) parts.push(`好友 +${m.invitee_battalion} 军团贡献`)
  return parts
}

export function milestoneLabel(m: ReferralMilestoneRule): string {
  return m.label || FALLBACK_LABELS[m.key] || m.key
}

export function formatMilestoneReward(m: ReferralMilestoneRule): string {
  const parts = rewardParts(m)
  return parts.length ? parts.join(' · ') : '无额外奖励'
}
