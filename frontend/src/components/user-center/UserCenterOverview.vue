<template>
  <div class="uc-overview">
    <div class="identity-bar glass-panel">
      <div class="identity-left">
        <div class="avatar" :class="avatarFrameClass(user?.avatar_frame)">
          {{ (user?.nickname || '?').slice(0, 1) }}
        </div>
        <div class="identity-text">
          <div class="name-row">
            <strong>{{ user?.nickname }}</strong>
            <span v-if="profileStatus" class="level-tag">Lv.{{ profileStatus.fan_level }}</span>
          </div>
          <p class="sub-line">
            <span class="email">{{ user?.email }}</span>
            <span v-if="passActive" class="pass-dot active">通行证生效</span>
            <span v-else-if="passExpired" class="pass-dot expired">通行证已过期</span>
          </p>
        </div>
      </div>
      <button
        v-if="profileStatus?.main_team"
        type="button"
        class="team-btn"
        @click="$router.push('/onboarding')"
      >
        ⚽ {{ profileStatus.main_team.name }}
      </button>
      <button v-else type="button" class="team-btn muted" @click="$router.push('/onboarding')">
        设置主队
      </button>
    </div>

    <FanRecommendationsBar
      v-if="showRecommendations"
      :max="2"
      :daily-status="dailyStatus"
    />

    <CollectionPassNudgeBar :status="dailyStatus" />

    <TodayTasksCard
      :status="dailyStatus"
      :quiz="quiz"
      :quiz-load-failed="quizLoadFailed"
      :focus-key="focusKey"
      :signing="signing"
      @signin="$emit('signin')"
      @answer-quiz="$emit('answer-quiz', $event)"
      @reload-quiz="$emit('reload-quiz')"
    />

    <AssetSummaryRow :user="user" />

    <div class="quick-grid">
      <button type="button" class="quick-btn" @click="$router.push('/predict')">
        <span class="quick-icon">🎯</span>
        <span>去竞猜</span>
      </button>
      <button type="button" class="quick-btn" @click="$router.push('/arena')">
        <span class="quick-icon">🏟</span>
        <span>球迷擂台</span>
      </button>
      <button type="button" class="quick-btn" @click="$router.push('/collection?tab=pass')">
        <span class="quick-icon">📖</span>
        <span>藏品手册</span>
      </button>
      <button type="button" class="quick-btn" @click="$router.push('/shop')">
        <span class="quick-icon">🛒</span>
        <span>球迷商城</span>
      </button>
      <button type="button" class="quick-btn" @click="openInviteShare">
        <span class="quick-icon">👥</span>
        <span>召友中心</span>
        <el-badge v-if="referralUnread" :value="referralUnread" class="invite-badge" />
      </button>
    </div>

    <div v-if="inviteSummary" class="invite-strip glass-inner" @click="openInviteShare">
      <span v-if="inviteSummary.next_tier">
        再邀 {{ inviteSummary.next_tier.remaining }} 人解锁「{{ inviteSummary.next_tier.title }}」
      </span>
      <span v-else>
        有效邀请 {{ inviteSummary.effective_invites }} 人 · 本季已赚 {{ inviteSummary.season_coins_earned }} 币
      </span>
      <el-icon><ArrowRight /></el-icon>
    </div>

    <div class="more-links">
      <button type="button" @click="$router.push('/me/card')">球迷名片</button>
      <span class="sep">·</span>
      <button type="button" @click="$router.push({ path: '/shop', query: { tab: 'redeem' } })">积分兑换</button>
      <span class="sep">·</span>
      <button type="button" @click="$emit('go-tab', 'records')">我的竞猜</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { ArrowRight } from '@element-plus/icons-vue'
import FanRecommendationsBar from '../FanRecommendationsBar.vue'
import CollectionPassNudgeBar from '../collectible/CollectionPassNudgeBar.vue'
import TodayTasksCard from './TodayTasksCard.vue'
import AssetSummaryRow from './AssetSummaryRow.vue'
import type { AuthUser } from '../../stores/authStore'
import type { ProfileStatus } from '../../api/profile'
import type { DailyStatus } from '../../api/commerce'
import type { ReferralMe } from '../../api/referral'
import { avatarFrameClass } from '../../utils/entitlements'
import { useInviteShare } from '../../composables/useInviteShare'

