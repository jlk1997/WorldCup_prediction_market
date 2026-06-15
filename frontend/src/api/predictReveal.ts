import { apiClient } from './client'

export interface PredictRevealStateConfig {
  title: string
  match_template: string
  pick_template: string
  show_confetti?: boolean
}

export interface PredictRevealConfig {
  states: Record<string, PredictRevealStateConfig>
  buttons: {
    next_match: string
    share_fan_card: string
    view_records: string
    dismiss: string
  }
  hints: {
    loss_streak_protect: string
    loss_default: string
    void_no_score: string
    void_default: string
  }
  carousel: {
    enabled: boolean
    max_items: number
    swipe_threshold_px: number
  }
  score_template: string
  score_template_simple: string
}

export async function getPredictRevealConfig() {
  const { data } = await apiClient.get<PredictRevealConfig>('/api/game/predict-reveal-config')
  return data
}

export async function updatePredictRevealConfig(patch: Partial<PredictRevealConfig>) {
  const { data } = await apiClient.put<PredictRevealConfig>(
    '/api/game/admin/predict-reveal-config',
    patch,
  )
  return data
}
