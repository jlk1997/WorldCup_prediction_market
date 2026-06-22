import { ref } from 'vue'
import { ElMessageBox } from 'element-plus'
import { useRouter } from 'vue-router'
import { getRealNameStatus } from '@/api/asset'

let cached: boolean | null = null

export function invalidateRealnameCache() {
  cached = null
}

/** 流通操作前实名校验，未认证则引导至我的资产页。 */
export function useAssetRealname() {
  const router = useRouter()
  const checking = ref(false)

  async function ensureVerified(actionLabel: string): Promise<boolean> {
    if (cached === null) {
      checking.value = true
      try {
        cached = (await getRealNameStatus()).verified
      } catch {
        cached = false
      } finally {
        checking.value = false
      }
    }
    if (cached) return true
    try {
      await ElMessageBox.confirm(
        `进行「${actionLabel}」需先完成实名认证（合规要求）。是否前往认证？`,
        '实名认证',
        {
          customClass: 'wc-message-box',
          roundButton: true,
          confirmButtonText: '去认证',
          cancelButtonText: '稍后再说',
          type: 'info',
        },
      )
      await router.push('/me/assets')
    } catch {
      /* cancelled */
    }
    return false
  }

  return { ensureVerified, invalidateCache: invalidateRealnameCache, checking }
}