const { openShareSheet } = useInviteShare()

function openInviteShare() {
  openShareSheet()
}

const props = defineProps<{
  user: AuthUser | null
  profileStatus: ProfileStatus | null | undefined
  dailyStatus: DailyStatus | null
  quiz: Record<string, unknown> | null
  quizLoadFailed?: boolean
  focusKey?: string | null
  signing?: boolean
  passActive?: boolean
  passExpired?: boolean
  referralUnread?: number
  inviteSummary?: Pick<ReferralMe, 'effective_invites' | 'season_coins_earned' | 'next_tier'> | null
}>()

defineEmits<{
  signin: []
  'answer-quiz': [idx: number]
  'reload-quiz': []
  'go-tab': [tab: string]
}>()

const showRecommendations = computed(() => {
  const action = props.dailyStatus?.next_action
  if (!action) return true
  return !['signin', 'quiz', 'pending'].includes(action.key)
})
</script>

<style scoped>
.uc-overview {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.identity-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
  margin-bottom: 12px;
  position: sticky;
  top: 0;
  z-index: 10;
}

.identity-left {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
  flex: 1;
}

.avatar {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--wc-accent-rose), var(--wc-accent-gold));
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.1rem;
  font-weight: 700;
  flex-shrink: 0;
  color: #1a1208;
}

.avatar.frame-gold_wc {
  box-shadow: 0 0 0 2px #e8c88a, 0 0 10px rgba(212, 165, 116, 0.4);
}

.avatar.frame-silver_wc {
  box-shadow: 0 0 0 2px #c0c0c0, 0 0 8px rgba(200, 200, 200, 0.35);
}

.identity-text {
  min-width: 0;
}

.name-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.name-row strong {
  font-size: 1rem;
  color: #f5f0e8;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.level-tag {
  flex-shrink: 0;
  font-size: 0.68rem;
  padding: 2px 6px;
  border-radius: 6px;
  background: rgba(212, 165, 116, 0.15);
  color: var(--wc-accent-gold);
}

.sub-line {
  margin: 4px 0 0;
  font-size: 0.72rem;
  color: rgba(255, 255, 255, 0.5);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pass-dot {
  margin-left: 6px;
}

.pass-dot.active {
  color: #8fd48a;
}

.pass-dot.expired {
  color: var(--wc-text-muted);
}

.team-btn {
  flex-shrink: 0;
  padding: 6px 10px;
  border-radius: 10px;
  border: 1px solid rgba(212, 165, 116, 0.3);
  background: rgba(212, 165, 116, 0.1);
  color: var(--wc-accent-gold);
  font-size: 0.78rem;
  font-weight: 600;
  cursor: pointer;
  max-width: 110px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.team-btn.muted {
  color: var(--wc-text-muted);
  border-color: rgba(255, 255, 255, 0.12);
}

.quick-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
  margin-bottom: 12px;
}

.quick-btn {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  min-height: 72px;
  padding: 8px 4px;
  border-radius: 12px;
  border: 1px solid rgba(212, 165, 116, 0.25);
  background: rgba(18, 22, 36, 0.75);
  color: #f5f0e8;
  font-size: 0.72rem;
  font-weight: 600;
  cursor: pointer;
}

.quick-btn:hover {
  border-color: var(--wc-accent-gold);
  background: rgba(212, 165, 116, 0.1);
}

.quick-icon {
  font-size: 1.25rem;
}

.invite-strip {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 12px;
  margin-bottom: 10px;
  border-radius: 10px;
  font-size: 0.78rem;
  color: rgba(255, 255, 255, 0.75);
  cursor: pointer;
  border: 1px solid rgba(212, 165, 116, 0.2);
}

.more-links {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 8px 0 4px;
  font-size: 0.78rem;
}

.more-links button {
  border: none;
  background: none;
  color: var(--wc-accent-gold);
  cursor: pointer;
  padding: 4px;
}

.more-links button:hover {
  text-decoration: underline;
}

.sep {
  color: rgba(255, 255, 255, 0.25);
}

@media (max-width: 768px) {
  .quick-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
