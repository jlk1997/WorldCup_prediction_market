import { reactive } from 'vue'
import {
  getPredictRevealConfig,
  type PredictRevealConfig,
} from '@/api/predictReveal'

const DEFAULT_CONFIG: PredictRevealConfig = {
  states: {
    won: {
      title: '猜中了！',
      match_template: '{team1} vs {team2}',
      pick_template: '{team1} vs {team2} · 你选「{pick}」',
      show_confetti: true,
    },
    lost: {
      title: '差一点',
      match_template: '{team1} vs {team2}',
      pick_template: '{team1} vs {team2} · 你选「{pick}」',
      show_confetti: false,
    },
    void: {
      title: '流局退款',
      match_template: '{team1} vs {team2}',
      pick_template: '{team1} vs {team2} · 你选「{pick}」',
      show_confetti: false,
    },
  },
  buttons: {
    next_match: '去猜下一场',
    share_fan_card: '分享球迷名片',
    view_records: '查看流水',
    dismiss: '知道了',
  },
  hints: {
    loss_streak_protect: '连败保护已生效：下次猜中积分有额外加成，继续加油！',
    loss_default: '下次继续加油，下一场还有机会。',
    void_no_score: '比赛完场超过 72 小时仍无比分，质押已原路退还。',
    void_default: '比赛推迟或取消，质押已退还。',
  },
  carousel: { enabled: true, max_items: 10, swipe_threshold_px: 50 },
  score_template: '赛果 {score}（{result}）',
  score_template_simple: '赛果 {score}',
}

export const predictRevealConfig = reactive<PredictRevealConfig>({ ...DEFAULT_CONFIG })

let loaded = false
let loading: Promise<void> | null = null

export function ensurePredictRevealConfig() {
  if (loaded) return Promise.resolve()
  if (loading) return loading
  loading = getPredictRevealConfig()
    .then((cfg) => {
      Object.assign(predictRevealConfig, cfg)
      loaded = true
    })
    .catch(() => {
      Object.assign(predictRevealConfig, DEFAULT_CONFIG)
    })
    .finally(() => {
      loading = null
    })
  return loading
}

export function resetPredictRevealConfigCache() {
  loaded = false
}
