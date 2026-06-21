/** Client-side rate-limit cooldown, parsing, and deduplicated global notifications. */

import { ElMessage } from 'element-plus'
import type { ApiErrorBody } from '../types/api'

const DEFAULT_COOLDOWN_MS = 60_000
const TOAST_DEDUPE_MS = 60_000

const DEFAULT_FRIENDLY_MESSAGE =
  '操作有点快了，请稍等一会儿再试。系统正在保护服务稳定性，不会影响已完成的操作。'

let pausedUntil = 0
let lastToastAt = 0
let lastRateLimitMessage: string | null = null

export class RateLimitError extends Error {
  readonly isRateLimit = true
  readonly notified: boolean
  readonly retryAfterMs: number

  constructor(message: string, notified = true, retryAfterMs = DEFAULT_COOLDOWN_MS) {
    super(message)
    this.name = 'RateLimitError'
    this.notified = notified
    this.retryAfterMs = retryAfterMs
  }
}

export function isRateLimitError(error: unknown): error is RateLimitError {
  return error instanceof RateLimitError || (error instanceof Error && error.name === 'RateLimitError')
}

export function isRateLimited(): boolean {
  return Date.now() < pausedUntil
}

export function getRateLimitRemainingMs(): number {
  return Math.max(0, pausedUntil - Date.now())
}

export function getLastRateLimitMessage(): string | null {
  if (!isRateLimited()) return null
  return lastRateLimitMessage
}

export function enterRateLimitCooldown(ms = DEFAULT_COOLDOWN_MS, message?: string) {
  pausedUntil = Math.max(pausedUntil, Date.now() + ms)
  if (message) lastRateLimitMessage = message
}

/** @deprecated use enterRateLimitCooldown */
export function pauseForRateLimit(ms = DEFAULT_COOLDOWN_MS) {
  enterRateLimitCooldown(ms)
}

export function parseRateLimitFromResponse(
  body: unknown,
  status?: number,
  retryAfterHeader?: string | number | null,
): { message: string; retryAfterMs: number } | null {
  const headerSec = _parseRetryAfterHeader(retryAfterHeader)
  if (status === 429) {
    const parsed = _bodyFields(body)
    return {
      message: parsed.message || DEFAULT_FRIENDLY_MESSAGE,
      retryAfterMs: headerSec ?? (parsed.retryAfterSec ?? 60) * 1000,
    }
  }
  const parsed = _bodyFields(body)
  if (parsed.code === 'RATE_LIMIT') {
    return {
      message: parsed.message || DEFAULT_FRIENDLY_MESSAGE,
      retryAfterMs: headerSec ?? (parsed.retryAfterSec ?? 60) * 1000,
    }
  }
  if (parsed.message && /过于频繁|too many requests|rate limit/i.test(parsed.message)) {
    return {
      message: parsed.message,
      retryAfterMs: headerSec ?? (parsed.retryAfterSec ?? 60) * 1000,
    }
  }
  return null
}

function _parseRetryAfterHeader(value: string | number | null | undefined): number | null {
  if (value == null || value === '') return null
  const sec = typeof value === 'number' ? value : parseInt(String(value), 10)
  if (!Number.isFinite(sec) || sec <= 0) return null
  return sec * 1000
}

function _bodyFields(body: unknown): {
  code?: string
  message?: string
  retryAfterSec?: number
} {
  if (!body || typeof body !== 'object') return {}
  const b = body as ApiErrorBody
  return {
    code: b.code,
    message: typeof b.message === 'string' ? b.message : undefined,
    retryAfterSec:
      typeof b.retry_after_sec === 'number' && b.retry_after_sec > 0
        ? b.retry_after_sec
        : undefined,
  }
}

/** @deprecated use parseRateLimitFromResponse */
export function rateLimitMessageFromBody(body: unknown): string | null {
  return parseRateLimitFromResponse(body)?.message ?? null
}

export function notifyRateLimitOnce(message?: string): boolean {
  const now = Date.now()
  if (now - lastToastAt < TOAST_DEDUPE_MS) return false
  lastToastAt = now
  ElMessage.warning({
    message: message || DEFAULT_FRIENDLY_MESSAGE,
    duration: 6000,
    showClose: true,
  })
  return true
}

/** Always show rate-limit feedback (e.g. login send-code). Bypasses global toast dedupe. */
export function notifyRateLimitExplicit(message: string, durationMs = 6000) {
  ElMessage.warning({
    message,
    duration: durationMs,
    showClose: true,
  })
}

export function handleRateLimitResponse(
  body: unknown,
  status?: number,
  retryAfterHeader?: string | number | null,
): RateLimitError | null {
  const parsed = parseRateLimitFromResponse(body, status, retryAfterHeader)
  if (!parsed) return null
  enterRateLimitCooldown(parsed.retryAfterMs, parsed.message)
  const notified = notifyRateLimitOnce(parsed.message)
  return new RateLimitError(parsed.message, notified, parsed.retryAfterMs)
}

export function rejectIfRateLimited(): RateLimitError | null {
  if (!isRateLimited()) return null
  const remainingSec = Math.ceil(getRateLimitRemainingMs() / 1000)
  const message =
    lastRateLimitMessage ||
    `操作过于频繁，请 ${remainingSec} 秒后再试`
  const notified = notifyRateLimitOnce(message)
  return new RateLimitError(message, notified, getRateLimitRemainingMs())
}

/** Test helper */
export function resetRateLimitGuardState() {
  pausedUntil = 0
  lastToastAt = 0
  lastRateLimitMessage = null
}

export function formatRateLimitCountdown(retryAfterMs?: number): string {
  const sec = Math.max(1, Math.ceil((retryAfterMs ?? getRateLimitRemainingMs()) / 1000))
  if (sec >= 3600) {
    const h = Math.floor(sec / 3600)
    const m = Math.ceil((sec % 3600) / 60)
    return m > 0 ? `${h} 小时 ${m} 分钟` : `${h} 小时`
  }
  if (sec >= 60) {
    const m = Math.floor(sec / 60)
    const s = sec % 60
    return s > 0 ? `${m} 分 ${s} 秒` : `${m} 分钟`
  }
  return `${sec} 秒`
}
