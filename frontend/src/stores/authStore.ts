import { computed, reactive } from 'vue'
import { apiClient, isRateLimitError } from '../api/client'
import type { ReferralLoginInfo } from '../api/referral'
import { runLogoutCleanups } from './logoutRegistry'

export interface AuthUser {
  id: number
  email: string
  nickname: string
  avatar_url?: string | null
  fan_coins: number
  season_points: number
  redeem_points?: number
  extra_free_predict_daily?: number
  win_streak: number
  level: number
  favorite_team_id: number | null
  secondary_team_id?: number | null
  profile_completed?: boolean
  fan_cheers_total?: number
  fan_level?: number
  battalion_points_season?: number
  arena_tier?: string
  has_season_pass: boolean
  has_active_season_pass?: boolean
  season_pass_until: string | null
  avatar_frame?: string | null
  theme_key?: string | null
  last_signin_date?: string | null
  signin_streak?: number
}

const STORAGE_KEY = 'wc_auth'

interface AuthState {
  accessToken: string | null
  refreshToken: string | null
  user: AuthUser | null
  loading: boolean
  /** 首屏 initAuth 完成后为 true，避免 localStorage 残留 token 闪现用户 UI */
  authInitialized: boolean
}

function loadStored(): Partial<Pick<AuthState, 'accessToken' | 'refreshToken' | 'user'>> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return {}
    return JSON.parse(raw)
  } catch {
    return {}
  }
}

function persist() {
  localStorage.setItem(
    STORAGE_KEY,
    JSON.stringify({
      accessToken: authState.accessToken,
      refreshToken: authState.refreshToken,
      user: authState.user,
    })
  )
}

const stored = loadStored()

export const authState = reactive<AuthState>({
  accessToken: stored.accessToken ?? null,
  refreshToken: stored.refreshToken ?? null,
  user: stored.user ?? null,
  loading: false,
  authInitialized: false,
})

/** 会话已校验：token + user 且已完成首屏 initAuth */
export const isLoggedIn = computed(
  () => authState.authInitialized && !!authState.accessToken && !!authState.user,
)

/** 首屏正在从 localStorage 恢复并校验 token */
export const isAuthBootstrapping = computed(() => !authState.authInitialized)

export function getAccessToken(): string | null {
  return authState.accessToken
}

export function setSession(access: string, refresh: string, user: AuthUser) {
  authState.accessToken = access
  authState.refreshToken = refresh
  authState.user = user
  persist()
}

export function logout() {
  authState.accessToken = null
  authState.refreshToken = null
  authState.user = null
  localStorage.removeItem(STORAGE_KEY)
  try {
    sessionStorage.removeItem('wc_home_predict_redirect_done')
    sessionStorage.removeItem('wc_second_predict_coach_shown')
  } catch {
    /* ignore */
  }
  runLogoutCleanups()
}

export function patchUserFields(fields: Partial<AuthUser>) {
  if (!authState.user) return
  Object.assign(authState.user, fields)
  persist()
}

let fetchMeInflight: Promise<AuthUser | null> | null = null

export async function fetchMe(): Promise<AuthUser | null> {
  if (!authState.accessToken) return null
  if (fetchMeInflight) return fetchMeInflight

  fetchMeInflight = (async () => {
    authState.loading = true
    try {
      const { data } = await apiClient.get<AuthUser>('/api/auth/me')
      authState.user = data
      persist()
      return data
    } catch (e) {
      if (isRateLimitError(e)) {
        return authState.user
      }
      logout()
      return null
    } finally {
      authState.loading = false
      fetchMeInflight = null
    }
  })()

  return fetchMeInflight
}

export async function sendCode(email: string, ageConfirmed = true) {
  await apiClient.post('/api/auth/send-code', { email, age_confirmed: ageConfirmed })
}

export async function verifyCode(
  email: string,
  code: string,
  ageConfirmed = true,
  inviteCode?: string
) {
  const { data } = await apiClient.post<{
    access_token: string
    refresh_token: string
    user: AuthUser
    is_new: boolean
    referral?: ReferralLoginInfo | null
  }>('/api/auth/verify', {
    email,
    code,
    age_confirmed: ageConfirmed,
    invite_code: inviteCode || undefined,
  })
  setSession(data.access_token, data.refresh_token, data.user)
  return data
}

export async function refreshSession(): Promise<boolean> {
  if (!authState.refreshToken) return false
  try {
    const { data } = await apiClient.post<{ access_token: string; refresh_token: string }>(
      '/api/auth/refresh',
      { refresh_token: authState.refreshToken }
    )
    authState.accessToken = data.access_token
    authState.refreshToken = data.refresh_token
    persist()
    return true
  } catch {
    logout()
    return false
  }
}

let initPromise: Promise<void> | null = null

export async function initAuth(): Promise<void> {
  if (!initPromise) {
    initPromise = (async () => {
      try {
        if (authState.accessToken) {
          await fetchMe()
        } else if (authState.user) {
          authState.user = null
          persist()
        }
      } finally {
        authState.authInitialized = true
      }
    })()
  }
  return initPromise
}
