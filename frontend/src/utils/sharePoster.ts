export interface SharePosterOptions {
  title: string
  subtitle: string
  statsLine?: string
  footer: string
  qrUrl?: string
}

export async function generateSharePosterBlob(opts: SharePosterOptions): Promise<Blob | null> {
  const canvas = document.createElement('canvas')
  canvas.width = 600
  canvas.height = 900
  const ctx = canvas.getContext('2d')
  if (!ctx) return null

  const grad = ctx.createLinearGradient(0, 0, 600, 900)
  grad.addColorStop(0, '#1a1224')
  grad.addColorStop(0.5, '#2d1a28')
  grad.addColorStop(1, '#121018')
  ctx.fillStyle = grad
  ctx.fillRect(0, 0, 600, 900)

  ctx.strokeStyle = 'rgba(212, 165, 116, 0.45)'
  ctx.lineWidth = 3
  ctx.strokeRect(24, 24, 552, 852)

  ctx.fillStyle = '#d4a574'
  ctx.font = 'bold 28px sans-serif'
  ctx.textAlign = 'center'
  ctx.fillText('最后一舞 · 世界杯2026', 300, 100)

  ctx.fillStyle = '#f5f0ea'
  ctx.font = 'bold 36px sans-serif'
  wrapText(ctx, opts.title, 300, 200, 520, 44)

  ctx.fillStyle = '#c9a0a8'
  ctx.font = '22px sans-serif'
  wrapText(ctx, opts.subtitle, 300, 320, 520, 30)

  if (opts.statsLine) {
    ctx.fillStyle = '#9a94a8'
    ctx.font = '20px sans-serif'
    wrapText(ctx, opts.statsLine, 300, 420, 520, 28)
  }

  if (opts.qrUrl) {
    try {
      const qrImg = await loadImage(
        `https://api.qrserver.com/v1/create-qr-code/?size=160x160&data=${encodeURIComponent(opts.qrUrl)}`
      )
      ctx.drawImage(qrImg, 220, 500, 160, 160)
    } catch {
      ctx.fillStyle = '#9a94a8'
      ctx.font = '16px monospace'
      wrapText(ctx, opts.qrUrl, 300, 560, 520, 22)
    }
  }

  ctx.fillStyle = '#6e7681'
  ctx.font = '16px sans-serif'
  wrapText(ctx, opts.footer, 300, 820, 520, 22)

  return new Promise((resolve) => {
    canvas.toBlob((blob) => resolve(blob), 'image/png')
  })
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

function wrapText(
  ctx: CanvasRenderingContext2D,
  text: string,
  x: number,
  y: number,
  maxWidth: number,
  lineHeight: number
) {
  const words = text.split('')
  let line = ''
  let drawY = y
  for (let i = 0; i < words.length; i++) {
    const test = line + words[i]
    if (ctx.measureText(test).width > maxWidth && line) {
      ctx.fillText(line, x, drawY)
      line = words[i]
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
