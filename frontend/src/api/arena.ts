import { apiClient } from './client'

export interface ArenaStanding {
  team_id: number | null
  rank: number | null
  total_members: number
  battalion_points: number
  gap_to_prev: number
  arena_tier: string
  tier_label: string
  star_contributions?: { player_id: number; player_name: string; heat: number }[]
}

export interface ArenaTeamRankEntry {
  user_id: number
  nickname: string
  battalion_points: number
  arena_tier: string
  tier_label: string
}

export interface MatchArena {
  match_id: number
  team1_name: string
  team2_name: string
  status: string
  home: { team_id: number | null; name: string; power: number }
  away: { team_id: number | null; name: string; power: number }
  leader_name: string | null
  lead_points: number
  user_contributed: boolean
  frozen: boolean
}

export interface StarHeatRow {
  player_id: number
  player_name: string
  team_id?: number
  my_heat?: number
  global_heat?: number
  can_boost_today?: boolean
}

export interface MatchdayGoal {
  active: boolean
  team_id?: number
  team_name?: string | null
  progress: number
  goals: number[]
  goal_titles?: string[]
  tier_reached: number
  rewards_coins?: number[]
  my_titles?: string[]
  rally_done_today?: boolean
}

export interface TodayMatchRow {
  match_id: number
  match_date: string
  match_time: string | null
  team1_name: string
  team2_name: string
  team1_id: number | null
  team2_id: number | null
  team1_affiliation: 'primary' | 'secondary' | 'neutral'
  team2_affiliation: 'primary' | 'secondary' | 'neutral'
  team1_underdog_bonus?: number
  team2_underdog_bonus?: number
  can_cheer: boolean
  user_cheered: boolean
  user_cheer_team_id: number | null
  has_prediction?: boolean
  predict_combo_pending?: boolean
  predict_combo_after_cheer?: boolean
  cheer_block_reason: string | null
  arena: {
    home_power: number
    away_power: number
    leader_name: string | null
    lead_points: number
  }
}

export interface ArenaQuickStats {
  today_matches: number
  today_cheerable: number
  spot_remaining: number
  combo_opportunities: number
}

export interface SpotCheerStatus {
  daily_limit: number
  used_today: number
  remaining: number
  cost: number
  battalion_per_cheer: number
  slogans: string[]
  teams_today: { team_id: number; team_name: string }[]
}

export async function getArenaOverview() {
  const { data } = await apiClient.get('/api/arena/overview')
  return data as {
    standing: ArenaStanding
    next_match_arena: MatchArena | null
    my_stars: StarHeatRow[]
    matchday_goal: MatchdayGoal
    matchday_goal_secondary: MatchdayGoal
    spot_cheer: SpotCheerStatus
    card_boost_pct: number
    quick_stats: ArenaQuickStats
  }
}

export async function getTodayMatches() {
  const { data } = await apiClient.get<TodayMatchRow[]>('/api/arena/today-matches')
  return data
}

export async function getArenaTeamRank(teamId?: number, period = 'season') {
  const { data } = await apiClient.get<ArenaTeamRankEntry[]>('/api/arena/team-rank', {
    params: { team_id: teamId, period },
  })
  return data
}

export async function getMatchArena(matchId: number) {
  const { data } = await apiClient.get<MatchArena>(`/api/arena/match/${matchId}`)
  return data
}

export async function getStarHeat(scope: 'my' | 'global' = 'global', limit = 20) {
  const { data } = await apiClient.get<{ scope: string; rows: StarHeatRow[] }>('/api/arena/star-heat', {
    params: { scope, limit },
  })
  return data
}

export async function getStarAccuracy(playerId?: number) {
  const { data } = await apiClient.get('/api/arena/star-accuracy', { params: { player_id: playerId } })
  return data
}

export async function getMatchdayGoal(teamId?: number) {
  const { data } = await apiClient.get<MatchdayGoal>('/api/arena/matchday-goal', {
    params: teamId ? { team_id: teamId } : undefined,
  })
  return data
}

export async function boostStar(playerId: number) {
  const { data } = await apiClient.post('/api/arena/boost/star', { player_id: playerId })
  return data
}

export async function boostCheerExtra(matchId: number) {
  const { data } = await apiClient.post('/api/arena/boost/cheer-extra', { match_id: matchId })
  return data
}

export async function matchdayRally(teamId?: number) {
  const { data } = await apiClient.post<{
    collectible_drop?: import('./collectible').CollectibleDropResult | null
  }>('/api/arena/boost/matchday-rally', teamId != null ? { team_id: teamId } : {})
  return data
}

export async function getSpotCheerStatus() {
  const { data } = await apiClient.get<SpotCheerStatus>('/api/arena/spot-cheer')
  return data
}

export async function submitSpotCheer(teamId: number, sloganIndex: number) {
  const { data } = await apiClient.post<{
    fan_coins: number
    battalion_added: number
    slogan: string
    spot_cheer: SpotCheerStatus
  }>('/api/arena/spot-cheer', { team_id: teamId, slogan_index: sloganIndex })
  return data
}

export async function getTeamSupporters(teamId: number, period = 'season') {
  const { data } = await apiClient.get<ArenaTeamRankEntry[]>('/api/arena/team-supporters', {
    params: { team_id: teamId, period },
  })
  return data
}
