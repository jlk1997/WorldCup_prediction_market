/** 海报展示用昵称：过滤纯数字 ID / 手机号，避免海报上出现冷冰冰的一串数字 */
export function posterDisplayName(raw?: string | null): string {
  const s = (raw || '').trim()
  if (!s) return '球友'
  if (/^\d+$/.test(s)) return '球友'
  if (/^1\d{10}$/.test(s)) return '球友'
  const emailLocal = s.includes('@') ? s.split('@')[0]?.trim() : ''
  if (emailLocal && emailLocal !== s) {
    if (/^\d+$/.test(emailLocal)) return '球友'
    return emailLocal.length > 12 ? `${emailLocal.slice(0, 10)}…` : emailLocal
  }
  if (s.length > 14) return `${s.slice(0, 12)}…`
  return s
}

export function posterInitial(name: string): string {
  const n = posterDisplayName(name)
  if (n === '球友') return '⚽'
  return n.charAt(0).toUpperCase()
}
