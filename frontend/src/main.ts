import { createApp } from 'vue'
import App from './App.vue'
import './styles/theme.css'
import './styles/responsive.css'
import router from './router'
import { registerGlobalErrorHandlers } from './utils/errorHandler'

// 屏蔽 ResizeObserver loop 错误
const debounce = (fn: Function, delay: number) => {
  let timer: ReturnType<typeof setTimeout> | undefined
  return (...args: unknown[]) => {
    if (timer) clearTimeout(timer)
    timer = setTimeout(() => {
      fn(...args)
    }, delay)
  }
}
const _ResizeObserver = window.ResizeObserver
window.ResizeObserver = class ResizeObserver extends _ResizeObserver {
  constructor(callback: ResizeObserverCallback) {
    callback = debounce(callback, 16)
    super(callback)
  }
}

import { initAuth } from './stores/authStore'

const app = createApp(App)

registerGlobalErrorHandlers(app)

app.use(router)
initAuth()
app.mount('#app')
