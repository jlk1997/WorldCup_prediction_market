const STORAGE_KEY = 'duel_staged_picks'

export function readStagedDuelPicks(): number[] {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw) as unknown
    if (!Array.isArray(parsed)) return []
    return parsed.map((x) => Number(x)).filter((n) => Number.isFinite(n) && n > 0).slice(0, 3)
  } catch {
    return []
  }
}

export function writeStagedDuelPicks(ids: number[]) {
  sessionStorage.setItem(STORAGE_KEY, JSON.stringify(ids.slice(0, 3)))
}

export function toggleStagedDuelPick(userCardId: number): number[] {
  const cur = readStagedDuelPicks()
  const idx = cur.indexOf(userCardId)
  if (idx >= 0) {
    cur.splice(idx, 1)
  } else if (cur.length < 3) {
    cur.push(userCardId)
  }
  writeStagedDuelPicks(cur)
  return cur
}

export function clearStagedDuelPicks() {
  sessionStorage.removeItem(STORAGE_KEY)
}
