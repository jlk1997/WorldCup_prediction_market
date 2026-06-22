export const walletReasonLabels: Record<string, string> = {
  register_bonus: '注册赠送',
  signin: '每日签到',
  qq_group_join: '加入官方 QQ 群',
  quiz: '主队问答',
  ai_analysis: 'AI 分析',
  ai_analysis_refund: 'AI 分析退款',
  season_pass_daily: '通行证每日领币',
  cheer: '助威',
  predict_stake: '竞猜质押',
  predict_win: '竞猜猜中（累计）',
  predict_win_redeem: '竞猜猜中（可用）',
  predict_win_return: '竞猜返币',
  predict_void_refund: '流局退质押',
  free_predict_win: '免费竞猜奖励',
  redeem_purchase: '积分兑换',
  referral_tier_5: '召友档位奖励',
  recharge: '充值到账',
  purchase: '商城购买',
  nickname_change: '修改昵称',
  arena_boost: '擂台应援',
  referral_register_invitee: '邀请注册奖励',
  referral_profile_inviter: '好友完成档案',
  referral_profile_invitee: '完成档案奖励',
  referral_action_inviter: '好友首玩奖励',
  referral_action_invitee: '首玩奖励',
  referral_active_7d: '好友7日活跃',
  referral_same_team_inviter: '同主队扩编',
  referral_same_team_invitee: '同主队扩编',
  referral_weekly_rank: '召友周榜',
}

const pointReasonOverrides: Record<string, string> = {
  predict_win: '竞猜猜中（累计积分）',
  predict_win_redeem: '竞猜猜中（可用积分）',
  redeem_purchase: '积分兑换消费',
  referral_tier_5: '召友里程碑',
  referral_weekly_rank: '召友周榜荣誉分',
  card_buyback: '卡牌官方回购（可用积分）',
  market_sale: '交易行出售（可用积分）',
  market_buy: '交易行购买',
  collectible_set_reward: '套组奖励（可用积分）',
  card_stake_yield: '卡牌质押产出',
  card_duel_win: '卡牌对决奖励',
}

export function walletReasonLabel(code: string) {
  return walletReasonLabels[code] || code
}

export function pointReasonLabel(code: string) {
  return pointReasonOverrides[code] || walletReasonLabel(code)
}

export function formatLedgerTime(iso: string | null) {
  if (!iso) return '-'
  return iso.replace('T', ' ').slice(0, 16)
}
