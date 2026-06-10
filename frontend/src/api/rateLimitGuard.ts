/** Client-side backoff when backend returns rate-limit errors. */

const RATE_LIMIT_PAUSE_MS = 60_000

let pausedUntil = 0

export function isRateLimited(): boolean {
  return Date.now() < pausedUntil
}

export function pauseForRateLimit(ms = RATE_LIMIT_PAUSE_MS) {
  pausedUntil = Math.max(pausedUntil, Date.now() + ms)
}

export function rateLimitMessageFromBody(body: unknown): string | null {
  if (!body || typeof body !== 'object') return null
  const msg = (body as { message?: unknown }).message
  if (typeof msg !== 'string') return null
  return /过于频繁|too many requests|rate limit/i.test(msg) ? msg : null
}
