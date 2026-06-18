<template>
  <div class="invite-hub" v-loading="loading">
    <div class="header glass-panel">
      <h1>召友中心</h1>
      <p>邀请好友一起玩，双方得币 · 冲周榜赢荣誉</p>
      <el-alert
        v-if="countdownLabel"
        type="warning"
        :closable="false"
        show-icon
        :title="countdownLabel"
      />
      <el-alert
        v-if="rankMoveHint"
        type="success"
        :closable="true"
        show-icon
        :title="rankMoveHint"
      />
    </div>

    <div v-if="me" class="invite-card glass-panel">
      <h2>我的邀请</h2>
      <MatchDayShareBar :status="inviteDailyStatus" class="invite-match-day-bar" />
      <div class="hero-share">
        <p v-if="me.next_tier" class="hero-hint">
          再邀 <strong>{{ me.next_tier.remaining }}</strong> 位有效好友解锁「{{ me.next_tier.title }}」
        </p>
        <p v-else class="hero-hint">
          有效邀请 {{ me.effective_invites }} 人 · 本季已赚 {{ me.season_coins_earned }} 币
        </p>
        <el-button type="primary" size="large" class="hero-cta" @click="openShareSheet">
          分享给好友
        </el-button>
        <span class="code-inline">邀请码 {{ me.invite_code }}</span>
      </div>
      <div class="stats-grid">
        <div class="stat"><span>有效邀请</span><strong>{{ me.effective_invites }}</strong></div>
        <div class="stat"><span>本季已赚</span><strong>{{ me.season_coins_earned }} 币</strong></div>
        <div class="stat"><span>本周榜分</span><strong>{{ me.week_score }}</strong></div>
        <div class="stat" v-if="me.weekly_rank?.rank"><span>本周排名</span><strong>第 {{ me.weekly_rank.rank }} 名</strong></div>
      </div>
      <div v-if="me.next_tier" class="tier-hint">
        再邀 <strong>{{ me.next_tier.remaining }}</strong> 位有效好友解锁「{{ me.next_tier.title }}」
      </div>
      <div v-if="me.recruitment_tiers?.length" class="tiers">
        <div
          v-for="t in me.recruitment_tiers"
          :key="t.count"
          class="tier-chip"
          :class="{ unlocked: t.unlocked }"
        >
          <strong>{{ t.title }}</strong>
          <span>{{ t.count }} 人 · {{ t.perk }}</span>
        </div>
      </div>
    </div>

    <div v-if="invites.length" class="friends glass-panel">
      <h2>好友进度</h2>
      <div v-for="inv in invites" :key="inv.invitee_id" class="friend-row">
        <div>
          <strong>{{ inv.nickname }}</strong>
          <span class="hint">{{ inv.next_hint || '已完成主要步骤' }}</span>
        </div>
        <div class="friend-actions">
          <span class="coins">已为你 +{{ inv.inviter_coins_earned }} 币</span>
          <el-button v-if="inv.nudge_text" size="small" plain @click="copyNudge(inv.nudge_text!)">
            复制提醒
          </el-button>
        </div>
      </div>
    </div>

    <div v-else-if="me && !loading" class="empty-friends glass-panel">
      <el-empty description="还没有好友通过你的链接加入">
        <p class="empty-tip">复制链接发给球友，对方注册并完成档案或首次竞猜后，才算有效邀请</p>
        <el-button type="primary" @click="openShareSheet">分享给好友</el-button>
      </el-empty>
    </div>

    <div v-if="rules" class="rules glass-panel">
      <h2>规则说明</h2>
      <p class="rules-summary">{{ rules.summary }}</p>
      <p v-if="rules.season_coin_cap" class="rules-cap">
        邀请人本季通过召友最多获得 <strong>{{ rules.season_coin_cap }}</strong> 球迷币（超出后里程碑不再发币，榜与军团仍累计）
      </p>
      <ul v-if="rules.milestones?.length" class="rules-list">
        <li v-for="m in rules.milestones" :key="m.key" class="rule-item">
          <span class="rule-step">{{ milestoneLabel(m) }}</span>
          <span class="rule-reward">{{ formatMilestoneReward(m) }}</span>
        </li>
      </ul>
      <div v-if="rules.weekly?.rank_rewards?.length" class="weekly-block">
        <h3>召友周榜奖励（每周一结算上周）</h3>
        <ul class="weekly-list">
          <li v-for="r in rules.weekly.rank_rewards" :key="r.rank">
            第 {{ r.rank }} 名 · +{{ r.points }} 荣誉积分
            <span v-if="r.coins"> · +{{ r.coins }} 球迷币</span>
          </li>
        </ul>
      </div>
      <p v-else-if="rules.weekly" class="rules-weekly">
        周榜前 {{ rules.weekly.settle_top_n }} 名有荣誉奖励
      </p>
    </div>

    <div v-if="me?.invitee_journey" class="journey glass-panel">
      <h2>{{ me.invitee_journey.inviter_nickname }} 邀你加入</h2>
      <p v-if="me.invitee_journey.next_step" class="journey-next">
        下一步：{{ me.invitee_journey.next_step.label }}
      </p>
      <div
        v-for="step in me.invitee_journey.steps"
        :key="step.key"
        class="step"
        :class="{ done: step.done, clickable: !step.done && step.action }"
        role="button"
        tabindex="0"
        @click="goStep(step)"
        @keydown.enter="goStep(step)"
      >
        {{ step.done ? '✓' : '○' }} {{ step.label }}
        <span v-if="step.reward_coins"> +{{ step.reward_coins }} 币</span>
        <span v-if="!step.done && step.action" class="step-go">去完成 →</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { usePageMeta } from '../composables/usePageMeta'

