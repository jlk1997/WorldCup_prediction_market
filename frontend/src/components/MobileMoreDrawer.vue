<template>

  <el-drawer

    v-model="visible"

    direction="rtl"

    size="78%"

    :with-header="false"

    class="mobile-more-drawer"

  >

    <div class="drawer-inner">

      <div class="drawer-head">

        <h2>更多</h2>

        <el-button circle text @click="visible = false" aria-label="关闭">

          <el-icon><Close /></el-icon>

        </el-button>

      </div>



      <button v-if="showProfileChip" type="button" class="drawer-profile-chip" @click="nav('/onboarding')">

        完善球迷档案 →

      </button>



      <div v-if="isLoggedIn && mainTeamName" class="drawer-team" @click="nav('/me')">

        ⚽ {{ mainTeamName }}

      </div>



      <div class="drawer-section">

        <span class="section-label">3D 球场画质</span>

        <StadiumModeSelector class="drawer-mode" />

      </div>



      <nav class="drawer-nav">

        <button v-for="item in navItems" :key="item.path" type="button" class="drawer-link" @click="nav(item.path)">

          {{ item.label }}

        </button>

      </nav>



      <div class="drawer-legal">

        <router-link to="/legal/terms" @click="visible = false">用户协议</router-link>

        <router-link to="/legal/privacy" @click="visible = false">隐私政策</router-link>

        <router-link to="/legal/ai" @click="visible = false">AI 使用说明</router-link>

        <span class="muted">虚拟道具不可提现</span>

      </div>



      <div class="drawer-foot">

        <el-button v-if="isLoggedIn" type="danger" plain class="mobile-full-btn" @click="logout">退出登录</el-button>

        <el-button v-else type="primary" class="mobile-full-btn" @click="nav('/login')">登录 / 注册</el-button>

      </div>

    </div>

  </el-drawer>

</template>



<script setup lang="ts">

import { computed } from 'vue'

import { useRouter } from 'vue-router'

import { Close } from '@element-plus/icons-vue'

import StadiumModeSelector from './StadiumModeSelector.vue'

import { isLoggedIn, logout as doLogout } from '../stores/authStore'

import { needsFirstPredict } from '../stores/dailyStatusStore'

import { profileState } from '../stores/profileStore'



defineProps<{ showProfileChip?: boolean }>()



const visible = defineModel<boolean>({ default: false })



const router = useRouter()



const mainTeamName = computed(

  () =>

    profileState.recommendations?.fan_identity?.main_team?.name ??

    profileState.status?.main_team?.name ??

    null,

)



const navItems = computed(() => {

  const items = [

    { path: '/agent', label: needsFirstPredict.value ? 'AI 工作台 · 先猜' : 'AI 工作台' },

    { path: '/leaderboard', label: '排行榜' },

    { path: '/news', label: '资讯' },

    { path: '/teams', label: '球队库' },

    { path: '/shop', label: '商城' },

  ]

  if (isLoggedIn.value) {

    items.push({ path: '/invite', label: '召友中心' })

  }

  return items

})



function nav(path: string) {

  visible.value = false

  router.push(path)

}



function logout() {

  visible.value = false

  doLogout()

  router.push('/login')

}

</script>



<style scoped>

.drawer-inner {

  display: flex;

  flex-direction: column;

  height: 100%;

  padding: 16px;

  color: var(--wc-text-primary);

}



.drawer-head {

  display: flex;

  align-items: center;

  justify-content: space-between;

  margin-bottom: 16px;

}



.drawer-head h2 {

  margin: 0;

  font-size: 1.1rem;

  color: var(--wc-accent-gold);

}



.drawer-profile-chip {

  width: 100%;

  min-height: 44px;

  margin-bottom: 10px;

  padding: 10px 14px;

  border-radius: 10px;

  border: 1px solid rgba(212, 165, 116, 0.4);

  background: rgba(212, 165, 116, 0.14);

  color: var(--wc-accent-gold);

  font-weight: 600;

  cursor: pointer;

  text-align: left;

}



.drawer-team {

  padding: 10px 14px;

  border-radius: 10px;

  background: rgba(139, 41, 66, 0.25);

  color: var(--wc-accent-gold);

  font-weight: 600;

  margin-bottom: 12px;

  cursor: pointer;

  border: none;

  width: 100%;

  text-align: left;

  min-height: 44px;

}



.drawer-section {

  display: flex;

  align-items: center;

  justify-content: space-between;

  gap: 10px;

  padding: 10px 12px;

  margin-bottom: 12px;

  border-radius: 10px;

  background: rgba(255, 255, 255, 0.04);

}



.section-label {

  font-size: 0.82rem;

  color: var(--wc-text-muted);

  flex-shrink: 0;

}



.drawer-mode :deep(.mode-trigger) {

  margin-right: 0;

}



.drawer-nav {

  display: flex;

  flex-direction: column;

  gap: 4px;

  flex: 1;

  overflow-y: auto;

  min-height: 0;

}



.drawer-link {

  text-align: left;

  padding: 12px 14px;

  border: none;

  border-radius: 8px;

  background: rgba(255, 255, 255, 0.04);

  color: var(--wc-text-secondary);

  font-size: 0.95rem;

  cursor: pointer;

  min-height: 44px;

}



.drawer-link:active {

  background: rgba(212, 165, 116, 0.12);

}



.drawer-legal {

  display: flex;

  flex-direction: column;

  gap: 8px;

  margin: 16px 0;

  font-size: 0.8rem;

}



.drawer-legal a {

  color: var(--wc-accent-gold);

  text-decoration: none;

}



.drawer-legal .muted {

  color: var(--wc-text-muted);

  margin-top: 4px;

}



.drawer-foot {

  padding-top: 8px;

  padding-bottom: env(safe-area-inset-bottom, 0px);

}

</style>



<style>

.mobile-more-drawer .el-drawer__body {

  padding: 0;

  background: var(--wc-bg-mid);

}

</style>

