import { apiClient } from './client'

export interface ReferralLeaderboardRow {
  rank: number
  user_id: number
  nickname: string
  score: number
}

export interface ReferralLeaderboardResponse {
  rows: ReferralLeaderboardRow[]
  period_label: string
  my_rank: number | null
  my_score: number
  week_ends_at?: string | null
  seconds_until_settle?: number | null
}

export interface ReferralPreview {
  valid: boolean
  inviter_nickname?: string
  register_invitee_bonus?: number
  total_new_user_coins?: number
  invite_code?: string
}

export interface ReferralLoginInfo {
  invite_code: string
  is_new: boolean
  bound_inviter?: boolean
  bound?: boolean
  inviter_nickname?: string | null
  invite_code_attempted?: string | null
  invite_accepted?: boolean | null
  message?: string | null
}

export interface InviteeJourneyStep {
  key: string
  label: string
  done: boolean
  reward_coins?: number
  reward_battalion?: number
  action?: string
}

export interface InviteeJourney {
  inviter_nickname: string
  steps: InviteeJourneyStep[]
  next_step?: { key: string; label: string; action?: string } | null
  days_left_active?: number | null
}

export interface RecruitmentTier {
  count: number
  title: string
  perk: string
  unlocked: boolean
}

export interface ReferralMe {
  invite_code: string
  invite_link: string
  invited_total: number
  total_invites: number
  effective_invites: number
  coins_earned_season: number
  season_coins_earned: number
  season_cap_near: boolean
  week_score: number
  week_key: string
  weekly_rank?: { rank: number | null; score: number }
  next_tier?: { count: number; title: string; remaining: number } | null
  recruitment_tiers?: RecruitmentTier[]
  same_team_invites?: number
  invitee_journey?: InviteeJourney | null
  seconds_until_weekly_settle?: number | null
}

export interface ReferralInvite {
  invitee_id: number
  nickname: string
  profile_completed: boolean
  inviter_coins_earned: number
  milestones: string[]
  same_team: boolean
  next_hint?: string | null
  nudge_text?: string | null
}

export interface ReferralMilestoneRule {
  key: string
  label?: string
  inviter_coins: number
  invitee_coins: number
  inviter_battalion: number
  invitee_battalion: number
}

export interface ReferralRules {
  summary: string
  milestones: ReferralMilestoneRule[]
  season_coin_cap?: number
  weekly: {
    settle_top_n: number
    rank_rewards: Array<{ rank: number; points: number; coins: number }>
  }
}

export async function previewReferralCode(code: string) {
  const { data } = await apiClient.get<ReferralPreview>('/api/referral/preview', {
    params: { code: code.trim().toUpperCase() },
  })
  return data
}

export async function getReferralLeaderboard() {
  const { data } = await apiClient.get<ReferralLeaderboardResponse>('/api/referral/leaderboard')
  return data
}

export async function getReferralMe() {
  const { data } = await apiClient.get<ReferralMe>('/api/referral/me')
  return data
}

export async function getReferralInvites() {
  const { data } = await apiClient.get<ReferralInvite[]>('/api/referral/invites')
  return data
}

export async function getReferralRules() {
  const { data } = await apiClient.get<ReferralRules>('/api/referral/rules')
  return data
}
