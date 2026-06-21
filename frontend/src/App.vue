<template>
  <div class="app-wrapper" :class="[themeClass, { 'is-mobile': isMobile }]">
    <LegendsPageBackdrop />

    <el-container class="layout-container">
      <el-header class="app-header safe-area-top">
        <router-link
          to="/"
          class="logo"
          :class="{ 'logo--mobile': isMobile }"
          aria-label="最后一舞 世界杯2026 首页"
        >
          <AppLogo class="logo-img" />
          <div class="brand-text">
            <span class="title-main">最后一舞</span>
            <span v-if="!isMobile" class="title-sub">世界杯2026</span>
          </div>
        </router-link>

        <div class="header-right">
          <!-- 桌面端完整顶栏 -->
          <StadiumModeSelector class="hide-mobile" />

          <div v-if="isLoggedIn && authState.user?.profile_completed && mainTeamName" class="team-chip hide-mobile" @click="router.push('/me')">
            ⚽ {{ mainTeamName }}
          </div>
          <div v-else-if="showProfileHeaderChip" class="team-chip incomplete hide-mobile" @click="router.push('/onboarding')">
            完善档案
          </div>

          <PredictSettlementNotifier class="hide-mobile" />
          <CollectibleNotifier class="hide-mobile" />
          <ReferralNotifier class="hide-mobile" />

          <div
            v-if="isLoggedIn"
            class="user-chip hide-mobile"
            :class="avatarFrameClass"
            @click="router.push('/me')"
          >
            <span class="coins">{{ authState.user?.fan_coins ?? 0 }} 币</span>
            <span class="redeem-pts">{{ authState.user?.redeem_points ?? 0 }} 可用分</span>
            <span class="nick">{{ authState.user?.nickname }}</span>
            <span class="me-label">球迷中心</span>
          </div>
          <el-button v-else type="primary" plain size="small" class="hide-mobile" @click="router.push('/login')">登录</el-button>

          <!-- 移动端精简顶栏 -->
          <div v-if="isMobile" class="mobile-header-actions hide-desktop-flex">
            <div class="mobile-header-scroll">
              <button
                v-if="isLoggedIn"
                type="button"
                class="mobile-me-chip touch-target"
                :class="avatarFrameClass"
                aria-label="进入球迷中心"
                @click="router.push('/me')"
              >
                <span class="mobile-me-avatar">
                  <span class="mobile-avatar-letter">{{ mobileAvatarInitial }}</span>
                  <span v-if="passActive" class="pass-badge">通</span>
                </span>
                <span class="mobile-me-text">
                  <span class="mobile-me-nick">{{ mobileDisplayNick }}</span>
                  <span class="mobile-me-label">球迷中心 ›</span>
                </span>
              </button>
              <CollectibleNotifier v-if="isLoggedIn" />
              <ReferralNotifier v-if="isLoggedIn" />
              <PredictSettlementNotifier v-if="isLoggedIn" />
              <button
                v-if="isLoggedIn"
                type="button"
                class="mobile-balance-chip touch-target"
                aria-label="球迷币与积分，点击进入商城"
                @click="router.push('/shop')"
              >
                <span class="balance-row">
                  <span class="coin-icon">🪙</span>
                  <span class="coins">{{ authState.user?.fan_coins ?? 0 }}</span>
                  <span class="balance-divider">·</span>
                  <span class="pts-inline">{{ authState.user?.redeem_points ?? 0 }} 分</span>
                </span>
              </button>
              <el-button v-else type="primary" plain size="small" class="mobile-login-btn" @click="router.push('/login')">
                登录
              </el-button>
            </div>
            <button
              type="button"
              class="mobile-more-btn touch-target"
              :class="{ 'has-alert': showProfileHeaderChip }"
              aria-label="打开更多菜单"
              @click="moreOpen = true"
            >
              <span class="more-icon-bars" aria-hidden="true">
                <span /><span /><span />
              </span>
              <span class="more-label">菜单</span>
            </button>
          </div>

          <el-menu
            mode="horizontal"
            :router="true"
            :default-active="$route.path"
            class="nav-menu desktop-nav hide-mobile"
            background-color="transparent"
            text-color="#9a94a8"
            active-text-color="#d4a574"
          >
            <el-menu-item index="/">赛事大屏</el-menu-item>
            <el-menu-item index="/live">赛事中心</el-menu-item>
            <el-menu-item index="/predict">竞猜</el-menu-item>
            <el-menu-item index="/arena">擂台</el-menu-item>
            <el-menu-item index="/leaderboard">排行榜</el-menu-item>
            <el-menu-item index="/agent">
              AI 工作台
              <span v-if="aiNeedsPredictFirst" class="nav-hint-badge">先猜</span>
            </el-menu-item>
            <el-menu-item index="/news">资讯</el-menu-item>
            <el-menu-item index="/teams">球队库</el-menu-item>
            <el-menu-item v-if="isLoggedIn" index="/invite">召友</el-menu-item>
            <el-menu-item v-if="isLoggedIn" index="/collection">收藏册</el-menu-item>
            <el-menu-item index="/shop">商城</el-menu-item>
            <el-menu-item v-if="isLoggedIn" index="/me">球迷中心</el-menu-item>
          </el-menu>

          <el-dropdown class="mobile-nav tablet-nav hide-mobile" trigger="click" @command="onNav">
            <el-button circle class="touch-target" aria-label="打开导航菜单">
              <el-icon><Menu /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="/">赛事大屏</el-dropdown-item>
                <el-dropdown-item command="/live">赛事中心</el-dropdown-item>
                <el-dropdown-item command="/predict">竞猜</el-dropdown-item>
                <el-dropdown-item command="/arena">擂台</el-dropdown-item>
                <el-dropdown-item command="/leaderboard">排行榜</el-dropdown-item>
                <el-dropdown-item command="/agent">
                  AI 工作台<span v-if="aiNeedsPredictFirst"> · 先猜</span>
                </el-dropdown-item>
                <el-dropdown-item command="/news">资讯</el-dropdown-item>
                <el-dropdown-item command="/teams">球队库</el-dropdown-item>
                <el-dropdown-item v-if="isLoggedIn" command="/collection">球星收藏册</el-dropdown-item>
                <el-dropdown-item command="/shop">商城</el-dropdown-item>
                <el-dropdown-item v-if="isLoggedIn" command="/invite">召友中心</el-dropdown-item>
                <el-dropdown-item v-if="isLoggedIn" command="/me">球迷中心</el-dropdown-item>
                <el-dropdown-item v-else command="/login">登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <RateLimitBanner />

      <el-main
        class="main-content safe-area-bottom"
        :class="{
          'is-dashboard': $route.path === '/',
          'is-auth-flow': isAuthFlow,
          'has-bottom-nav': isMobile && !isAuthFlow,
        }"
      >
        <ProfileIncompleteBanner v-if="showProfileBannerVisible" @dismiss="profileBannerHidden = true" />
        <router-view></router-view>
      </el-main>

      <el-footer v-if="!isMobile" class="app-footer safe-area-bottom">
        <router-link to="/legal/terms">用户协议</router-link>
        <span class="sep">·</span>
        <router-link to="/legal/privacy">隐私政策</router-link>
        <span class="sep">·</span>
        <router-link to="/legal/ai">AI 使用说明</router-link>
        <span class="sep">·</span>
        <span class="muted">虚拟道具不可提现</span>
      </el-footer>
    </el-container>

    <MobileBottomNav v-if="isMobile && !isAuthFlow" />
    <MobileMoreDrawer v-model="moreOpen" :show-profile-chip="showProfileHeaderChip" />
    <LeaderboardRewardDialog v-model="showRewardDialog" />
    <InviteShareSheet />
    <PredictShareSheet />
    <CollectibleShareSheet />
    <PredictSettlementReveal />
    <CollectibleDropHost />
    <SecondPredictCoach v-if="isLoggedIn" :status="lastDailyStatus" />
    <OnboardingTour v-if="showFeatureTour" />
    <GuideModal />
    <OfficialQqGroupFab />
    <OfficialQqGroupModal />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Menu } from '@element-plus/icons-vue'
