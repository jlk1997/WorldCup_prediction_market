/** Parse kickoff from schedule date/time (ISO or 中文日期). Times are stored in Asia/Shanghai. */

const CN_DATE = /^(\d{4})年(\d{1,2})月(\d{1,2})日$/
/** Must match backend `bsd_timezone` (default Asia/Shanghai). */
const SCHEDULE_TZ_OFFSET = '+08:00'

function pad2(n: number) {
  return String(n).padStart(2, '0')
}

export function parseMatchKickoff(date?: string | null, time?: string | null): Date | null {
  if (!date) return null
  const rawDate = date.trim()
  const rawTime = (time || '00:00').trim()
  const [hhRaw, mmRaw] = rawTime.split(':')
  const hh = pad2(Number(hhRaw) || 0)
  const mm = pad2(Number(mmRaw) || 0)

  const cn = CN_DATE.exec(rawDate)
  if (cn) {
    const iso = `${cn[1]}-${pad2(Number(cn[2]))}-${pad2(Number(cn[3]))}T${hh}:${mm}:00${SCHEDULE_TZ_OFFSET}`
    const parsed = new Date(iso)
    return Number.isNaN(parsed.getTime()) ? null : parsed
  }

  if (/^\d{4}-\d{2}-\d{2}/.test(rawDate)) {
    const iso = `${rawDate.slice(0, 10)}T${hh}:${mm}:00${SCHEDULE_TZ_OFFSET}`
    const parsed = new Date(iso)
    return Number.isNaN(parsed.getTime()) ? null : parsed
  }
  return null
}

export function isMatchPastKickoff(
  m: { date?: string | null; time?: string | null },
  closeMinutes = 30,
): boolean {
  const kick = parseMatchKickoff(m.date, m.time)
  if (!kick) return false
  return kick.getTime() - closeMinutes * 60_000 <= Date.now()
}

export function isMatchStaleScheduled(m: {
  status?: string | null
  is_live?: boolean
  date?: string | null
  time?: string | null
}): boolean {
  const st = m.status || 'scheduled'
  if (st !== 'scheduled' || m.is_live) return false
  return isMatchPastKickoff(m)
}

export function isMatchPredictable(m: {
  status?: string | null
  is_live?: boolean
  date?: string | null
  time?: string | null
}): boolean {
  if (m.status === 'finished' || m.status === 'live' || m.is_live) return false
  if (isMatchPastKickoff(m)) return false
  return true
}

export function formatMatchScore(
  home?: number | null,
  away?: number | null,
  opts?: { status?: string | null; isLive?: boolean },
): string {
  const st = opts?.status
  const live = opts?.isLive || st === 'live'
  if (st === 'finished' || live) {
    return `${home ?? 0} : ${away ?? 0}`
  }
  if (home != null && away != null) return `${home} : ${away}`
  return '-'
}

export function matchStatusLabel(m: {
  status?: string | null
  is_live?: boolean
  minute?: number | null
  date?: string | null
  time?: string | null
}): string {
  if (m.status === 'finished') return '已结束'
  if (m.is_live || m.status === 'live') return `${m.minute ?? ''}' LIVE`.trim()
  if (isMatchStaleScheduled(m)) {
    const kick = parseMatchKickoff(m.date, m.time)
    if (kick && Date.now() - kick.getTime() > 48 * 3_600_000) {
      return '数据源暂无比分'
    }
    return '比分同步中'
  }
  return [m.date, m.time].filter(Boolean).join(' ')
}
