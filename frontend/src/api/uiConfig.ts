import { apiClient } from './client'

export interface GuideStep {
  icon?: string
  title: string
  desc?: string
  bullets?: string[]
  highlight?: string
}

export interface GuideModalConfig {
  enabled: boolean
  version: number
  storage_key: string
  trigger: {
    require_login?: boolean
    require_profile?: boolean
    routes?: string[]
    auto_open?: boolean
    show_once?: boolean
    delay_ms?: number
    query_param?: string
  }
  dialog: {
    badge?: string
    title: string
    subtitle?: string
  }
  steps: GuideStep[]
  footer: {
    skip?: string
    prev?: string
    next?: string
    finish?: string
    secondary_finish?: string
  }
  finish_action?: {
    primary_route?: string
    secondary_route?: string
  }
}

export async function getUiConfig<T = Record<string, unknown>>(configKey: string) {
  const { data } = await apiClient.get<T>(`/api/ui-config/${configKey}`)
  return data
}
