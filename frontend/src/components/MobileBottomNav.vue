<template>
  <nav class="mobile-bottom-nav safe-area-bottom" aria-label="主导航">
    <button
      v-for="item in tabs"
      :key="item.path"
      type="button"
      class="nav-item touch-target"
      :class="{ active: isActive(item.path) }"
      @click="go(item)"
    >
      <el-icon :size="20"><component :is="item.icon" /></el-icon>
      <span class="nav-label">{{ item.label }}</span>
    </button>
  </nav>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { HomeFilled, Trophy, Coin, Flag, User } from '@element-plus/icons-vue'
import { isLoggedIn } from '../stores/authStore'

const router = useRouter()
const route = useRoute()

const tabs = computed(() => [
  { path: '/', label: '首页', icon: HomeFilled, auth: false },
  { path: '/live', label: '赛事', icon: Trophy, auth: false },
  { path: '/predict', label: '竞猜', icon: Coin, auth: true },
  { path: '/arena', label: '擂台', icon: Flag, auth: true },
  { path: '/me', label: '我的', icon: User, auth: true },
])

function isActive(path: string) {
  if (path === '/') return route.path === '/'
  return route.path === path || route.path.startsWith(`${path}/`)
}

function go(item: { path: string; auth: boolean }) {
  if (item.auth && !isLoggedIn.value) {
    router.push({ path: '/login', query: { redirect: item.path } })
    return
  }
  router.push(item.path)
}
</script>

<style scoped>
.mobile-bottom-nav {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 200;
  display: flex;
  align-items: stretch;
  justify-content: space-around;
  height: calc(var(--wc-bottom-nav-height) + env(safe-area-inset-bottom, 0px));
  padding-bottom: env(safe-area-inset-bottom, 0px);
  background: rgba(10, 12, 24, 0.94);
  backdrop-filter: blur(16px);
  border-top: 1px solid rgba(212, 165, 116, 0.2);
  pointer-events: auto;
}

.nav-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  border: none;
  background: transparent;
  color: var(--wc-text-muted);
  font-size: 0.65rem;
  cursor: pointer;
  padding: 4px 0;
  transition: color 0.15s;
}

.nav-item.active {
  color: var(--wc-accent-gold);
  background: rgba(212, 165, 116, 0.08);
  border-radius: 10px 10px 0 0;
}

.nav-item:active {
  opacity: 0.75;
}

.nav-label {
  line-height: 1.1;
}
</style>
