import { reactive } from 'vue'
import type { CollectibleDropResult } from '@/api/collectible'
import { registerLogoutCleanup } from '@/stores/logoutRegistry'
import {
  GuidePriority,
  flushGuideQueue,
  notifyGuideClosed,
  notifyGuideOpened,
  registerGuide,
} from '@/composables/useGuideOrchestrator'

const COLLECTIBLE_REVEAL_ID = 'collectible-reveal'

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
  notifyGuideOpened(COLLECTIBLE_REVEAL_ID, GuidePriority.CollectibleReveal)
  if (typeof navigator !== 'undefined' && navigator.vibrate) {
    try {
      navigator.vibrate(12)
    } catch {
      /* ignore */
    }
  }
  return true
}

/** Build a drop payload from synthesis API `{ card }` response. */
export function buildSynthesisDrop(card: CollectibleDropResult['cards'][0]): CollectibleDropResult {
  return {
    dropped: true,
    cards: [{ ...card, owned: true }],
    shards: [],
    source: 'synthesis',
  }
}

export function closeCollectibleReveal() {
  collectibleRevealState.visible = false
  collectibleRevealState.drop = null
  collectibleRevealState.subtitle = ''
  notifyGuideClosed(COLLECTIBLE_REVEAL_ID)
  flushGuideQueue()
}

registerGuide(COLLECTIBLE_REVEAL_ID, {
  priority: GuidePriority.CollectibleReveal,
  isActive: () => collectibleRevealState.visible,
  open: () => {
    if (collectibleRevealState.drop) collectibleRevealState.visible = true
  },
})

export function resetCollectibleReveal() {
  closeCollectibleReveal()
}

registerLogoutCleanup(resetCollectibleReveal)
