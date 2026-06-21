import type { App, ComponentPublicInstance } from 'vue'
import { ElMessage } from 'element-plus'
import { getErrorMessage, isRateLimitError } from '../api/client'
import { notifyRateLimitOnce, notifyRateLimitExplicit } from '../api/rateLimitGuard'

export function showApiError(error: unknown, fallback?: string) {
  if (isRateLimitError(error)) {
    if (!error.notified) {
      notifyRateLimitExplicit(error.message)
    }
    return
  }
  ElMessage.error(getErrorMessage(error) || fallback || '操作失败，请稍后重试')
}

/** Login / critical flows: always surface rate-limit copy (inline + toast). */
export function showRateLimitError(error: unknown, fallback?: string): string {
  const message = isRateLimitError(error)
    ? error.message
    : getErrorMessage(error) || fallback || '请求过于频繁，请稍后再试'
  notifyRateLimitExplicit(message)
  return message
}

export function registerGlobalErrorHandlers(app: App) {
  app.config.errorHandler = (
    err: unknown,
    _instance: ComponentPublicInstance | null,
    info: string,
  ) => {
    console.error('[Vue Error]', info, err)
    ElMessage.error('页面出现异常，请刷新后重试')
  }

  window.addEventListener('unhandledrejection', (event) => {
    const reason = event.reason
    if (isRateLimitError(reason)) {
      notifyRateLimitOnce(getErrorMessage(reason))
      event.preventDefault()
      return
    }
    console.error('[Unhandled Promise]', reason)
  })
}