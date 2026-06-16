import { ElMessageBox } from 'element-plus'
import { getProducts, type Product } from '@/api/commerce'
import { isWeChatBrowser, WECHAT_PAY_HINT } from '@/utils/payEnv'
import { trackEvent } from '@/utils/analytics'

let cachedStarter: Product | null | undefined

export async function getStarterPackProduct(): Promise<Product | null> {
  if (cachedStarter !== undefined) return cachedStarter
  try {
    const products = await getProducts()
    cachedStarter =
      products.find((p) => p.sku === 'coins_small') ??
      products.find((p) => p.product_type === 'coins' && p.price_fen === 600) ??
      null
    return cachedStarter
  } catch {
    cachedStarter = null
    return null
  }
}

export function invalidateStarterPackCache() {
  cachedStarter = undefined
}

/** ¥6 小包 one-click 推荐（质押 / AI 币不足时） */
export async function offerStarterPack(options: {
  reason: 'predict_stake' | 'ai_billing'
  shortfall?: number
  onNavigate: (path: string, query?: Record<string, string>) => void
}): Promise<void> {
  const pack = await getStarterPackProduct()
  const priceYuan = pack ? (pack.price_fen / 100).toFixed(0) : '6'
  const coins = pack?.coins_grant ?? 60
  const shortfallHint =
    options.shortfall && options.shortfall > 0 ? `还差 ${options.shortfall} 币 · ` : ''
  const body = pack
    ? `${shortfallHint}推荐 ${priceYuan} 元球迷币小包（+${coins} 币），够再猜好几场或买 AI 分析。`
    : `${shortfallHint}去商城充值球迷币，或购买赛季通行证每日领 50 币。`

  trackEvent('starter_pack_offer_show', { reason: options.reason })

  if (isWeChatBrowser()) {
    try {
      await ElMessageBox.alert(`${WECHAT_PAY_HINT}\n\n${body}`, '请用浏览器打开', {
        confirmButtonText: '我知道了',
        type: 'warning',
      })
    } catch {
      /* closed */
    }
    options.onNavigate('/shop', pack ? { highlight: pack.sku } : undefined)
    return
  }

  try {
    await ElMessageBox.confirm(body, '球迷币不足', {
      confirmButtonText: pack ? `买 ${priceYuan} 元小包` : '去商城',
      cancelButtonText: '先看看',
      type: 'info',
    })
    trackEvent('starter_pack_offer_accept', { reason: options.reason, sku: pack?.sku ?? '' })
    options.onNavigate('/shop', pack ? { highlight: pack.sku, buy: '1' } : undefined)
  } catch {
    trackEvent('starter_pack_offer_dismiss', { reason: options.reason })
  }
}

export function passBenefitsSummary(benefits: {
  coins_saved_today?: number
  coins_claimed_today?: boolean
  daily_coins_grant?: number
  points_bonus_pct?: number
} | null | undefined): string | null {
  if (!benefits) return null
  const parts: string[] = []
  if (benefits.coins_saved_today && benefits.coins_saved_today > 0) {
    parts.push(`今日已省 ${benefits.coins_saved_today} 币`)
  } else if (benefits.daily_coins_grant && !benefits.coins_claimed_today) {
    parts.push(`今日 ${benefits.daily_coins_grant} 币未领`)
  }
  if (benefits.points_bonus_pct) {
    parts.push(`猜中积分 +${benefits.points_bonus_pct}%`)
  }
  return parts.length ? parts.join(' · ') : '通行证生效中'
}
