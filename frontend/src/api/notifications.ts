import { apiClient } from './client'

export interface UserNotification {
  id: number
  category: string
  title: string
  body: string
  payload?: Record<string, unknown> | null
  read_at?: string | null
  created_at?: string | null
}

export async function getNotifications(params?: {
  unread_only?: boolean
  category?: string
  limit?: number
}) {
  const { data } = await apiClient.get<UserNotification[]>('/api/game/notifications', { params })
  return data
}

export async function getUnreadNotificationCount(category?: string) {
  const { data } = await apiClient.get<{ count: number }>('/api/game/notifications/unread-count', {
    params: category ? { category } : undefined,
  })
  return data.count
}

export async function markNotificationsRead(ids?: number[]) {
  const { data } = await apiClient.post<{ updated: number }>('/api/game/notifications/read', {
    ids: ids ?? null,
  })
  return data
}

export async function getPendingPredictionsCount() {
  const { data } = await apiClient.get<{ count: number }>('/api/game/pending-predictions-count')
  return data.count
}
