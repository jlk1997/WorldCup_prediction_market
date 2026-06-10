<template>
  <div class="app-wrapper" :class="[themeClass, { 'is-mobile': isMobile }]">
    <StadiumBackground v-if="showStadiumBg" />

    <el-container class="layout-container">
      <el-header class="app-header safe-area-top">
        <router-link to="/" class="logo" aria-label="最后一舞 世界杯2026 首页">
          <AppLogo class="logo-img" />
          <div class="brand-text">
            <span class="title-main">最后一舞</span>
            <span class="title-sub">世界杯2026</span>
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
          </div>
          <el-button v-else type="primary" plain size="small" class="hide-mobile" @click="router.push('/login')">登录</el-button>

          <!-- 移动端精简顶栏 -->
          <div v-if="isMobile" class="mobile-header-actions hide-desktop-flex">
            <button
              v-if="isLoggedIn"
              type="button"
              class="mobile-avatar-chip touch-target"
              :class="avatarFrameClass"
              aria-label="进入球迷中心"
              @click="router.push('/me')"
            >
              <span class="mobile-avatar-letter">{{ mobileAvatarInitial }}</span>
              <span v-if="passActive" class="pass-badge">通</span>
            </button>
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
              </span>
              <span class="balance-row sub">
                <span class="pts-label">可用分</span>
                <span class="redeem-pts">{{ authState.user?.redeem_points ?? 0 }}</span>
              </span>
            </button>
            <el-button v-else type="primary" plain size="small" @click="router.push('/login')">登录</el-button>
            <button
              v-if="showProfileHeaderChip"
              type="button"
              class="mobile-profile-chip touch-target"
              @click="router.push('/onboarding')"
            >
              完善档案
            </button>
            <button
              type="button"
              class="mobile-more-btn touch-target"
              aria-label="更多菜单"
              @click="moreOpen = true"
            >
              <el-icon :size="20"><Menu /></el-icon>
              <span class="more-label">更多</span>
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
            <el-menu-item index="/agent">AI 工作台</el-menu-item>
            <el-menu-item index="/news">资讯</el-menu-item>
            <el-menu-item index="/teams">球队库</el-menu-item>
            <el-menu-item v-if="isLoggedIn" index="/invite">召友</el-menu-item>
            <el-menu-item index="/shop">商城</el-menu-item>
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
                <el-dropdown-item command="/agent">AI 工作台</el-dropdown-item>
                <el-dropdown-item command="/news">资讯</el-dropdown-item>
                <el-dropdown-item command="/teams">球队库</el-dropdown-item>
                <el-dropdown-item command="/shop">商城</el-dropdown-item>
                <el-dropdown-item v-if="isLoggedIn" command="/invite">召友中心</el-dropdown-item>
                <el-dropdown-item v-if="isLoggedIn" command="/me">球迷中心</el-dropdown-item>
                <el-dropdown-item v-else command="/login">登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <el-main
        class="main-content safe-area-bottom"
        :class="{
          'is-dashboard': $route.path === '/',
          'is-auth-flow': isAuthFlow,
          'has-bottom-nav': isMobile && !isAuthFlow,
        }"
      >
        <ProfileIncompleteBanner v-if="showProfileBannerVisible" @dismiss="profileBannerHidden = true" />
        <OnboardingTour v-if="showFeatureTour" />
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
  </div>
</template>

<script setup lang="ts">
import { defineAsyncComponent, computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Menu } from '@element-plus/icons-vue'
import StadiumModeSelector from './components/StadiumModeSelector.vue'
import AppLogo from './components/AppLogo.vue'
import OnboardingTour from './components/OnboardingTour.vue'
import ProfileIncompleteBanner from './components/ProfileIncompleteBanner.vue'
import PredictSettlementNotifier from './components/PredictSettlementNotifier.vue'
import ReferralNotifier from './components/ReferralNotifier.vue'
import MobileBottomNav from './components/MobileBottomNav.vue'
import MobileMoreDrawer from './components/MobileMoreDrawer.vue'
import { useBreakpoint } from './composables/useBreakpoint'
import { authState, isLoggedIn, initAuth } from './stores/authStore'
import { avatarFrameClass as frameClassUtil, hasActiveSeasonPass } from './utils/entitlements'
import { fetchProfileStatus, fetchRecommendations, profileState } from './stores/profileStore'
import { useGuideVisibility } from './composables/useGuideVisibility'
import { useStadiumStore } from './stores/stadiumStore'

