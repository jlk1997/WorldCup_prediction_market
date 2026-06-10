import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios'
import type { ApiErrorBody } from '../types/api'
import { getAccessToken, logout, refreshSession } from '../stores/authStore'
import { isRateLimited, pauseForRateLimit, rateLimitMessageFromBody } from './rateLimitGuard'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:10086'

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000,
})

apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  if (isRateLimited()) {
    return Promise.reject(new Error('请求过于频繁，请稍后再试'))
  }
  const token = getAccessToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

let refreshing: Promise<boolean> | null = null

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<ApiErrorBody>) => {
    const status = error.response?.status
    const original = error.config

    if (status === 401 && original && !original.url?.includes('/api/auth/refresh')) {
      if (!refreshing) {
        refreshing = refreshSession().finally(() => {
          refreshing = null
        })
      }
      const ok = await refreshing
      if (ok && original.headers) {
        original.headers.Authorization = `Bearer ${getAccessToken()}`
        return apiClient.request(original)
      }
      logout()
      if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/login')) {
        window.location.href = `/login?redirect=${encodeURIComponent(window.location.pathname)}`
      }
    }

    const rateMsg = rateLimitMessageFromBody(error.response?.data)
    if (rateMsg) {
      pauseForRateLimit()
    }

    const message =
      rateMsg ||
      error.response?.data?.message ||
      error.message ||
      '网络请求失败，请检查后端是否已启动'
    return Promise.reject(new Error(message))
  }
)

export { API_BASE_URL }

export function getErrorMessage(error: unknown): string {
  if (error instanceof Error) return error.message
  return '未知错误'
}
