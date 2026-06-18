import { reactive } from 'vue'
import { getProfileStatus, getRecommendations, type ProfileStatus, type Recommendations } from '../api/profile'
import { authState, patchUserFields } from './authStore'
import { registerLogoutCleanup } from './logoutRegistry'

export const profileState = reactive({
  status: null as ProfileStatus | null,
  recommendations: null as Recommendations | null,
  loadedAt: 0,
})

const STALE_MS = 5 * 60 * 1000

export function syncAuthFromProfile(status?: ProfileStatus | null) {
  const s = status ?? profileState.status
  if (!s || !authState.user) return
  patchUserFields({
    profile_completed: s.profile_completed,
    fan_cheers_total: s.fan_cheers_total,
    fan_level: s.fan_level,
    favorite_team_id: s.main_team?.id ?? authState.user.favorite_team_id,
    secondary_team_id: s.secondary_team?.id ?? null,
  })
}

export async function fetchProfileStatus(force = false) {
  if (!force && profileState.status) return profileState.status
  profileState.status = await getProfileStatus()
  syncAuthFromProfile(profileState.status)
  return profileState.status
}

export async function fetchRecommendations(force = false) {
  const now = Date.now()
  if (!force && profileState.recommendations && now - profileState.loadedAt < STALE_MS) {
    return profileState.recommendations
  }
  profileState.recommendations = await getRecommendations()
  profileState.loadedAt = now
  const fi = profileState.recommendations?.fan_identity
  if (fi) {
    patchUserFields({
      profile_completed: fi.profile_completed,
      fan_cheers_total: fi.cheers_total,
      fan_level: fi.fan_level,
    })
  }
  return profileState.recommendations
}

export function clearProfileCache() {
  profileState.status = null
  profileState.recommendations = null
  profileState.loadedAt = 0
}

registerLogoutCleanup(clearProfileCache)