const StadiumBackground = defineAsyncComponent(() => import('./components/StadiumBackground.vue'))

const router = useRouter()
const route = useRoute()
const { isMobile } = useBreakpoint()
const moreOpen = ref(false)
const profileBannerHidden = ref(false)
const { setUiOverlay } = useStadiumStore()
const { isAuthFlow, showProfileBanner, showProfileHeaderChip, showFeatureTour } = useGuideVisibility()

const showProfileBannerVisible = computed(
  () => showProfileBanner.value && !profileBannerHidden.value,
)

const STADIUM_ROUTES = ['/', '/agent', '/live', '/login', '/onboarding', '/me', '/arena', '/cheer', '/predict', '/news', '/teams', '/invite', '/shop', '/leaderboard']
const showStadiumBg = computed(
  () =>
    route.path !== '/' &&
    STADIUM_ROUTES.some((p) => (p === '/' ? route.path === '/' : route.path.startsWith(p))),
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

const passActive = computed(() => hasActiveSeasonPass(authState.user))

onMounted(async () => {
  await initAuth()
  if (authState.accessToken) {
    try {
      await Promise.all([fetchProfileStatus(), fetchRecommendations()])
    } catch {
      /* ignore */
    }
  }
})

watch(moreOpen, (open) => setUiOverlay('more-drawer', open))
watch(showFeatureTour, (open) => setUiOverlay('onboarding-tour', open))

function onNav(path: string) {
  router.push(path)
}
</script>

<style>
.app-wrapper {
  width: 100vw;
  height: 100vh;
  height: 100dvh;
  overflow: hidden;
  background:
    radial-gradient(ellipse at 50% 0%, var(--wc-glow-rose) 0%, transparent 50%),
    radial-gradient(ellipse at 50% 30%, var(--wc-bg-mid) 0%, var(--wc-bg-deep) 100%);
}

.layout-container {
  height: 100vh;
  height: 100dvh;
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
  background: rgba(10, 12, 24, 0.88);
  backdrop-filter: blur(18px);
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
  position: relative;
  z-index: 100;
}

.el-main {
  padding: 0 !important;
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
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

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  justify-content: flex-end;
  min-width: 0;
}

.mobile-header-actions {
  align-items: center;
  gap: 6px;
  margin-left: auto;
}

.mobile-balance-chip {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  padding: 5px 10px;
  border-radius: 12px;
  border: 1px solid rgba(212, 165, 116, 0.4);
  background: rgba(14, 16, 32, 0.92);
  box-shadow: 0 0 12px rgba(212, 165, 116, 0.12);
  cursor: pointer;
  font-size: 12px;
  line-height: 1.2;
  flex-shrink: 1;
  min-width: 0;
}

.balance-row {
  display: flex;
  align-items: center;
  gap: 4px;
}

.balance-row.sub {
  opacity: 0.95;
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
  gap: 1px;
  min-width: 44px;
  min-height: 44px;
  padding: 4px 8px;
  border-radius: 12px;
  border: 1.5px solid rgba(212, 165, 116, 0.55);
  background: linear-gradient(180deg, rgba(212, 165, 116, 0.22), rgba(212, 165, 116, 0.08));
  color: var(--wc-accent-gold-light);
  cursor: pointer;
  flex-shrink: 0;
  box-shadow: 0 0 14px rgba(212, 165, 116, 0.2);
}

.mobile-more-btn .more-label {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.5px;
}

.mobile-more-btn:active {
  transform: scale(0.97);
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
  overflow-y: auto;
  overflow-x: hidden;
  overscroll-behavior: contain;
  -webkit-overflow-scrolling: touch;
  pointer-events: none;
}

.page-shell,
.main-content > * {
  pointer-events: auto;
}

.main-content.is-dashboard {
  padding: 0 !important;
  overflow-y: auto;
  overflow-x: hidden;
  position: relative;
  -webkit-overflow-scrolling: touch;
}

.main-content.is-auth-flow {
  padding: 0 !important;
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
    padding: 0 10px;
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