usePageMeta({ title: '召友中心 — 最后一舞', path: '/invite', noIndex: true })

import {
  getReferralInvites,
  getReferralMe,
  getReferralRules,
  type ReferralInvite,
  type ReferralMe,
  type ReferralRules,
  type InviteeJourneyStep,
} from '../api/referral'
import { showApiError } from '../utils/errorHandler'
import { formatMilestoneReward, milestoneLabel } from '../utils/referralRules'
import { useInviteShare } from '../composables/useInviteShare'
import MatchDayShareBar from '../components/MatchDayShareBar.vue'
import { fetchDailyStatus, useDailyStatusRef } from '../stores/dailyStatusStore'

const { openShareSheet } = useInviteShare()

const RANK_STORAGE_KEY = 'wc_referral_last_rank'

const router = useRouter()
const loading = ref(false)
const me = ref<ReferralMe | null>(null)
const invites = ref<ReferralInvite[]>([])
const rules = ref<ReferralRules | null>(null)
const rankMoveHint = ref<string | null>(null)
const inviteDailyStatus = useDailyStatusRef()

const countdownLabel = computed(() => {
  const sec = me.value?.seconds_until_weekly_settle
  if (sec == null) return null
  const days = Math.floor(sec / 86400)
  const hours = Math.floor((sec % 86400) / 3600)
  return `距周一周榜结算还有 ${days} 天 ${hours} 小时 · 仅计完成档案或首玩的好友`
})

function trackRankChange(rank: number | null | undefined) {
  if (rank == null) return
  try {
    const raw = sessionStorage.getItem(RANK_STORAGE_KEY)
    const prev = raw ? Number(raw) : null
    sessionStorage.setItem(RANK_STORAGE_KEY, String(rank))
    if (prev != null && rank < prev) {
      rankMoveHint.value = `你已超过 ${prev - rank} 位球友，升至第 ${rank} 名！`
    }
  } catch {
    /* ignore */
  }
}

async function load() {
  loading.value = true
  try {
    const [meData, inviteList, rulesData] = await Promise.all([
      getReferralMe(),
      getReferralInvites(),
      getReferralRules().catch(() => null),
      fetchDailyStatus(true).catch(() => null),
    ])
    me.value = meData
    invites.value = inviteList
    rules.value = rulesData
    trackRankChange(meData.weekly_rank?.rank)
  } catch (e) {
    showApiError(e)
  } finally {
    loading.value = false
  }
}

async function copyText(text: string, msg: string) {
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success(msg)
  } catch {
    ElMessage.warning('复制失败，请手动复制')
  }
}

function copyNudge(text: string) {
  const link = me.value?.invite_link ? `\n${me.value.invite_link}` : ''
  copyText(text + link, '提醒文案已复制')
}

function goStep(step: InviteeJourneyStep) {
  if (step.done || !step.action) return
  router.push(step.action)
}

onMounted(load)
</script>

<style scoped>
.invite-hub {
  max-width: 720px;
  margin: 0 auto;
  padding: 16px 20px 32px;
  background: transparent;
}
.header h1 { margin: 0 0 8px; }
.header p { margin: 0 0 12px; color: var(--wc-text-muted); }
.invite-card, .friends, .journey, .rules, .empty-friends {
  padding: 20px;
  margin-top: 16px;
}

