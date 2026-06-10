/** Client-side fallback when API returns legacy raw summaries. */

export function cleanNewsSummary(raw: string | null | undefined, maxLen = 220): string {
  if (!raw) return ''
  let text = raw
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&amp;/g, '&')
  text = text.replace(/<(script|style)[^>]*>[\s\S]*?<\/\1>/gi, ' ')
  text = text.replace(/<img[^>]+alt=["']([^"']+)["'][^>]*>/gi, ' $1 ')
  text = text.replace(/<[^>]+>/g, ' ')
  text = text.replace(/https?:\/\/\S+/g, ' ')
  text = text.replace(/\s+/g, ' ').trim()
  if (text.length > maxLen) text = `${text.slice(0, maxLen - 1)}…`
  return text
}

export function newsSummaryDisplay(
  summary: string | null | undefined,
  hasUrl: boolean,
): string {
  const clean = cleanNewsSummary(summary)
  if (clean) return clean
  return hasUrl ? '本文为图文资讯，点击标题查看详情与配图' : '暂无文字摘要'
}
