import { API_BASE_URL } from './client'
import { authState, refreshSession } from '../stores/authStore'
import type { AgentAnalyzeResponse } from '@/types/api'

export interface AgentStreamEvent {
  type: string
  phase?: string
  message?: string
  elapsed_sec?: number
  queue?: { active?: number; limit?: number; source?: string }
  step?: { agent: string; action: string; output?: unknown }
  run_id?: number
  cached?: boolean
  status?: string
  data?: AgentAnalyzeResponse['data']
  validation_warnings?: string[]
  billing?: Record<string, unknown>
  status_code?: number
}

export interface AiBillingStatus {
  daily_free_limit: number
  free_used_today: number
  free_remaining: number
  fan_coins: number
  has_season_pass: boolean
  costs: { pre_match: number; live: number; force_refresh_extra: number }
}

async function authFetch(url: string, init: RequestInit, retried = false): Promise<Response> {
  const token = authState.accessToken
  const headers: Record<string, string> = {
    ...(init.headers as Record<string, string> | undefined),
  }
  if (token) headers.Authorization = `Bearer ${token}`

  const res = await fetch(url, { ...init, headers })
  if (res.status === 401 && !retried && authState.refreshToken) {
    const ok = await refreshSession()
    if (ok) return authFetch(url, init, true)
  }
  return res
}

export async function getAiBillingStatus(): Promise<AiBillingStatus> {
  const res = await authFetch(`${API_BASE_URL}/api/agent/billing-status`, {})
  if (!res.ok) throw new Error('无法加载 AI 计费信息')
  return res.json()
}

export interface BillingPreview {
  cache_hit: boolean
  data: {
    charge_coins: number
    used_free_quota: boolean
    free_remaining: number
    daily_free_limit: number
    mode: string
    force_refresh: boolean
  }
}

export async function getBillingPreview(body: {
  team1_name: string
  team2_name: string
  mode: string
  force_refresh: boolean
}): Promise<BillingPreview> {
  const res = await authFetch(`${API_BASE_URL}/api/agent/billing-preview`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error('无法预估本次扣费')
  return res.json()
}

const STREAM_TIMEOUT_MS = 360_000

export async function streamAgentAnalyze(
  body: { team1_name: string; team2_name: string; mode: string; force_refresh: boolean },
  onEvent: (event: AgentStreamEvent) => void,
  signal?: AbortSignal,
): Promise<AgentAnalyzeResponse & { billing?: Record<string, unknown> }> {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), STREAM_TIMEOUT_MS)
  const onExternalAbort = () => controller.abort()
  if (signal) {
    if (signal.aborted) controller.abort()
    else signal.addEventListener('abort', onExternalAbort, { once: true })
  }

  try {
  const res = await authFetch(`${API_BASE_URL}/api/agent/analyze/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal: controller.signal,
  })

  if (!res.ok) {
    let message = `分析请求失败 (${res.status})`
    try {
      const err = await res.json()
      message = err.message || message
    } catch {
      /* ignore */
    }
    throw new Error(message)
  }

  const reader = res.body?.getReader()
  if (!reader) throw new Error('浏览器不支持流式响应')

  const decoder = new TextDecoder()
  let buffer = ''
  let finalResult: (AgentAnalyzeResponse & { billing?: Record<string, unknown> }) | null = null

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const parts = buffer.split('\n\n')
    buffer = parts.pop() || ''

    for (const part of parts) {
      const line = part.trim()
      if (!line.startsWith('data:')) continue
      const payload = line.slice(5).trim()
      if (!payload) continue
      let event: AgentStreamEvent
      try {
        event = JSON.parse(payload) as AgentStreamEvent
      } catch {
        continue
      }
      onEvent(event)
      if (event.type === 'result') {
        finalResult = {
          status: event.status || 'success',
          cached: event.cached || false,
          run_id: event.run_id,
          data: event.data!,
          validation_warnings: event.validation_warnings,
          billing: event.billing,
        }
      }
      if (event.type === 'error') {
        throw new Error(event.message || '分析失败')
      }
    }
  }

  if (!finalResult) throw new Error('分析未完成，连接已关闭')
  return finalResult
  } finally {
    clearTimeout(timeoutId)
    if (signal) signal.removeEventListener('abort', onExternalAbort)
  }
}