import StadiumModeSelector from './components/StadiumModeSelector.vue'
import AppLogo from './components/AppLogo.vue'
import OnboardingTour from './components/OnboardingTour.vue'
import GuideModal from './components/GuideModal.vue'
import OfficialQqGroupFab from './components/OfficialQqGroupFab.vue'
import OfficialQqGroupModal from './components/OfficialQqGroupModal.vue'
import ProfileIncompleteBanner from './components/ProfileIncompleteBanner.vue'
import PredictSettlementNotifier from './components/PredictSettlementNotifier.vue'
import PredictSettlementReveal from './components/PredictSettlementReveal.vue'
import CollectibleDropHost from './components/collectible/CollectibleDropHost.vue'
import PredictShareSheet from './components/PredictShareSheet.vue'
import ReferralNotifier from './components/ReferralNotifier.vue'
import CollectibleNotifier from './components/CollectibleNotifier.vue'
import InviteShareSheet from './components/InviteShareSheet.vue'
import CollectibleShareSheet from './components/CollectibleShareSheet.vue'
import MobileBottomNav from './components/MobileBottomNav.vue'
import MobileMoreDrawer from './components/MobileMoreDrawer.vue'
import RateLimitBanner from './components/RateLimitBanner.vue'
import LeaderboardRewardDialog from './components/LeaderboardRewardDialog.vue'
import LegendsPageBackdrop from './components/LegendsPageBackdrop.vue'
import { useBreakpoint } from './composables/useBreakpoint'
import { useLeaderboardRewardPrompt } from './composables/useLeaderboardRewardPrompt'
import { authState, isLoggedIn, initAuth, fetchMe } from './stores/authStore'
import { fetchPaidPendingOrder } from './api/commerce'
import { clearPendingOrder, PENDING_ORDER_KEY } from './utils/payEnv'
import { avatarFrameClass as frameClassUtil, hasActiveSeasonPass } from './utils/entitlements'
import { fetchProfileStatus, fetchRecommendations, profileState } from './stores/profileStore'
import { useGuideVisibility } from './composables/useGuideVisibility'
import { useStadiumStore } from './stores/stadiumStore'
import { subscribeLiveMatches } from './stores/liveMatchesStore'
import { startHeaderNotificationPoll } from './stores/headerNotificationsStore'
import { ensurePredictRevealConfig } from './stores/predictRevealConfigStore'
import { tryAutoOpenGuide } from './composables/useGuideModal'
import { useBrowserNotify } from './composables/useBrowserNotify'
import {
  ensureOfficialQqGroupConfig,
  openOfficialQqGroupModal,
  syncQqGroupClaimed,
} from './composables/useOfficialQqGroup'
import { fetchDailyStatus, clearDailyStatus, needsFirstPredict, useDailyStatusRef } from './stores/dailyStatusStore'
import SecondPredictCoach from './components/SecondPredictCoach.vue'
import { syncMatchKickoffReminders } from './composables/useMatchKickoffReminders'
import { useUserPredictWs } from './composables/useUserPredictWs'
import { warmLegendBackdropImages } from './utils/legendsImageCache'

