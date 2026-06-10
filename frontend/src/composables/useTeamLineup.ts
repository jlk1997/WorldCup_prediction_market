import type { LineupPlayer } from '@/components/TeamLineupColumn.vue'

const POS_ORDER: Record<string, number> = { 门将: 0, 后卫: 1, 中场: 2, 前锋: 3 }

export function teamNamesMatch(a: string | undefined, b: string | undefined): boolean {
  if (!a || !b) return false
  const x = a.trim()
  const y = b.trim()
  if (x === y) return true
  return x.includes(y) || y.includes(x)
}

export function sortPlayers(players: LineupPlayer[]): LineupPlayer[] {
  return [...players].sort((a, b) => {
    const pa = POS_ORDER[a.position ?? ''] ?? 9
    const pb = POS_ORDER[b.position ?? ''] ?? 9
    if (pa !== pb) return pa - pb
    return (b.overall_rating ?? 0) - (a.overall_rating ?? 0)
  })
}

export function splitLineup(players: LineupPlayer[]): { lineup: LineupPlayer[]; bench: LineupPlayer[] } {
  const sorted = sortPlayers(players)
  const flagged = sorted.filter((p) => p.is_starter)
  if (flagged.length >= 7) {
    const names = new Set(flagged.map((p) => p.name))
    return { lineup: flagged, bench: sorted.filter((p) => !names.has(p.name)) }
  }
  return { lineup: sorted.slice(0, 11), bench: sorted.slice(11) }
}

export function computeTopPlayer(players: LineupPlayer[]): LineupPlayer | null {
  const pool = players.filter((p) => p.position !== '教练' && p.overall_rating)
  if (!pool.length) return null
  return pool.reduce((best, cur) =>
    (best.overall_rating ?? 0) >= (cur.overall_rating ?? 0) ? best : cur,
  )
}

export function playersFromTeamData(data: { players?: LineupPlayer[] } | null): LineupPlayer[] {
  if (!data?.players?.length) return []
  return data.players.filter((p) => p.position !== '教练')
}

export function resolveFocusSides(
  team1: string,
  team2: string,
  mainTeamName: string | null,
): { left: string; right: string } {
  const t1 = team1.trim()
  const t2 = team2.trim()
  if (mainTeamName) {
    if (teamNamesMatch(t2, mainTeamName) && !teamNamesMatch(t1, mainTeamName)) {
      return { left: t2, right: t1 }
    }
    if (teamNamesMatch(t1, mainTeamName)) {
      return { left: t1, right: t2 }
    }
  }
  return { left: t1, right: t2 }
}

export function panelTag(
  teamName: string,
  matchTeam1: string,
  mainTeamName: string | null,
  isMainMatch: boolean,
): { tagLabel: string; tagClass: string } {
  if (mainTeamName && teamNamesMatch(teamName, mainTeamName) && isMainMatch) {
    return { tagLabel: '我的主队', tagClass: 'main' }
  }
  if (teamName === matchTeam1) return { tagLabel: '主场', tagClass: 'home' }
  return { tagLabel: '客场', tagClass: 'away' }
}
