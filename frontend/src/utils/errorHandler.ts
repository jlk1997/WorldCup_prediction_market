import type { App, ComponentPublicInstance } from 'vue'
import { ElMessage } from 'element-plus'
import { getErrorMessage, isRateLimitError } from '../api/client'
import { notifyRateLimitOnce } from '../api/rateLimitGuard'

export function showApiError(error: unknown, fallback?: string) {
  if (isRateLimitError(error) && error.notified) return
  ElMessage.error(getErrorMessage(error) || fallback || '操作失败，请稍后重试')
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