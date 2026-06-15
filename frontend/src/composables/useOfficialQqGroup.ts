import { reactive } from 'vue'
import { getUiConfig } from '@/api/uiConfig'
import { claimQqGroupReward } from '@/api/commerce'
import { isLoggedIn } from '@/stores/authStore'

export interface OfficialQqGroupConfig {
  enabled: boolean
  group_name: string
  group_number: string
  qr_image_url: string
  reward_coins: number
  fab_label: string
  fab_hint?: string
  modal_title: string
  modal_subtitle: string
  steps?: string[]
}

const DEFAULT_CONFIG: OfficialQqGroupConfig = {
  enabled: true,
  group_name: '最后一舞足球',
  group_number: '941989773',
  qr_image_url: '/qq-group-qr.png',
  reward_coins: 50,
  fab_label: '官方群',
  fab_hint: '领币交流',
  modal_title: '加入官方 QQ 群',
  modal_subtitle: '看球交流 · 活动福利 · 问题反馈 · 第一时间获取更新',
  steps: [
    '长按或保存下方二维码',
    '打开 QQ 扫一扫，加入群聊',
    '回本站点击「我已加群」领取球迷币（每个账号一次）',
  ],
}

export const officialQqGroupConfig = reactive<OfficialQqGroupConfig>({ ...DEFAULT_CONFIG })

export const officialQqGroupState = reactive({
  modalOpen: false,
  claimed: false,
  claiming: false,
})

let configLoaded = false

export async function ensureOfficialQqGroupConfig() {
  if (configLoaded) return
  try {
    const cfg = await getUiConfig<OfficialQqGroupConfig>('official_qq_group')
    Object.assign(officialQqGroupConfig, { ...DEFAULT_CONFIG, ...cfg })
  } catch {
    Object.assign(officialQqGroupConfig, DEFAULT_CONFIG)
  }
  configLoaded = true
}

export function openOfficialQqGroupModal() {
  if (!officialQqGroupConfig.enabled) return
  officialQqGroupState.modalOpen = true
}

export function closeOfficialQqGroupModal() {
  officialQqGroupState.modalOpen = false
}

export function syncQqGroupClaimed(claimed: boolean | undefined) {
  if (claimed != null) officialQqGroupState.claimed = claimed
}

export async function claimOfficialQqGroupReward(): Promise<{
  ok: boolean
  coinsAdded: number
  needLogin?: boolean
}> {
  if (!isLoggedIn.value) {
    return { ok: false, coinsAdded: 0, needLogin: true }
  }
  if (officialQqGroupState.claimed || officialQqGroupState.claiming) {
    return { ok: false, coinsAdded: 0 }
  }
  officialQqGroupState.claiming = true
  try {
    const res = await claimQqGroupReward()
    officialQqGroupState.claimed = res.already_claimed || res.coins_added > 0
    return {
      ok: !res.already_claimed && res.coins_added > 0,
      coinsAdded: res.coins_added,
    }
  } finally {
    officialQqGroupState.claiming = false
  }
}
