import QRCode from 'qrcode'
import { posterDisplayName, posterInitial } from './sharePosterDisplayName'

export type SharePosterVariant = 'invite' | 'predict' | 'profile' | 'card' | 'set_complete' | 'collectible'
export type SharePosterRarity = 'common' | 'rare' | 'epic' | 'legend'

export interface SharePosterOptions {
  variant?: SharePosterVariant
  /** 原始昵称，内部会 sanitize */
  displayName?: string
  title?: string
  subtitle: string
  statsLine?: string
  footer?: string
  qrUrl?: string
  /** 顶部角标，如「注册送100币」 */
  badge?: string
  /** predict：我押的内容 */
  pickHighlight?: string
  /** collectible / card 海报 */
  cardImageUrl?: string
  playerName?: string
  rarity?: SharePosterRarity
  star?: number
  owned?: boolean
  chainMinted?: boolean
  chainHashShort?: string
  inviteCode?: string
  aiHookLine?: string
  layoutVersion?: 'v1' | 'v2'
  showAiPill?: boolean
}

export const RARITY_POSTER_STYLES: Record<
  SharePosterRarity,
  { border: string; glow: string; label: string; badgeBg: string }
> = {
  common: { border: '#9eb0c8', glow: 'rgba(158,176,200,0.25)', label: '普通', badgeBg: '#6b7d96' },
  rare: { border: '#4da6ff', glow: 'rgba(77,166,255,0.35)', label: '稀有', badgeBg: '#2d6fbf' },
  epic: { border: '#b57bff', glow: 'rgba(181,123,255,0.35)', label: '史诗', badgeBg: '#7a45b8' },
  legend: { border: '#e8c547', glow: 'rgba(232,197,71,0.45)', label: '传奇', badgeBg: '#a8841a' },
}

export const DEFAULT_AI_HOOK = '免费 AI 赛事快览 · 猜中掉落球星数字藏品'

const W = 600
const H = 1000

const C = {
  bgTop: '#0a1628',
  bgMid: '#12243d',
  bgBottom: '#0d1a12',
  gold: '#e8c547',
  goldDim: '#c9a227',
  green: '#3dd68c',
  greenDark: '#1a5c42',
  white: '#ffffff',
  text: '#f0f4f8',
  muted: '#9eb0c8',
  card: 'rgba(255,255,255,0.06)',
  cardBorder: 'rgba(232, 197, 71, 0.35)',
}

export async function generateSharePosterBlob(opts: SharePosterOptions): Promise<Blob | null> {
  const canvas = document.createElement('canvas')
  canvas.width = W
  canvas.height = H
  const ctx = canvas.getContext('2d')
  if (!ctx) return null

  const variant = opts.variant ?? 'invite'
  const name = posterDisplayName(opts.displayName ?? extractNameFromTitle(opts.title))

  drawBackground(ctx)
  drawPitchLines(ctx)
  drawBrandHeader(ctx, opts.badge, opts.showAiPill ?? (variant === 'collectible' || variant === 'card'))
  drawFootball(ctx, 520, 72, 28)

  if (variant === 'predict') {
    await drawPredictLayout(ctx, opts, name)
  } else if (variant === 'profile') {
    await drawProfileLayout(ctx, opts, name)
  } else if (variant === 'collectible' || variant === 'card' || variant === 'set_complete') {
    await drawCollectibleLayout(ctx, opts, name, variant)
  } else if (variant === 'invite' && opts.layoutVersion === 'v2') {
    await drawInviteLayoutV2(ctx, opts, name)
  } else {
    await drawInviteLayout(ctx, opts, name)
  }

  return new Promise((resolve) => {
    canvas.toBlob((blob) => resolve(blob), 'image/png')
  })
}

export async function generateSharePosterObjectUrl(opts: SharePosterOptions): Promise<string | null> {
  const blob = await generateSharePosterBlob(opts)
  if (!blob) return null
  return URL.createObjectURL(blob)
}

