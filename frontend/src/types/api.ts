export interface TeamBrief {
  id: number
  name: string
  country_code: string
  fifa_ranking: number | null
  group_name: string | null
  coach: string | null
}

export interface ScheduleItem {
  group: string
  date: string
  time: string
  team1: string
  team2: string
  stadium: string
  id?: number
  status?: string
  home_score?: number | null
  away_score?: number | null
  minute?: number | null
  period?: string | null
  is_live?: boolean
  events?: MatchEvent[] | unknown
}

export interface MatchEvent {
  minute?: number | null
  extra?: number | null
  type?: string | null
  detail?: string | null
  team?: string | null
  player?: string | null
  assist?: string | null
}

export interface LiveMatch extends ScheduleItem {
  events?: MatchEvent[] | unknown
  live_updated_at?: string
}

export interface StatsOverview {
  teams: number
  matches: number
  live_matches: number
  finished_matches: number
  news_articles: number
}

export interface NewsArticle {
  id: number
  title: string
  url: string | null
  source: string | null
  published_at: string | null
  summary: string | null
  lang?: string
  team_tags?: string[] | null
}

export interface AgentStep {
  agent: string
  action: string
  output?: unknown
}

export interface ReasoningTraceStep {
  agent: string
  action: string
  summary: string
}

export interface BettingGuide {
  recommended_pick: '1' | 'X' | '2'
  pick_label: string
  pick_probability: number
  confidence_tier: string
  predicted_score: string
  total_goals_hint: string
  card_penalty_hint: string
  stake_suggestion: string
  one_line_verdict: string
  rationale: string
  watch_points?: string[]
  key_risks?: string[]
  model_confidence: number
  win_probability: { team1: number; draw: number; team2: number }
}

export interface AgentReport {
  summary: string
  predicted_score: string
  win_probability: { team1: number; draw: number; team2: number }
  key_factors: string[]
  injury_impact: string
  tactical_edge: string
  betting_notes: string
  confidence: number
  sources: { type: string; ref?: string; url?: string }[]
  agent_steps?: AgentStep[]
  reasoning_trace?: ReasoningTraceStep[]
  betting_guide?: BettingGuide
  watch_points?: string[]
  mode?: string
  news_digest?: string
  scenario_analysis?: string
  critic_notes?: string
  critic_issues?: string[]
  tactical_brief?: { brief?: string; key_matchups?: string[]; team1_edge?: string; team2_edge?: string }
  score?: string
  total_goals?: string
  red_cards?: string
  penalties?: string
  advice?: string
  validation_warnings?: string[]
  live_context?: string | null
}

export interface AgentAnalyzeResponse {
  status: string
  cached: boolean
  run_id?: number
  data: AgentReport
  validation_warnings?: string[]
}

export interface AgentInsight {
  has_data: boolean
  run_id?: number | null
  summary?: string
  predicted_score?: string
  confidence?: number | null
  win_probability?: { team1: number; draw: number; team2: number } | null
  betting_pick?: string | null
  pick_label?: string | null
  mode?: string | null
  created_at?: string | null
}

export interface PlayerBrief {
  id: number
  name: string
  position: string | null
  age: number | null
  jersey_number?: number | null
  is_key_player: boolean
  team_name?: string | null
}

export interface PlayerStats {
  [key: string]: number
}

export interface PlayerDetailed {
  id: number
  name: string
  age: number | null
  position: string | null
  club: string | null
  is_starter: boolean
  description: string | null
  height: number | null
  weight: number | null
  preferred_foot: string | null
  birth_date: string | null
  overall_rating: number | null
  stats: PlayerStats | null
  honors: string[] | null
  transfers: unknown[] | null
  injuries: unknown[] | null
  injury_status?: string | null
  injury_detail?: string | null
  market_value?: string | null
  form_rating?: number | null
}

export interface TeamDetail extends Omit<TeamBrief, 'coach'> {
  total_value: string | null
  avg_age: number | null
  coach: string | null
  formation: string | null
  logo_url: string | null
  founded: string | null
  city: string | null
  stadium: string | null
  capacity: string | null
  players: PlayerDetailed[]
}

export interface TeamDetailResponse {
  status: string
  data: TeamDetail
}

export interface AnalysisData {
  score: string
  total_goals: string
  red_cards: string
  penalties: string
  advice: string
}

export interface AnalysisResponse {
  status: string
  cached: boolean
  data: AnalysisData
}

export interface ApiErrorBody {
  status: 'error'
  message: string
  code?: string
  retry_after_sec?: number
  details?: unknown
}