const router = useRouter()
const route = useRoute()
const { isMobile } = useBreakpoint()
const moreOpen = ref(false)
const profileBannerHidden = ref(false)
const { setUiOverlay } = useStadiumStore()
const { isAuthFlow, showProfileBanner, showProfileHeaderChip, showFeatureTour } = useGuideVisibility()
const { showRewardDialog } = useLeaderboardRewardPrompt({ blocked: showFeatureTour })
const { maybePromptForNotify, showNotification } = useBrowserNotify()
const lastDailyStatus = useDailyStatusRef()

const showProfileBannerVisible = computed(
  () => showProfileBanner.value && !profileBannerHidden.value,
)

const mainTeamName = computed(
  () =>
    profileState.recommendations?.fan_identity?.main_team?.name ??
    profileState.status?.main_team?.name ??
    null
)

const themeClass = computed(() => {
  const key = authState.user?.theme_key
  return key ? `theme-${key}` : ''
})

const avatarFrameClass = computed(() => frameClassUtil(authState.user?.avatar_frame))

const mobileAvatarInitial = computed(() => (authState.user?.nickname || '球').slice(0, 1))

const mobileDisplayNick = computed(() => {
  const n = authState.user?.nickname || '球迷'
  return n.length > 4 ? `${n.slice(0, 4)}…` : n
})

