/** Normalized pitch coordinates (0-100) for 4-3-3 */

export interface PitchDot {
  name: string
  x: number
  y: number
  side: 'home' | 'away'
}

const SLOT_433: Record<string, number[]> = {
  门将: [50, 8],
  后卫: [20, 22],
  后卫2: [40, 18],
  后卫3: [60, 18],
  后卫4: [80, 22],
  中场: [30, 42],
  中场2: [50, 38],
  中场3: [70, 42],
  前锋: [25, 68],
  前锋2: [50, 72],
  前锋3: [75, 68],
}

export function buildFormationDots(
  players: { name: string; position?: string | null; is_starter?: boolean }[],
  side: 'home' | 'away'
): PitchDot[] {
  const starters = players.filter((p) => p.is_starter && p.position !== '教练').slice(0, 11)
  const buckets: Record<string, number> = { 门将: 0, 后卫: 0, 中场: 0, 前锋: 0 }
  const dots: PitchDot[] = []

  for (const p of starters) {
    const pos = p.position || '中场'
    const base = pos.startsWith('门') ? '门将' : pos.startsWith('后') ? '后卫' : pos.startsWith('前') ? '前锋' : '中场'
    buckets[base] = (buckets[base] || 0) + 1
    const key = buckets[base] > 1 && base !== '门将' ? `${base}${buckets[base]}` : base
    const slotKey = key in SLOT_433 ? key : base
    const [x, y] = SLOT_433[slotKey] || SLOT_433['中场2']
    const flipY = side === 'away' ? 100 - y : y
    dots.push({ name: p.name, x, y: flipY, side })
  }
  return dots
}
