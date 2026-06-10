import { apiClient } from './client'

export interface NewsArticle {
  id: number
  title: string
  url: string | null
  source: string | null
  published_at: string | null
  summary: string | null
  thumbnail_url?: string | null
  lang: string
  team_tags?: string[] | null
  for_my_team?: boolean
  for_sub_team?: boolean
}

export async function getNews(params?: {
  lang?: string
  team?: string
  limit?: number
  personalize?: boolean
}) {
  const { data } = await apiClient.get<NewsArticle[]>('/api/news', { params })
  return data
}

export interface NewsStats {
  en: number
  zh: number
  total: number
}

export async function getNewsStats() {
  const { data } = await apiClient.get<NewsStats>('/api/news/stats')
  return data
}