const passActive = computed(() => hasActiveSeasonPass(authState.user))

const aiNeedsPredictFirst = needsFirstPredict

useUserPredictWs()

let unsubscribeLive: (() => void) | null = null

onMounted(async () => {
  void warmLegendBackdropImages()
  unsubscribeLive = subscribeLiveMatches()
  await ensurePredictRevealConfig()
  await ensureOfficialQqGroupConfig()
  startHeaderNotificationPoll()
  window.addEventListener('daily-status-refresh', onDailyStatusRefresh)
  await initAuth()
  if (authState.accessToken) {
    const pendingNo =
      typeof sessionStorage !== 'undefined'
        ? sessionStorage.getItem(PENDING_ORDER_KEY)
        : null
    if (pendingNo && route.path !== '/shop/result') {
      const paid = await fetchPaidPendingOrder()
      if (paid) {
        clearPendingOrder()
        await fetchMe()
      }
      await router.replace({ path: '/shop/result', query: { out_trade_no: pendingNo } })
      return
    }
    try {
      await Promise.all([fetchProfileStatus(), fetchRecommendations()])
    } catch {
      /* ignore */
    }
  }
})

onUnmounted(() => {
  unsubscribeLive?.()
  window.removeEventListener('daily-status-refresh', onDailyStatusRefresh)
})

watch(moreOpen, (open) => setUiOverlay('more-drawer', open))
watch(showFeatureTour, (open) => setUiOverlay('onboarding-tour', open))

watch(
  () => [route.path, route.query.guide, isLoggedIn.value, authState.user?.profile_completed] as const,
  () => {
    if (isAuthFlow.value) return
    void tryAutoOpenGuide('site_intro', route.path, route.query as Record<string, unknown>)
  },
)

watch(
  () => route.query.qq,
  (v) => {
    if (v === '1' || v === 'true') openOfficialQqGroupModal()
  },
  { immediate: true },
)

async function refreshQqGroupClaimState() {
  if (!isLoggedIn.value) {
    syncQqGroupClaimed(false)
    clearDailyStatus()
    return
  }
  const daily = await fetchDailyStatus(true).catch(() => null)
  syncQqGroupClaimed(daily?.qq_group_claimed)
  if (daily) {
    const prevPending = lastDailyStatus.value?.pending_predictions ?? 0
    if ((daily.pending_predictions ?? 0) > prevPending && document.hidden) {
      showNotification('你有新的待开奖', '提交成功，赛后会自动通知结果', '/me?focus=predictions')
    }
    if (daily.streak_risk?.message && !lastDailyStatus.value?.streak_risk) {
      void maybePromptForNotify('开启后可收到待开奖与连胜提醒')
    }
  }
}

watch(isLoggedIn, () => {
  void refreshQqGroupClaimState()
  if (isLoggedIn.value) void syncMatchKickoffReminders()
}, { immediate: true })

function onDailyStatusRefresh() {
  void refreshQqGroupClaimState()
}

function onNav(path: string) {
  router.push(path)
}
</script>

<style>
.app-wrapper {
  width: 100vw;
  height: var(--app-height, 100vh);
  height: var(--app-height, 100dvh);
  overflow: hidden;
  background:
    radial-gradient(ellipse at 50% 0%, var(--wc-glow-rose) 0%, transparent 50%),
    radial-gradient(ellipse at 50% 30%, var(--wc-bg-mid) 0%, var(--wc-bg-deep) 100%);
}

.layout-container {
  height: var(--app-height, 100vh);
  height: var(--app-height, 100dvh);
  width: 100vw;
  background: transparent;
  color: var(--wc-text-primary);
  display: flex;
  flex-direction: column;
  position: relative;
  z-index: 10;
  pointer-events: none;
}

.app-header {
  pointer-events: auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-shrink: 0;
  min-height: var(--wc-header-height);
  background: rgba(10, 12, 24, 0.92);
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
  border-bottom: 1px solid transparent;
  border-image: linear-gradient(
    90deg,
    rgba(139, 41, 66, 0.2) 0%,
    rgba(212, 165, 116, 0.35) 30%,
    rgba(201, 120, 138, 0.25) 70%,
    rgba(139, 41, 66, 0.2) 100%
  ) 1;
  padding: 0 40px;
  height: var(--wc-header-height);
  position: sticky;
  top: 0;
  z-index: 400;
  overflow: visible;
}

