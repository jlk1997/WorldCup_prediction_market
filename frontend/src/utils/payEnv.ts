export type PayChannel = 'page' | 'wap'

export function isWeChatBrowser(): boolean {
  if (typeof navigator === 'undefined') return false
  return /MicroMessenger/i.test(navigator.userAgent)
}

export function isMobileBrowser(): boolean {
  if (typeof navigator === 'undefined') return false
  const ua = navigator.userAgent.toLowerCase()
  if (/ipad|tablet/i.test(ua)) return false
  return /mobile|android|iphone|ipod/i.test(ua)
}

export function resolvePayChannel(): PayChannel {
  return isMobileBrowser() ? 'wap' : 'page'
}

export const WECHAT_PAY_HINT =
  '微信内无法直接完成支付宝支付。请点击右上角「⋯」，选择「在浏览器中打开」后再购买。'
