import type { AxiosError } from 'axios'
import type { ApiErrorBody } from '../types/api'

/** 从 API 异常中提取用户可读的错误文案。 */
export function extractApiError(err: unknown, fallback = '操作失败，请稍后重试'): string {
  if (!err) return fallback
  const ax = err as AxiosError<ApiErrorBody>
  const msg = ax.response?.data?.message
  if (typeof msg === 'string' && msg.trim()) return msg.trim()
  if (err instanceof Error && err.message) return err.message
  return fallback
}