.el-main {
  padding: 0 !important;
  flex: 1;
  min-height: 0;
}

/* 竞猜/收藏等长页：单页滚动，避免 flex 子项被压成「小窗滚动」 */
.el-main.main-content:not(.is-dashboard) {
  display: block;
  overflow-y: auto;
  overflow-x: hidden;
  overscroll-behavior-y: contain;
  touch-action: pan-y;
  -webkit-overflow-scrolling: touch;
}

.el-main.main-content.is-dashboard {
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  overflow-x: hidden;
  overscroll-behavior-y: contain;
  touch-action: pan-y;
  position: relative;
  -webkit-overflow-scrolling: touch;
}

.logo {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
  text-decoration: none;
  color: inherit;
  transition: opacity 0.2s;
}

.logo:hover {
  opacity: 0.92;
}

.logo-img {
  flex-shrink: 0;
}

.brand-text {
  display: flex;
  flex-direction: column;
  line-height: 1.15;
  gap: 1px;
}

.title-main {
  font-family: var(--wc-font-serif);
  font-size: 20px;
  font-weight: 900;
  letter-spacing: 3px;
  background: linear-gradient(135deg, #e8c88a 0%, var(--wc-accent-gold) 50%, var(--wc-accent-rose) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.title-sub {
  font-family: var(--wc-font-sans);
  font-size: 11px;
  font-weight: 500;
  letter-spacing: 2px;
  color: var(--wc-text-muted);
  -webkit-text-fill-color: var(--wc-text-muted);
}

.nav-menu {
  border-bottom: none !important;
  font-size: 15px;
  flex: 1;
}

.nav-hint-badge {
  display: inline-block;
  margin-left: 4px;
  padding: 0 5px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 600;
  line-height: 1.4;
  background: rgba(230, 162, 60, 0.25);
  color: #e6a23c;
  vertical-align: middle;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  justify-content: flex-end;
  min-width: 0;
  overflow: hidden;
}

.logo--mobile {
  gap: 6px;
  flex-shrink: 0;
}

.logo--mobile .title-main {
  font-size: 16px;
  letter-spacing: 2px;
  white-space: nowrap;
}

.mobile-header-actions {
  align-items: center;
  gap: 8px;
  margin-left: auto;
  flex: 1;
  min-width: 0;
  max-width: 100%;
  justify-content: flex-end;
}

.mobile-header-scroll {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  flex: 1;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: none;
  padding-right: 2px;
}

.mobile-header-scroll::-webkit-scrollbar {
  display: none;
}

.mobile-header-scroll .ref-badge {
  flex-shrink: 0;
}

.mobile-header-scroll .ref-badge .el-button {
  width: 36px;
  height: 36px;
  padding: 0;
}

.mobile-login-btn {
  flex-shrink: 0;
}

.mobile-balance-chip {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 2px;
  padding: 6px 10px;
  border-radius: 12px;
  border: 1px solid rgba(212, 165, 116, 0.4);
  background: rgba(14, 16, 32, 0.92);
  box-shadow: 0 0 12px rgba(212, 165, 116, 0.12);
  cursor: pointer;
  font-size: 12px;
  line-height: 1.2;
  flex-shrink: 0;
  white-space: nowrap;
}

.balance-row {
  display: flex;
  align-items: center;
  gap: 4px;
}

.balance-row.sub {
  display: none;
}

.balance-divider {
  color: rgba(212, 165, 116, 0.45);
  margin: 0 2px;
}

.pts-inline {
  color: #f0a0b0;
  font-weight: 700;
  font-size: 11px;
}

.coin-icon {
  font-size: 11px;
  line-height: 1;
}

.mobile-balance-chip .coins {
  color: var(--wc-accent-gold-light);
  font-weight: 800;
  font-size: 13px;
}

.pts-label {
  font-size: 10px;
  color: var(--wc-text-muted);
}

.mobile-balance-chip .redeem-pts {
  color: #f0a0b0;
  font-weight: 700;
  font-size: 12px;
}

.mobile-me-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
  padding: 4px 10px 4px 4px;
  border-radius: 24px;
  border: 1px solid rgba(212, 165, 116, 0.35);
  background: rgba(212, 165, 116, 0.1);
  cursor: pointer;
  max-width: 130px;
}

