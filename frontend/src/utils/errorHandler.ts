import type { App, ComponentPublicInstance } from 'vue'
import { ElMessage } from 'element-plus'

export function registerGlobalErrorHandlers(app: App) {
  app.config.errorHandler = (
    err: unknown,
    _instance: ComponentPublicInstance | null,
    info: string
  ) => {
    console.error('[Vue Error]', info, err)
    ElMessage.error('页面出现异常，请刷新后重试')
  }

  window.addEventListener('unhandledrejection', (event) => {
    console.error('[Unhandled Promise]', event.reason)
  })
}
