import { createRouter, createWebHistory } from 'vue-router'
import { authState } from '../stores/authStore'
import { fetchDailyStatus } from '../stores/dailyStatusStore'

const HOME_PREDICT_REDIRECT_KEY = 'wc_home_predict_redirect_done'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'Dashboard',
      component: () => import('../views/Dashboard.vue'),
    },
    {
      path: '/live/match/:id',
      name: 'MatchDetail',
      component: () => import('../views/MatchDetail.vue'),
    },
    {
      path: '/live',
      name: 'LiveCenter',
      component: () => import('../views/LiveCenter.vue'),
    },
    {
      path: '/teams',
      name: 'Teams',
      component: () => import('../views/Teams.vue'),
    },
    {
      path: '/teams/:name',
      name: 'TeamDetail',
      component: () => import('../views/TeamDetail.vue'),
    },
    {
      path: '/players/:id',
      name: 'PlayerDetail',
      component: () => import('../views/PlayerDetail.vue'),
    },
    {
      path: '/players',
      name: 'Players',
      component: () => import('../views/Players.vue'),
    },
    {
      path: '/agent',
      name: 'Agent',
      component: () => import('../views/AgentWorkbench.vue'),
    },
    {
      path: '/agent/:team1/:team2',
      name: 'AgentMatch',
      component: () => import('../views/AgentWorkbench.vue'),
    },
    {
      path: '/news',
      name: 'News',
      component: () => import('../views/News.vue'),
    },
    {
      path: '/onboarding',
      name: 'FanOnboarding',
      component: () => import('../views/FanOnboarding.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/cheer/:matchId',
      name: 'CheerWall',
      component: () => import('../views/CheerWall.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/me/card',
      name: 'FanCard',
      component: () => import('../views/FanCard.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/invite',
      name: 'InviteHub',
      component: () => import('../views/InviteHub.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/login',
      name: 'Login',
      component: () => import('../views/Login.vue'),
      meta: { guestOnly: true },
    },
    {
      path: '/me',
      name: 'UserCenter',
      component: () => import('../views/UserCenter.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/predict',
      name: 'PredictHall',
      component: () => import('../views/PredictHall.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/arena',
      name: 'ArenaHub',
      component: () => import('../views/ArenaHub.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/collection',
      name: 'Collection',
      component: () => import('../views/Collection.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/market',
      name: 'Marketplace',
      component: () => import('../views/Marketplace.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/mint',
      name: 'MintEvent',
      component: () => import('../views/MintEvent.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/admin/economy',
      name: 'AdminEconomy',
      component: () => import('../views/AdminEconomy.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/fantasy',
      name: 'Fantasy',
      component: () => import('../views/Fantasy.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/me/assets',
      name: 'MyAssets',
      component: () => import('../views/MyAssets.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/leaderboard',
      name: 'Leaderboard',
      component: () => import('../views/Leaderboard.vue'),
    },
    {
      path: '/shop',
      name: 'Shop',
      component: () => import('../views/Shop.vue'),
    },
    {
      path: '/shop/result',
      name: 'ShopPaymentResult',
      component: () => import('../views/ShopPaymentResult.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/worldcup2026',
      name: 'WorldCup2026Guide',
      component: () => import('../views/WorldCup2026Guide.vue'),
    },
    {
      path: '/legal/terms',
      name: 'LegalTerms',
      component: () => import('../views/LegalTerms.vue'),
    },
    {
      path: '/legal/privacy',
      name: 'LegalPrivacy',
      component: () => import('../views/LegalPrivacy.vue'),
    },
    {
      path: '/legal/ai',
      name: 'LegalAiUsage',
      component: () => import('../views/LegalAiUsage.vue'),
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'NotFound',
      component: () => import('../views/NotFound.vue'),
    },
    {
      path: '/prediction',
      redirect: (to) => ({
        path: '/agent',
        query: { team1: to.query.team1, team2: to.query.team2, auto: '1' },
      }),
    },
  ],
})

router.beforeEach(async (to) => {
  if (to.meta.requiresAuth && !authState.accessToken) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  if (to.meta.guestOnly && authState.accessToken) {
    if (authState.user && !authState.user.profile_completed) {
      return { path: '/onboarding' }
    }
    const redirect = typeof to.query.redirect === 'string' ? to.query.redirect : '/'
    return redirect.startsWith('/login') ? { path: '/' } : redirect
  }
  if (to.name === 'Dashboard' && authState.accessToken) {
    try {
      if (!sessionStorage.getItem(HOME_PREDICT_REDIRECT_KEY)) {
        const daily = await fetchDailyStatus(true)
        if (daily) {
          sessionStorage.setItem(HOME_PREDICT_REDIRECT_KEY, '1')
          if ((daily.predict_count_total ?? 0) === 0) {
            return { path: '/predict', query: to.query }
          }
        }
      }
    } catch {
      /* ignore — stay on dashboard */
    }
  }
  return true
})

export default router
