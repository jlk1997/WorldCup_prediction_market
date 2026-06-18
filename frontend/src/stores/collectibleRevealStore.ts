import { reactive } from 'vue'
import type { CollectibleDropResult } from '@/api/collectible'

export const collectibleRevealState = reactive({
  visible: false,
  drop: null as CollectibleDropResult | null,
  subtitle: '' as string,
})

const SOURCE_LABELS: Record<string, string> = {
  predict_win: '猜中掉落',
  signin: '连签里程碑',
  matchday: '比赛日动员',
  referral: '召友奖励',
  synthesis: '碎片合成',
}

export function openCollectibleReveal(
  drop: CollectibleDropResult | null | undefined,
  options?: { subtitle?: string },
) {
  if (!drop?.dropped || !drop.cards?.length) return false
  collectibleRevealState.drop = drop
  collectibleRevealState.subtitle =
    options?.subtitle || SOURCE_LABELS[drop.source] || '获得数字藏品'
  collectibleRevealState.visible = true
  return true
}

export function closeCollectibleReveal() {
  collectibleRevealState.visible = false
  collectibleRevealState.drop = null
  collectibleRevealState.subtitle = ''
}