.mobile-me-chip.frame-gold_wc {
  border-color: #e8c88a;
  box-shadow: 0 0 0 1px rgba(232, 200, 138, 0.35);
}

.mobile-me-chip.frame-silver_wc {
  border-color: #c0c0c0;
}

.mobile-me-avatar {
  position: relative;
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: rgba(212, 165, 116, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
}

.mobile-me-text {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  min-width: 0;
  line-height: 1.15;
}

.mobile-me-nick {
  font-size: 0.72rem;
  font-weight: 700;
  color: #f5f0e8;
  max-width: 72px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.mobile-me-label {
  font-size: 0.65rem;
  color: var(--wc-accent-gold);
  font-weight: 600;
}

.mobile-avatar-chip {
  position: relative;
  flex-shrink: 0;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: 2px solid rgba(212, 165, 116, 0.35);
  background: rgba(212, 165, 116, 0.15);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  padding: 0;
}

.mobile-avatar-chip.frame-gold_wc {
  border: 2px solid #e8c88a;
  box-shadow: 0 0 0 1px rgba(232, 200, 138, 0.35), 0 0 10px rgba(212, 165, 116, 0.4);
}

.mobile-avatar-chip.frame-silver_wc {
  border: 2px solid #c0c0c0;
  box-shadow: 0 0 0 1px rgba(192, 192, 192, 0.3), 0 0 8px rgba(200, 200, 200, 0.25);
}

.mobile-avatar-letter {
  font-size: 0.95rem;
  font-weight: 800;
  color: #f5f0e8;
}

.pass-badge {
  position: absolute;
  right: -4px;
  bottom: -2px;
  font-size: 0.55rem;
  font-weight: 800;
  line-height: 1;
  padding: 2px 4px;
  border-radius: 6px;
  background: rgba(103, 194, 58, 0.9);
  color: #fff;
}

.mobile-more-btn {
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  width: 48px;
  min-width: 48px;
  height: 48px;
  min-height: 48px;
  padding: 4px 6px;
  border-radius: 14px;
  border: 2px solid rgba(232, 200, 138, 0.75);
  background: linear-gradient(165deg, rgba(212, 165, 116, 0.42), rgba(139, 41, 66, 0.28));
  color: #fff8ee;
  cursor: pointer;
  flex-shrink: 0;
  box-shadow:
    0 2px 14px rgba(212, 165, 116, 0.35),
    inset 0 1px 0 rgba(255, 255, 255, 0.14);
  position: relative;
  z-index: 2;
}

.more-icon-bars {
  display: flex;
  flex-direction: column;
  gap: 4px;
  width: 18px;
}

.more-icon-bars span {
  display: block;
  height: 2px;
  border-radius: 2px;
  background: linear-gradient(90deg, #f5e6c8, var(--wc-accent-gold));
}

.mobile-more-btn .more-label {
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.5px;
  color: #f5e6c8;
}

.mobile-more-btn.has-alert::after {
  content: '';
  position: absolute;
  top: 4px;
  right: 4px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #f56c6c;
  border: 1.5px solid rgba(10, 12, 24, 0.9);
  box-shadow: 0 0 6px rgba(245, 108, 108, 0.65);
}

.mobile-more-btn:active {
  transform: scale(0.96);
}

.mobile-profile-chip {
  padding: 4px 10px;
  border-radius: 12px;
  border: 1px solid rgba(212, 165, 116, 0.35);
  background: rgba(212, 165, 116, 0.12);
  color: var(--wc-accent-gold);
  font-size: 11px;
  font-weight: 600;
  white-space: nowrap;
}

.user-chip {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 12px;
  border-radius: 20px;
  background: rgba(212, 165, 116, 0.12);
  cursor: pointer;
  font-size: 13px;
  flex-shrink: 0;
}
.user-chip .coins {
  color: var(--wc-accent-gold);
  font-weight: 700;
}
.user-chip .redeem-pts {
  color: var(--wc-accent-rose);
  font-size: 12px;
}
.user-chip .nick {
  color: var(--wc-text-muted);
  max-width: 80px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.user-chip .me-label {
  color: var(--wc-accent-gold);
  font-size: 12px;
  font-weight: 600;
  padding-left: 4px;
  border-left: 1px solid rgba(212, 165, 116, 0.35);
  margin-left: 2px;
}

.team-chip {
  padding: 4px 12px;
  border-radius: 16px;
  background: rgba(139, 41, 66, 0.25);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  flex-shrink: 0;
  color: var(--wc-accent-gold);
}
.team-chip.incomplete {
  background: rgba(212, 165, 116, 0.15);
  color: var(--wc-text-muted);
}

.mobile-nav,
.tablet-nav {
  display: none;
}

.el-menu-item {
  font-size: 15px !important;
  font-weight: 500;
  position: relative;
  border-bottom: none !important;
}

.el-menu-item:hover {
  background-color: rgba(201, 120, 138, 0.08) !important;
}

.el-menu--horizontal > .el-menu-item.is-active {
  border-bottom: 2px solid var(--wc-accent-rose) !important;
  background: rgba(212, 165, 116, 0.06) !important;
}

.main-content {
  padding: 30px;
  flex: 1;
  min-height: 0;
  pointer-events: auto;
}

.main-content:not(.is-dashboard):not(.is-auth-flow) {
  padding: 30px;
}

.page-shell,
.main-content > * {
  pointer-events: auto;
}

@media (max-width: 960px) {
  .app-header {
    padding: 0 12px;
    height: var(--wc-mobile-header-height);
  }

  .title-main {
    font-size: 17px;
    letter-spacing: 2px;
  }

  .title-sub {
    display: none;
  }

  .logo-img .app-logo {
    width: 34px;
    height: 34px;
  }

  .desktop-nav {
    display: none !important;
  }

  .tablet-nav {
    display: inline-flex;
  }

  .main-content:not(.is-dashboard) {
    padding: 16px;
  }
}

@media (max-width: 768px) {
  .app-header {
    height: var(--wc-mobile-header-height);
    min-height: var(--wc-mobile-header-height);
    padding: 0 8px 0 10px;
    gap: 8px;
    position: sticky;
    top: 0;
    z-index: 500;
  }

  .layout-container {
    /* 防止 flex 子项把顶栏挤没 */
    min-height: 0;
  }

  .layout-container > .el-header {
    flex: 0 0 auto !important;
    height: auto !important;
  }

  .tablet-nav {
    display: none !important;
  }

  .main-content.is-dashboard {
    overflow-y: auto;
    overflow-x: hidden;
  }

  .main-content:not(.is-dashboard):not(.is-auth-flow) {
    padding: 0;
  }
}

.app-footer {
  pointer-events: auto;
  height: auto !important;
  padding: 10px 24px 14px;
  text-align: center;
  font-size: 12px;
  color: var(--wc-text-muted);
  background: rgba(10, 12, 24, 0.75);
  border-top: 1px solid rgba(212, 165, 116, 0.12);
}
.app-footer a {
  color: var(--wc-accent-gold);
  text-decoration: none;
}
.app-footer a:hover {
  text-decoration: underline;
}
.app-footer .sep {
  margin: 0 8px;
  opacity: 0.5;
}
.app-footer .muted {
  opacity: 0.7;
}

.app-wrapper.theme-team_spirit {
  --wc-accent-gold: #e8b84a;
  --wc-glow-gold: rgba(232, 184, 74, 0.35);
}
.app-wrapper.theme-team_spirit .user-chip {
  background: rgba(232, 184, 74, 0.18);
}
.app-wrapper.theme-gold_wc {
  --wc-accent-gold: #f0c040;
  --wc-glow-gold: rgba(240, 192, 64, 0.4);
}
.user-chip.frame-gold_wc {
  box-shadow: 0 0 0 2px rgba(240, 192, 64, 0.55), 0 0 12px rgba(240, 192, 64, 0.25);
}
.user-chip.frame-silver_wc {
  box-shadow: 0 0 0 2px rgba(192, 192, 192, 0.6), 0 0 10px rgba(200, 200, 200, 0.2);
}
</style>
