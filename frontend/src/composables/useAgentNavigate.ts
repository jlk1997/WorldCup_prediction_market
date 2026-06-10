import { useRouter } from 'vue-router'
import type { LiveMatch, ScheduleItem } from '@/types/api'

export type AgentMode = 'pre_match' | 'live' | 'post_match'

export function resolveAgentMode(match: Pick<ScheduleItem | LiveMatch, 'is_live' | 'status'>): AgentMode {
  if (match.is_live || match.status === 'live') return 'live'
  if (match.status === 'finished') return 'post_match'
  return 'pre_match'
}

export function useAgentNavigate() {
  const router = useRouter()

  function goAgent(
    team1: string,
    team2: string,
    options?: { auto?: boolean; mode?: AgentMode; forceRefresh?: boolean },
  ) {
    const query: Record<string, string> = {}
    if (options?.auto) query.auto = '1'
    if (options?.mode) query.mode = options.mode
    if (options?.forceRefresh) query.refresh = '1'
    router.push({
      path: `/agent/${encodeURIComponent(team1)}/${encodeURIComponent(team2)}`,
      query: Object.keys(query).length ? query : undefined,
    })
  }

  function goAgentFromMatch(
    match: Pick<ScheduleItem | LiveMatch, 'team1' | 'team2' | 'is_live' | 'status'>,
    options?: { auto?: boolean; forceRefresh?: boolean },
  ) {
    if (!match.team1 || !match.team2) return
    goAgent(match.team1, match.team2, {
      auto: options?.auto,
      forceRefresh: options?.forceRefresh,
      mode: resolveAgentMode(match),
    })
  }

  function goMatchDetail(match: Pick<ScheduleItem | LiveMatch, 'id'>) {
    if (match.id) router.push(`/live/match/${match.id}`)
  }

  function agentButtonLabel(match: Pick<ScheduleItem | LiveMatch, 'is_live' | 'status'>): string {
    const mode = resolveAgentMode(match)
    if (mode === 'live') return '赛中 AI'
    if (mode === 'post_match') return '赛后复盘'
    return 'AI 分析'
  }

  return { goAgent, goAgentFromMatch, goMatchDetail, agentButtonLabel, resolveAgentMode }
}
