import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import {
  getCollectibleShareUrl,
  type CardRarity,
  type CollectibleCardBrief,
} from '../api/collectible'
import { authState } from '../stores/authStore'
import { registerLogoutCleanup } from '../stores/logoutRegistry'
import { copyToClipboard } from '../utils/copyToClipboard'
import {
  DEFAULT_AI_HOOK,
  downloadSharePoster,
  generateSharePosterObjectUrl,
  type SharePosterOptions,
} from '../utils/sharePoster'
import { posterDisplayName } from '../utils/sharePosterDisplayName'
import { trackEvent } from '../utils/analytics'

export interface CollectibleShareOpenPayload {
  card: CollectibleCardBrief
  variant?: 'collectible' | 'set_complete'
  setName?: string
  subtitleOverride?: string
}

const sheetOpen = ref(false)
const loading = ref(false)
const posterLoading = ref(false)
const shareText = ref('')
const shareUrl = ref('')
const posterPreviewUrl = ref<string | null>(null)
const activeCard = ref<CollectibleCardBrief | null>(null)
const activeVariant = ref<'collectible' | 'set_complete'>('collectible')
const activeSetName = ref<string | undefined>()

let posterGen = 0
let openRequest = 0

function revokePosterPreview() {
  if (posterPreviewUrl.value) {
    URL.revokeObjectURL(posterPreviewUrl.value)
    posterPreviewUrl.value = null
  }
}

function shortHash(hash?: string | null) {
  if (!hash || hash.length < 12) return undefined
  return `${hash.slice(0, 6)}…${hash.slice(-4)}`
}

function buildPosterOptions(
  card: CollectibleCardBrief,
  url: string,
  variant: 'collectible' | 'set_complete',
  setName?: string,
): SharePosterOptions {
  const nick = posterDisplayName(authState.user?.nickname)
  const owned = card.owned !== false
  const chainMinted = card.chain?.status === 'minted'
  return {
    variant: variant === 'set_complete' ? 'set_complete' : 'collectible',
    displayName: nick,
    playerName: card.name,
    title:
      variant === 'set_complete' && setName
        ? `集齐「${setName}」`
        : owned
          ? `${nick} 收藏了 ${card.name}`
          : `${nick} 正在收集 ${card.name}`,
    subtitle: '最后一舞 · 球星收藏册',
    statsLine: owned && card.star ? `★${card.star}` : undefined,
    badge: variant === 'set_complete' ? '套组成就' : '数字藏品',
    footer: '虚拟收藏 · 可用积分流通 · 仅供炫耀',
    qrUrl: url,
    cardImageUrl: card.image_url || undefined,
    rarity: card.rarity as SharePosterOptions['rarity'],
    star: card.star ?? 0,
    owned,
    chainMinted,
    chainHashShort: shortHash(card.chain?.tx_hash),
    showAiPill: true,
    aiHookLine: DEFAULT_AI_HOOK,
  }
}

async function refreshPosterPreview(
  card: CollectibleCardBrief,
  url: string,
  variant: 'collectible' | 'set_complete',
  setName?: string,
) {
  const gen = ++posterGen
  posterLoading.value = true
  try {
    const preview = await generateSharePosterObjectUrl(buildPosterOptions(card, url, variant, setName))
    if (gen !== posterGen) return
    revokePosterPreview()
    posterPreviewUrl.value = preview
  } finally {
    if (gen === posterGen) posterLoading.value = false
  }
}

export function resetCollectibleShareState() {
  openRequest++
  posterGen++
  sheetOpen.value = false
  loading.value = false
  posterLoading.value = false
  shareText.value = ''
  shareUrl.value = ''
  activeCard.value = null
  revokePosterPreview()
}

registerLogoutCleanup(resetCollectibleShareState)

watch(sheetOpen, (open) => {
  if (!open) revokePosterPreview()
})

export function useCollectibleShare() {
  async function openShareSheet(payload: CollectibleShareOpenPayload) {
    if (!authState.accessToken) {
      ElMessage.warning('请先登录后再分享')
      return
    }
    const req = ++openRequest
    loading.value = true
    activeCard.value = payload.card
    activeVariant.value = payload.variant ?? 'collectible'
    activeSetName.value = payload.setName
    try {
      const data = await getCollectibleShareUrl(payload.card.code)
      if (req !== openRequest) return
      shareUrl.value = data.url
      shareText.value = payload.subtitleOverride
        ? `${data.share_text.split('\n')[0]}\n${payload.subtitleOverride}\n${data.url}`
        : data.share_text
      if (data.card) {
        activeCard.value = {
          ...payload.card,
          name: data.card.name,
          rarity: data.card.rarity,
          star: data.card.star,
          image_url: data.card.image_url,
          owned: data.owned,
        }
        if (data.card.chain_minted) {
          activeCard.value.chain = {
            ...(payload.card.chain ?? { enabled: true, chain_name: '文昌链' }),
            status: 'minted',
            tx_hash: data.card.chain_hash_short ?? payload.card.chain?.tx_hash,
          }
        }
      }
      sheetOpen.value = true
      trackEvent('collectible_share_open', {
        code: payload.card.code,
        owned: data.owned,
        variant: activeVariant.value,
      })
      void refreshPosterPreview(activeCard.value!, data.url, activeVariant.value, payload.setName)
    } catch {
      ElMessage.error('无法获取分享链接，请稍后再试')
    } finally {
      if (req === openRequest) loading.value = false
    }
  }

  function closeShareSheet() {
    sheetOpen.value = false
  }

  async function copyShareText() {
    const ok = await copyToClipboard(shareText.value)
    if (ok) {
      ElMessage.success('分享文案已复制')
      trackEvent('collectible_share_copy')
    } else {
      ElMessage.info('请手动复制文案')
    }
    return ok
  }

  async function copyLink() {
    if (!shareUrl.value) return false
    const ok = await copyToClipboard(shareUrl.value)
    if (ok) ElMessage.success('链接已复制')
    return ok
  }

  async function savePoster() {
    const card = activeCard.value
    if (!card || !shareUrl.value) return
    try {
      await downloadSharePoster(
        buildPosterOptions(card, shareUrl.value, activeVariant.value, activeSetName.value),
        `wc2026-card-${card.code}.png`,
      )
      ElMessage.success('海报已保存')
      trackEvent('collectible_share_save')
    } catch {
      ElMessage.error('海报生成失败')
    }
  }

  async function shareNative() {
    if (!shareUrl.value) return
    if (typeof navigator.share === 'function') {
      try {
        await navigator.share({
          title: '我的球星数字藏品',
          text: shareText.value,
          url: shareUrl.value,
        })
        return
      } catch (e) {
        if ((e as Error).name === 'AbortError') return
      }
    }
    await copyShareText()
  }

  const canNativeShare = typeof navigator !== 'undefined' && typeof navigator.share === 'function'

  return {
    sheetOpen,
    loading,
    posterLoading,
    shareText,
    shareUrl,
    posterPreviewUrl,
    activeCard,
    canNativeShare,
    openShareSheet,
    closeShareSheet,
    copyShareText,
    copyLink,
    savePoster,
    shareNative,
  }
}

export type { CardRarity }
