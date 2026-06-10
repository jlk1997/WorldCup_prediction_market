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
  progress: number
  goals: number[]
  goal_titles?: string[]
  tier_reached: number
  rewards_coins?: number[]
  my_titles?: string[]
}

export async function getArenaOverview() {
  const { data } = await apiClient.get('/api/arena/overview')
  return data as {
    standing: ArenaStanding
    next_match_arena: MatchArena | null
    my_stars: StarHeatRow[]
    matchday_goal: MatchdayGoal
  }
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

export async function getMatchdayGoal() {
  const { data } = await apiClient.get<MatchdayGoal>('/api/arena/matchday-goal')
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

export async function matchdayRally() {
  const { data } = await apiClient.post('/api/arena/boost/matchday-rally')
  return data
}
