import { apiClient } from './client'

export interface TeamBrief {
  id: number
  name: string
  group_name: string | null
  country_code: string | null
  logo_url: string | null
  fifa_ranking: number | null
}

export interface PlayerBrief {
  id: number
  name: string
  position: string | null
  team_id: number
  is_starter: boolean
  overall_rating: number | null
}

export interface ProfileStatus {
  profile_completed: boolean
  main_team: TeamBrief | null
  secondary_team: TeamBrief | null
  players: { id: number; name: string; position: string | null; team_id: number; sort_order: number }[]
  missing_steps: string[]
  fan_cheers_total: number
  fan_level: number
}

export interface Recommendations {
  next_main_match: MatchBrief | null
  next_sub_match: MatchBrief | null
  star_player_matches: { player_name: string; match_id: number; team: string; team1: string; team2: string }[]
  cta: { type: string; label: string; path: string }[]
  fan_identity: {
    main_team: TeamBrief | null
    secondary_team: TeamBrief | null
    players: ProfileStatus['players']
    fan_level: number
    cheers_total: number
    profile_completed: boolean
  } | null
}

export interface MatchBrief {
  id: number
  team1: string | null
  team2: string | null
  date: string | null
  time: string | null
  group: string | null
  status: string
  can_predict: boolean
  can_cheer: boolean
  hours_until?: number | null
}

export async function getProfileStatus() {
  const { data } = await apiClient.get<ProfileStatus>('/api/profile/status')
  return data
}

export async function getTeams() {
  const { data } = await apiClient.get<TeamBrief[]>('/api/profile/teams')
  return data
}

export async function getPlayersForTeams(teamIds: number[]) {
  const { data } = await apiClient.get<PlayerBrief[]>('/api/profile/players', {
    params: { team_ids: teamIds.join(',') },
  })
  return data
}

export async function setupProfile(payload: {
  main_team_id: number
  secondary_team_id?: number | null
  player_ids: number[]
}) {
  const { data } = await apiClient.put<ProfileStatus>('/api/profile/setup', payload)
  return data
}

export async function patchProfile(payload: {
  main_team_id?: number
  secondary_team_id?: number | null
  player_ids?: number[]
}) {
  const { data } = await apiClient.patch<ProfileStatus>('/api/profile', payload)
  return data
}

export async function getRecommendations() {
  const { data } = await apiClient.get<Recommendations>('/api/profile/recommendations')
  return data
}

export async function getCheerStatus(matchId: number) {
  const { data } = await apiClient.get(`/api/game/cheer/${matchId}`)
  return data
}

export async function submitCheer(matchId: number, teamId: number) {
  const { data } = await apiClient.post('/api/game/cheer', { match_id: matchId, team_id: teamId })
  return data
}

export async function getQuizToday() {
  const { data } = await apiClient.get('/api/game/quiz/today')
  return data
}

export async function answerQuiz(answerIndex: number) {
  const { data } = await apiClient.post('/api/game/quiz/answer', { answer_index: answerIndex })
  return data
}

export async function getFanCard() {
  const { data } = await apiClient.get('/api/game/fan-card')
  return data
}

export async function getTeamContribution(teamId?: number) {
  const { data } = await apiClient.get('/api/game/team-contribution', {
    params: teamId ? { team_id: teamId } : {},
  })
  return data
}