.invite-match-day-bar {
  margin: 0 0 14px;
  width: 100%;
}

.hero-share {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  margin: 16px 0;
  text-align: center;
}
.hero-hint {
  margin: 0;
  font-size: 0.9rem;
  color: rgba(255, 255, 255, 0.78);
}
.hero-cta {
  width: 100%;
  max-width: 280px;
  min-height: 48px;
  font-weight: 700;
}
.code-inline {
  font-family: monospace;
  font-size: 0.85rem;
  color: var(--wc-text-muted);
  letter-spacing: 1px;
}
.code-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  margin: 12px 0;
}
.code {
  font-family: monospace;
  font-size: 1.2rem;
  letter-spacing: 2px;
  padding: 8px 12px;
  background: rgba(0,0,0,0.2);
  border-radius: 8px;
}
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 12px;
  margin: 16px 0;
}
.stat span { display: block; font-size: 12px; color: var(--wc-text-muted); }
.stat strong { font-size: 1.1rem; }
.tier-hint { margin: 12px 0; font-size: 14px; }
.tiers { display: flex; flex-wrap: wrap; gap: 8px; }
.tier-chip {
  padding: 8px 12px;
  border-radius: 8px;
  border: 1px solid rgba(255,255,255,0.1);
  font-size: 12px;
  opacity: 0.6;
}
.tier-chip.unlocked {
  opacity: 1;
  border-color: var(--wc-accent-gold);
}
.friend-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid rgba(255,255,255,0.06);
  gap: 12px;
  flex-wrap: wrap;
}
.friend-row .hint {
  display: block;
  font-size: 12px;
  color: var(--wc-text-muted);
  margin-top: 4px;
}
.friend-actions { display: flex; align-items: center; gap: 10px; }
.coins { font-size: 13px; color: var(--wc-accent-gold); }
.step {
  padding: 8px 0;
  font-size: 14px;
}
.step.clickable {
  cursor: pointer;
  border-radius: 6px;
  padding: 8px 10px;
  margin: 0 -10px;
}
.step.clickable:hover {
  background: rgba(212, 165, 116, 0.1);
}
.step.done { opacity: 0.7; }
.step-go {
  margin-left: 8px;
  font-size: 12px;
  color: var(--wc-accent-gold);
}
.journey-next {
  font-size: 13px;
  color: var(--wc-accent-gold);
  margin-bottom: 8px;
}
.empty-tip {
  font-size: 13px;
  color: var(--wc-text-muted);
  max-width: 320px;
  margin: 0 auto 12px;
}
.rules-summary {
  font-size: 14px;
  line-height: 1.6;
  margin: 0 0 12px;
  color: rgba(255, 255, 255, 0.78);
}
.rules-cap {
  margin: 0 0 14px;
  padding: 10px 12px;
  border-radius: 8px;
  font-size: 0.85rem;
  color: rgba(255, 255, 255, 0.65);
  background: rgba(212, 165, 116, 0.08);
  border: 1px solid rgba(212, 165, 116, 0.2);
}
.rules-cap strong {
  color: var(--wc-accent-gold);
}
.rules-list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.rule-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px 12px;
  border-radius: 10px;
  background: rgba(12, 14, 28, 0.45);
  border: 1px solid rgba(255, 255, 255, 0.08);
}
.rule-step {
  font-size: 0.9rem;
  font-weight: 600;
  color: #f0d9b5;
}
.rule-reward {
  font-size: 0.82rem;
  color: var(--wc-accent-gold);
}
.weekly-block {
  margin-top: 16px;
  padding-top: 14px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}
.weekly-block h3 {
  margin: 0 0 10px;
  font-size: 0.92rem;
  color: #f0d9b5;
}
.weekly-list {
  margin: 0;
  padding-left: 18px;
  font-size: 0.82rem;
  color: rgba(255, 255, 255, 0.7);
  line-height: 1.6;
}
.rules-weekly {
  margin-top: 12px;
  font-size: 13px;
  color: var(--wc-accent-gold);
}

@media (max-width: 768px) {
  .invite-hub {
    padding: 12px;
  }
  .stats-grid {
    grid-template-columns: 1fr 1fr;
  }
  .code-row {
    flex-direction: column;
  }
  .code-row .el-button {
    width: 100%;
    min-height: 44px;
  }
}

@media (max-width: 480px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }
}
</style>