export async function downloadSharePoster(opts: SharePosterOptions, filename = 'wc2026-share.png') {
  const blob = await generateSharePosterBlob(opts)
  if (!blob) throw new Error('无法生成海报')
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

export async function loadImageForCanvas(url: string, timeoutMs = 8000): Promise<HTMLImageElement | null> {
  if (!url) return null
  try {
    const src = url.startsWith('/') ? `${window.location.origin}${url}` : url
    const img = await Promise.race([
      loadImage(src),
      new Promise<never>((_, reject) => {
        setTimeout(() => reject(new Error('timeout')), timeoutMs)
      }),
    ])
    return img
  } catch {
    return null
  }
}

function extractNameFromTitle(title?: string): string | undefined {
  if (!title) return undefined
  const m = title.match(/^(.+?)\s*邀/)
  return m?.[1]?.trim()
}

async function drawInviteLayoutV2(ctx: CanvasRenderingContext2D, opts: SharePosterOptions, name: string) {
  drawAvatar(ctx, name, 300, 175, 48)
  setFont(ctx, 'bold 32px', C.white)
  ctx.textAlign = 'center'
  ctx.fillText(`${name} 邀你一起猜世界杯`, 300, 255)

  drawBenefitColumns(ctx, 310)

  const aiLine = opts.aiHookLine || DEFAULT_AI_HOOK
  drawAiHookBar(ctx, 400, aiLine)

  if (opts.statsLine) {
    setFont(ctx, '16px', C.gold)
    ctx.fillText(opts.statsLine, 300, 448)
  }

  const qrCaption = opts.inviteCode
    ? `长按识别 · 注册领币`
    : '长按识别 · 注册领币'
  await drawQrCard(ctx, opts.qrUrl, 590, qrCaption, opts.inviteCode)

  drawFooter(ctx, opts.footer ?? '虚拟奖励不可提现 · 非博彩 · 最后一舞')
}

function drawBenefitColumns(ctx: CanvasRenderingContext2D, centerY: number) {
  const colW = 248
  const gap = 24
  const leftX = (W - colW * 2 - gap) / 2
  const cols = [
    { title: '好友得', lines: ['注册送 100 球迷币', '免费猜一场'] },
    { title: '你得', lines: ['有效邀请得币', '冲召友榜'] },
  ]
  cols.forEach((col, i) => {
    const x = leftX + i * (colW + gap)
    ctx.fillStyle = C.card
    roundRect(ctx, x, centerY - 52, colW, 104, 12)
    ctx.fill()
    ctx.strokeStyle = 'rgba(61, 214, 140, 0.28)'
    ctx.lineWidth = 1
    roundRect(ctx, x, centerY - 52, colW, 104, 12)
    ctx.stroke()

    setFont(ctx, 'bold 17px', C.green)
    ctx.textAlign = 'center'
    ctx.fillText(col.title, x + colW / 2, centerY - 22)
    setFont(ctx, '15px', C.text)
    ctx.fillText(col.lines[0], x + colW / 2, centerY + 8)
    setFont(ctx, '14px', C.muted)
    ctx.fillText(col.lines[1], x + colW / 2, centerY + 32)
  })
}

function drawAiHookBar(ctx: CanvasRenderingContext2D, y: number, text: string) {
  const w = 520
  const h = 44
  const x = (W - w) / 2
  ctx.fillStyle = 'rgba(61, 214, 140, 0.12)'
  roundRect(ctx, x, y - h / 2, w, h, 10)
  ctx.fill()
  ctx.strokeStyle = 'rgba(61, 214, 140, 0.45)'
  ctx.lineWidth = 1
  roundRect(ctx, x, y - h / 2, w, h, 10)
  ctx.stroke()
  setFont(ctx, 'bold 16px', C.green)
  ctx.textAlign = 'center'
  ctx.fillText(`▶ ${text}`, W / 2, y + 6)
}

async function drawCollectibleLayout(
  ctx: CanvasRenderingContext2D,
  opts: SharePosterOptions,
  name: string,
  variant: 'collectible' | 'card' | 'set_complete',
) {
  const rarity = opts.rarity ?? 'common'
  const style = RARITY_POSTER_STYLES[rarity]
  const playerName = opts.playerName || extractPlayerFromTitle(opts.title) || '球星卡'
  const owned = opts.owned !== false

  const headline = owned
    ? variant === 'set_complete'
      ? `${name} 集齐套组`
      : `${name} 收藏了 ${playerName}`
    : `${name} 正在收集 ${playerName}`

  setFont(ctx, 'bold 26px', C.white)
  ctx.textAlign = 'center'
  wrapText(ctx, headline, 300, 148, 520, 32)

  await drawCardFrame(ctx, 300, 340, opts, style, owned)

  setFont(ctx, 'bold 22px', style.border)
  ctx.fillText(`${playerName} · 最后一舞`, 300, 560)

  const subParts = [style.label]
  if (owned && (opts.star ?? 0) > 0) subParts.unshift(`★${opts.star}`)
  if (variant === 'set_complete') subParts.push('套组成就')
  else if (!owned) subParts.push('猜中/手册可掉落')
  setFont(ctx, '18px', C.muted)
  ctx.fillText(subParts.join(' · '), 300, 592)

  if (opts.chainMinted) {
    drawChainBadge(ctx, 300, 622, opts.chainHashShort)
  }

  const qrCaption = owned
    ? variant === 'set_complete'
      ? '扫码一起收集'
      : '扫码查看 TA 的藏品'
    : '扫码一起收集'
  await drawQrCard(ctx, opts.qrUrl, opts.chainMinted ? 680 : 650, qrCaption)

  drawFooter(ctx, opts.footer ?? '虚拟收藏 · 可用积分流通 · 仅供炫耀')
}

async function drawCardFrame(
  ctx: CanvasRenderingContext2D,
  cx: number,
  cy: number,
  opts: SharePosterOptions,
  style: (typeof RARITY_POSTER_STYLES)[SharePosterRarity],
  owned: boolean,
) {
  const fw = 280
  const fh = 380
  const x = cx - fw / 2
  const y = cy - fh / 2

  ctx.save()
  ctx.shadowColor = style.glow
  ctx.shadowBlur = 24
  ctx.strokeStyle = style.border
  ctx.lineWidth = 4
  roundRect(ctx, x, y, fw, fh, 16)
  ctx.stroke()
  ctx.shadowBlur = 0

  ctx.fillStyle = 'rgba(0,0,0,0.45)'
  roundRect(ctx, x + 4, y + 4, fw - 8, fh - 8, 14)
  ctx.fill()

  const img = opts.cardImageUrl ? await loadImageForCanvas(opts.cardImageUrl) : null
  if (img) {
    ctx.save()
    roundRect(ctx, x + 8, y + 8, fw - 16, fh - 16, 12)
    ctx.clip()
    if (!owned) {
      ctx.filter = 'grayscale(1) brightness(0.55)'
    }
    ctx.drawImage(img, x + 8, y + 8, fw - 16, fh - 16)
    ctx.restore()
  } else {
    const initial = posterInitial(opts.playerName || '?')
    setFont(ctx, `bold ${initial.length === 1 ? '120px' : '72px'}`, style.border)
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillText(initial, cx, cy - 10)
    ctx.textBaseline = 'alphabetic'
  }

  if (!owned) {
    ctx.fillStyle = 'rgba(0,0,0,0.55)'
    roundRect(ctx, x + 8, y + fh - 56, fw - 16, 40, 8)
    ctx.fill()
    setFont(ctx, 'bold 16px', C.muted)
    ctx.textAlign = 'center'
    ctx.fillText('收集中', cx, y + fh - 28)
  }

  const badgeW = 56
  const badgeH = 28
  ctx.fillStyle = style.badgeBg
  roundRect(ctx, x + 12, y + 12, badgeW, badgeH, 8)
  ctx.fill()
  setFont(ctx, 'bold 13px', C.white)
  ctx.textAlign = 'center'
  ctx.fillText(style.label, x + 12 + badgeW / 2, y + 32)

  if (owned && (opts.star ?? 0) > 0) {
    setFont(ctx, 'bold 18px', C.gold)
    ctx.fillText(`★${opts.star}`, cx, y + fh - 24)
  }

  ctx.restore()
}

function drawChainBadge(ctx: CanvasRenderingContext2D, cx: number, y: number, hashShort?: string) {
  const label = hashShort ? `链上凭证 · ${hashShort}` : '文昌链收藏凭证'
  setFont(ctx, 'bold 14px', C.bgTop)
  const tw = Math.min(ctx.measureText(label).width + 32, 480)
  ctx.fillStyle = C.green
  roundRect(ctx, cx - tw / 2, y - 14, tw, 28, 14)
  ctx.fill()
  ctx.textAlign = 'center'
  ctx.fillText(label, cx, y + 5)
}

function extractPlayerFromTitle(title?: string): string | undefined {
  if (!title) return undefined
  const m = title.match(/(?:获得了|收藏了|正在收集)\s*(.+?)(?:\s|$|·)/)
  return m?.[1]?.trim()
}

async function drawInviteLayout(ctx: CanvasRenderingContext2D, opts: SharePosterOptions, name: string) {
  drawAvatar(ctx, name, 300, 200, 52)
  setFont(ctx, 'bold 34px', C.white)
  ctx.textAlign = 'center'
  ctx.fillText(`${name} 邀你猜世界杯`, 300, 290)

  setFont(ctx, '22px', C.muted)
  ctx.fillText('娱乐竞猜 · 猜胜负 · 赢球迷币 · 冲榜换装扮', 300, 328)

  drawHighlightCard(ctx, 300, 390, '免费猜一场 · 注册即送 100 球迷币', opts.subtitle)

  drawStepsRow(ctx, 455, [
    { n: '1', t: '扫码注册' },
    { n: '2', t: '免费竞猜' },
    { n: '3', t: '猜中领奖' },
  ])

  if (opts.statsLine) {
    setFont(ctx, '18px', C.gold)
    ctx.fillText(opts.statsLine, 300, 545)
  }

  await drawQrCard(ctx, opts.qrUrl, 575, '长按识别 · 加入一起猜')

  drawFooter(ctx, opts.footer ?? '虚拟奖励不可提现 · 非博彩 · 最后一舞')
}

async function drawPredictLayout(ctx: CanvasRenderingContext2D, opts: SharePosterOptions, _name: string) {
  setFont(ctx, 'bold 16px', C.gold)
  ctx.textAlign = 'center'
  ctx.fillText('⚽ 这场球 · 你来猜吗？', 300, 175)

  setFont(ctx, 'bold 40px', C.white)
  wrapText(ctx, opts.title || '世界杯场次', 300, 230, 520, 48)

  if (opts.pickHighlight) {
    drawPickBadge(ctx, 300, 320, opts.pickHighlight)
  }

  setFont(ctx, '20px', C.muted)
  wrapText(ctx, opts.subtitle, 300, 390, 520, 28)

  drawHighlightCard(ctx, 300, 455, '扫码也能免费猜 · 猜中拿积分', opts.statsLine || '一起来猜 2026 世界杯')

  await drawQrCard(ctx, opts.qrUrl, 620, '扫码猜这场 · 或复制链接')

  drawFooter(ctx, opts.footer ?? '娱乐竞猜 · 非博彩 · 最后一舞')
}

async function drawProfileLayout(ctx: CanvasRenderingContext2D, opts: SharePosterOptions, name: string) {
  drawAvatar(ctx, name, 300, 195, 56)
  setFont(ctx, 'bold 32px', C.white)
  ctx.textAlign = 'center'
  ctx.fillText(name, 300, 285)

  setFont(ctx, '20px', C.muted)
  wrapText(ctx, opts.subtitle, 300, 325, 520, 28)

  if (opts.statsLine) {
    drawHighlightCard(ctx, 300, 400, '我的战绩', opts.statsLine)
  }

  await drawQrCard(ctx, opts.qrUrl, 580, '扫码看我的球迷名片')

  drawFooter(ctx, opts.footer ?? '一起来猜世界杯 · 最后一舞')
}

function drawBackground(ctx: CanvasRenderingContext2D) {
  const grad = ctx.createLinearGradient(0, 0, 0, H)
  grad.addColorStop(0, C.bgTop)
  grad.addColorStop(0.45, C.bgMid)
  grad.addColorStop(1, C.bgBottom)
  ctx.fillStyle = grad
  ctx.fillRect(0, 0, W, H)

  const spot = ctx.createRadialGradient(300, 180, 20, 300, 400, 420)
  spot.addColorStop(0, 'rgba(61, 214, 140, 0.12)')
  spot.addColorStop(1, 'rgba(0,0,0,0)')
  ctx.fillStyle = spot
  ctx.fillRect(0, 0, W, H)

  ctx.strokeStyle = C.cardBorder
  ctx.lineWidth = 2
  roundRect(ctx, 16, 16, W - 32, H - 32, 20)
  ctx.stroke()
}

function drawPitchLines(ctx: CanvasRenderingContext2D) {
  ctx.save()
  ctx.strokeStyle = 'rgba(61, 214, 140, 0.07)'
  ctx.lineWidth = 1.5
  for (let i = 0; i < 6; i++) {
    const y = 680 + i * 28
    ctx.beginPath()
    ctx.moveTo(40, y)
    ctx.lineTo(W - 40, y)
    ctx.stroke()
  }
  ctx.beginPath()
  ctx.arc(300, 920, 120, Math.PI, 0)
  ctx.stroke()
  ctx.restore()
}

function drawBrandHeader(ctx: CanvasRenderingContext2D, badge?: string, showAiPill = false) {
  ctx.fillStyle = 'rgba(232, 197, 71, 0.12)'
  roundRect(ctx, 28, 28, W - 56, 88, 14)
  ctx.fill()

  setFont(ctx, 'bold 26px', C.gold)
  ctx.textAlign = 'left'
  ctx.fillText('最后一舞', 48, 68)

  setFont(ctx, '16px', C.muted)
  ctx.fillText('2026 世界杯 · 球迷竞猜', 48, 96)

  let rightEdge = W - 48
  if (showAiPill) {
    const pill = 'AI 快览'
    setFont(ctx, 'bold 12px', C.bgTop)
    const pw = ctx.measureText(pill).width + 16
    rightEdge -= pw + 8
    ctx.fillStyle = C.green
    roundRect(ctx, rightEdge, 48, pw, 26, 13)
    ctx.fill()
    ctx.textAlign = 'center'
    ctx.fillText(pill, rightEdge + pw / 2, 66)
  }

  if (badge) {
    setFont(ctx, 'bold 13px', C.bgTop)
    const tw = ctx.measureText(badge).width + 20
    ctx.fillStyle = C.green
    roundRect(ctx, rightEdge - tw, 48, tw, 28, 14)
    ctx.fill()
    ctx.textAlign = 'center'
    ctx.fillText(badge, rightEdge - tw / 2, 67)
  }
}

function drawFootball(ctx: CanvasRenderingContext2D, cx: number, cy: number, r: number) {
  ctx.save()
  ctx.beginPath()
  ctx.arc(cx, cy, r, 0, Math.PI * 2)
  ctx.fillStyle = '#f4f4f4'
  ctx.fill()
  ctx.strokeStyle = '#333'
  ctx.lineWidth = 1.2
  ctx.stroke()
  ctx.fillStyle = '#222'
  ctx.beginPath()
  for (let i = 0; i < 5; i++) {
    const a = (i * 72 - 90) * (Math.PI / 180)
    const px = cx + Math.cos(a) * r * 0.35
    const py = cy + Math.sin(a) * r * 0.35
    if (i === 0) ctx.moveTo(px, py)
    else ctx.lineTo(px, py)
  }
  ctx.closePath()
  ctx.fill()
  ctx.restore()
}

function drawAvatar(ctx: CanvasRenderingContext2D, name: string, cx: number, cy: number, r: number) {
  const grad = ctx.createLinearGradient(cx - r, cy - r, cx + r, cy + r)
  grad.addColorStop(0, C.gold)
  grad.addColorStop(1, C.greenDark)
  ctx.beginPath()
  ctx.arc(cx, cy, r, 0, Math.PI * 2)
  ctx.fillStyle = grad
  ctx.fill()
  ctx.strokeStyle = 'rgba(255,255,255,0.5)'
  ctx.lineWidth = 3
  ctx.stroke()

  const initial = posterInitial(name)
  setFont(ctx, initial.length === 1 ? `bold ${Math.round(r * 0.9)}px` : `bold ${Math.round(r * 0.65)}px`, C.white)
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.fillText(initial, cx, cy + 2)
  ctx.textBaseline = 'alphabetic'
}

function drawHighlightCard(ctx: CanvasRenderingContext2D, cx: number, cy: number, label: string, body?: string) {
  const w = 520
  const h = body ? 88 : 56
  ctx.fillStyle = C.card
  roundRect(ctx, cx - w / 2, cy - h / 2, w, h, 14)
  ctx.fill()
  ctx.strokeStyle = C.cardBorder
  ctx.lineWidth = 1.5
  roundRect(ctx, cx - w / 2, cy - h / 2, w, h, 14)
  ctx.stroke()

  setFont(ctx, 'bold 18px', C.green)
  ctx.textAlign = 'center'
  ctx.fillText(label, cx, cy - (body ? 12 : 0))
  if (body) {
    setFont(ctx, '17px', C.text)
    wrapText(ctx, body, cx, cy + 18, w - 40, 24)
  }
}

function drawPickBadge(ctx: CanvasRenderingContext2D, cx: number, cy: number, text: string) {
  setFont(ctx, 'bold 22px', C.bgTop)
  const tw = Math.min(ctx.measureText(text).width + 48, 480)
  ctx.fillStyle = C.gold
  roundRect(ctx, cx - tw / 2, cy - 22, tw, 44, 22)
  ctx.fill()
  ctx.textAlign = 'center'
  ctx.fillText(text, cx, cy + 8)
}

function drawStepsRow(
  ctx: CanvasRenderingContext2D,
  y: number,
  steps: { n: string; t: string }[],
) {
  const gap = 12
  const boxW = (520 - gap * 2) / 3
  const startX = 40
  steps.forEach((step, i) => {
    const x = startX + i * (boxW + gap)
    ctx.fillStyle = 'rgba(255,255,255,0.05)'
    roundRect(ctx, x, y, boxW, 72, 12)
    ctx.fill()
    ctx.strokeStyle = 'rgba(61, 214, 140, 0.25)'
    ctx.lineWidth = 1
    roundRect(ctx, x, y, boxW, 72, 12)
    ctx.stroke()

    ctx.beginPath()
    ctx.arc(x + 26, y + 26, 14, 0, Math.PI * 2)
    ctx.fillStyle = C.greenDark
    ctx.fill()
    setFont(ctx, 'bold 14px', C.green)
    ctx.textAlign = 'center'
    ctx.fillText(step.n, x + 26, y + 31)

    setFont(ctx, '15px', C.text)
    ctx.fillText(step.t, x + boxW / 2, y + 58)
  })
}

async function drawQrCard(
  ctx: CanvasRenderingContext2D,
  qrUrl: string | undefined,
  centerY: number,
  caption: string,
  inviteCode?: string,
) {
  const cardW = 280
  const cardH = inviteCode ? 340 : 300
  const x = (W - cardW) / 2
  const y = centerY - cardH / 2

  ctx.fillStyle = '#ffffff'
  roundRect(ctx, x, y, cardW, cardH, 18)
  ctx.fill()
  ctx.shadowColor = 'rgba(0,0,0,0.35)'
  ctx.shadowBlur = 24
  ctx.shadowOffsetY = 8
  roundRect(ctx, x, y, cardW, cardH, 18)
  ctx.fill()
  ctx.shadowColor = 'transparent'
  ctx.shadowBlur = 0
  ctx.shadowOffsetY = 0

  if (qrUrl) {
    try {
      const qrDataUrl = await QRCode.toDataURL(qrUrl, {
        width: 200,
        margin: 1,
        color: { dark: '#0a1628', light: '#ffffff' },
      })
      const qrImg = await loadImage(qrDataUrl)
      ctx.drawImage(qrImg, x + 40, y + 28, 200, 200)
    } catch {
      setFont(ctx, '12px monospace', '#333')
      ctx.textAlign = 'center'
      wrapText(ctx, qrUrl, x + cardW / 2, y + 120, cardW - 24, 16)
    }
  }

  let captionY = y + cardH - 28
  if (inviteCode) {
    setFont(ctx, 'bold 15px', '#1a2332')
    ctx.textAlign = 'center'
    ctx.fillText(`邀请码 ${inviteCode}`, W / 2, y + cardH - 52)
    captionY = y + cardH - 24
  }

  setFont(ctx, 'bold 17px', '#1a2332')
  ctx.textAlign = 'center'
  ctx.fillText(caption, W / 2, captionY)
}

function drawFooter(ctx: CanvasRenderingContext2D, text: string) {
  ctx.fillStyle = 'rgba(0,0,0,0.35)'
  roundRect(ctx, 40, H - 72, W - 80, 44, 10)
  ctx.fill()
  setFont(ctx, '15px', C.text)
  ctx.textAlign = 'center'
  ctx.fillText(text, W / 2, H - 44)
}

function roundRect(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  w: number,
  h: number,
  r: number,
) {
  const rad = Math.min(r, w / 2, h / 2)
  ctx.beginPath()
  ctx.moveTo(x + rad, y)
  ctx.lineTo(x + w - rad, y)
  ctx.quadraticCurveTo(x + w, y, x + w, y + rad)
  ctx.lineTo(x + w, y + h - rad)
  ctx.quadraticCurveTo(x + w, y + h, x + w - rad, y + h)
  ctx.lineTo(x + rad, y + h)
  ctx.quadraticCurveTo(x, y + h, x, y + h - rad)
  ctx.lineTo(x, y + rad)
  ctx.quadraticCurveTo(x, y, x + rad, y)
  ctx.closePath()
}

function setFont(ctx: CanvasRenderingContext2D, spec: string, color: string) {
  ctx.font = `${spec} "PingFang SC", "Microsoft YaHei", "Helvetica Neue", sans-serif`
  ctx.fillStyle = color
}

function wrapText(
  ctx: CanvasRenderingContext2D,
  text: string,
  x: number,
  y: number,
  maxWidth: number,
  lineHeight: number,
) {
  ctx.textAlign = 'center'
  const chars = text.split('')
  let line = ''
  let drawY = y
  for (let i = 0; i < chars.length; i++) {
    const test = line + chars[i]
    if (ctx.measureText(test).width > maxWidth && line) {
      ctx.fillText(line, x, drawY)
      line = chars[i]
      drawY += lineHeight
    } else {
      line = test
    }
  }
  if (line) ctx.fillText(line, x, drawY)
}

function loadImage(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.crossOrigin = 'anonymous'
    img.onload = () => resolve(img)
    img.onerror = reject
    img.src = src
  })
}
