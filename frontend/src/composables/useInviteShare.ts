import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { getReferralMe, type ReferralMe } from '../api/referral'
import { authState } from '../stores/authStore'
import { downloadSharePoster, generateSharePosterObjectUrl } from '../utils/sharePoster'
import { trackEvent } from '../utils/analytics'

const sheetOpen = ref(false)
const loading = ref(false)
const posterLoading = ref(false)
const cachedMe = ref<ReferralMe | null>(null)
const posterPreviewUrl = ref<string | null>(null)

const CACHE_MS = 60_000
let cacheAt = 0
let posterGen = 0
let openRequest = 0

function revokePosterPreview() {
  if (posterPreviewUrl.value) {
    URL.revokeObjectURL(posterPreviewUrl.value)
    posterPreviewUrl.value = null
  }
}

export function buildInviteShareText(me: ReferralMe | null) {
  const nick = authState.user?.nickname || '我'
  const link = me?.invite_link || ''
  if (!link) return `${nick} 邀你一起玩世界杯竞猜，注册得球迷币`
  return `${nick} 邀你一起玩世界杯竞猜，注册得球迷币\n${link}`
}

function posterOptions(me: ReferralMe) {
  const nick = authState.user?.nickname || '球迷'
  const tierHint = me.next_tier
    ? `再邀 ${me.next_tier.remaining} 人解锁「${me.next_tier.title}」`
    : `有效邀请 ${me.effective_invites} 人 · 本季已赚 ${me.season_coins_earned} 币`
  return {
    title: `${nick} 邀你一起猜世界杯`,
    subtitle: '注册得球迷币 · 猜中冲榜赢积分',
    statsLine: tierHint,
    footer: '扫码或复制链接加入 · 最后一舞',
    qrUrl: me.invite_link,
  }
}

async function ensureMe(force = false): Promise<ReferralMe | null> {
  if (!authState.accessToken) return null
  const now = Date.now()
  if (!force && cachedMe.value && now - cacheAt < CACHE_MS) {
    return cachedMe.value
  }
  loading.value = true
  try {
    cachedMe.value = await getReferralMe()
    cacheAt = now
    return cachedMe.value
  } catch {
    return null
  } finally {
    loading.value = false
  }
}

async function refreshPosterPreview(me: ReferralMe) {
  const gen = ++posterGen
  posterLoading.value = true
  try {
    const url = await generateSharePosterObjectUrl(posterOptions(me))
    if (gen !== posterGen) return
    revokePosterPreview()
    posterPreviewUrl.value = url
  } finally {
    if (gen === posterGen) posterLoading.value = false
  }
}

/** Clear invite share cache on logout (avoid stale link/code). */
export function resetInviteShareState() {
  openRequest++
  posterGen++
  sheetOpen.value = false
  cachedMe.value = null
  cacheAt = 0
  loading.value = false
  posterLoading.value = false
  revokePosterPreview()
}

watch(sheetOpen, (open) => {
  if (!open) revokePosterPreview()
})

export function useInviteShare() {
  async function openShareSheet() {
    if (!authState.accessToken) {
      ElMessage.warning('请先登录后再分享')
      return
    }
    const req = ++openRequest
    const me = await ensureMe()
    if (req !== openRequest) return
    if (!me?.invite_link) {
      ElMessage.warning('暂时无法获取邀请链接，请稍后再试')
      return
    }
    trackEvent('share_open', { source: 'invite_sheet' })
    sheetOpen.value = true
    void refreshPosterPreview(me)
  }

  function closeShareSheet() {
    sheetOpen.value = false
  }

  async function copyText(text: string, okMsg: string) {
    try {
      await navigator.clipboard.writeText(text)
      ElMessage.success(okMsg)
      return true
    } catch {
      ElMessage.warning('复制失败，请手动复制')
      return false
    }
  }

  async function copyInviteLink() {
    const me = await ensureMe()
    if (!me?.invite_link) return false
    return copyText(me.invite_link, '邀请链接已复制')
  }

  async function copyInviteCode() {
    const me = await ensureMe()
    if (!me?.invite_code) return false
    return copyText(me.invite_code, '邀请码已复制')
  }

  async function copyShareText() {
    const me = await ensureMe()
    return copyText(buildInviteShareText(me), '分享文案已复制，去粘贴给好友吧')
  }

  async function shareInvite() {
    const me = await ensureMe()
    if (!me?.invite_link) {
      ElMessage.warning('无法获取邀请链接')
      return
    }
    const text = buildInviteShareText(me)
    if (typeof navigator.share === 'function') {
      try {
        await navigator.share({
          title: '最后一舞 · 世界杯竞猜',
          text: `${authState.user?.nickname || '我'} 邀你一起玩`,
          url: me.invite_link,
        })
        return
      } catch (e) {
        if ((e as Error).name === 'AbortError') return
      }
    }
    await copyText(text, '分享文案已复制，去微信粘贴给好友吧')
  }

  async function saveInvitePoster() {
    const me = await ensureMe()
    if (!me?.invite_link) {
      ElMessage.warning('无法生成海报')
      return
    }
    try {
      await downloadSharePoster(posterOptions(me))
      ElMessage.success('海报已保存')
    } catch {
      ElMessage.error('海报生成失败')
    }
  }

  function invalidateInviteCache() {
    cachedMe.value = null
    cacheAt = 0
  }

  return {
    sheetOpen,
    loading,
    posterLoading,
    cachedMe,
    posterPreviewUrl,
    ensureMe,
    openShareSheet,
    closeShareSheet,
    shareInvite,
    copyInviteLink,
    copyInviteCode,
    copyShareText,
    saveInvitePoster,
    buildInviteShareText,
    invalidateInviteCache,
  }
}
