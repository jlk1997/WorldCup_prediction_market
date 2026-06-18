import QRCode from 'qrcode'
import { posterDisplayName, posterInitial } from './sharePosterDisplayName'

export type SharePosterVariant = 'invite' | 'predict' | 'profile' | 'card' | 'set_complete'

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
}

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
  drawBrandHeader(ctx, opts.badge)
  drawFootball(ctx, 520, 72, 28)

  if (variant === 'predict') {
    await drawPredictLayout(ctx, opts, name)
  } else if (variant === 'profile') {
    await drawProfileLayout(ctx, opts, name)
  } else if (variant === 'card' || variant === 'set_complete') {
    await drawCardLayout(ctx, opts, name, variant)
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

function extractNameFromTitle(title?: string): string | undefined {
  if (!title) return undefined
  const m = title.match(/^(.+?)\s*邀/)
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

async function drawCardLayout(
  ctx: CanvasRenderingContext2D,
  opts: SharePosterOptions,
  name: string,
  variant: 'card' | 'set_complete',
) {
  const title = opts.title || (variant === 'set_complete' ? `${name} 集齐套组` : `${name} 的球星卡`)
  setFont(ctx, 'bold 30px', C.gold)
  ctx.textAlign = 'center'
  ctx.fillText(title, 300, 220)

  setFont(ctx, '22px', C.text)
  wrapText(ctx, opts.subtitle, 300, 280, 520, 30)

  const cardLabel = variant === 'set_complete' ? '套组成就 · 典藏收藏家' : '数字藏品 · 虚拟收藏'
  drawHighlightCard(ctx, 300, 380, cardLabel, opts.statsLine || '猜中掉落 · 无金钱价值 · 不可交易')

  setFont(ctx, '16px', C.muted)
  wrapText(
    ctx,
    '平台内虚拟收藏，不可提现、不可转赠。仅供娱乐收集与炫耀。',
    300,
    480,
    520,
    24,
  )

  await drawQrCard(ctx, opts.qrUrl, 620, variant === 'set_complete' ? '扫码一起收集' : '扫码打开收藏册')

  drawFooter(ctx, opts.footer ?? '数字藏品 · 最后一舞 · 非金融属性')
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

function drawBrandHeader(ctx: CanvasRenderingContext2D, badge?: string) {
  ctx.fillStyle = 'rgba(232, 197, 71, 0.12)'
  roundRect(ctx, 28, 28, W - 56, 88, 14)
  ctx.fill()

  setFont(ctx, 'bold 26px', C.gold)
  ctx.textAlign = 'left'
  ctx.fillText('最后一舞', 48, 68)

  setFont(ctx, '16px', C.muted)
  ctx.fillText('2026 世界杯 · 球迷竞猜', 48, 96)

  if (badge) {
    setFont(ctx, 'bold 13px', C.bgTop)
    const tw = ctx.measureText(badge).width + 20
    ctx.fillStyle = C.green
    roundRect(ctx, W - 48 - tw, 48, tw, 28, 14)
    ctx.fill()
    ctx.textAlign = 'center'
    ctx.fillText(badge, W - 48 - tw / 2, 67)
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
) {
  const cardW = 280
  const cardH = 300
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

  setFont(ctx, 'bold 17px', '#1a2332')
  ctx.textAlign = 'center'
  ctx.fillText(caption, W / 2, y + cardH - 28)
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
    img.onload = () => resolve(img)
    img.onerror = reject
    img.src = src
  })
}
