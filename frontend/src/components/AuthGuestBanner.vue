<template>
  <el-alert
    v-if="show"
    :type="type"
    :closable="closable"
    show-icon
    class="auth-guest-banner"
    :title="title"
  >
    <slot>{{ body }}</slot>
    <template v-if="!$slots.default && showLoginLink">
      请先
      <router-link :to="loginTo">登录</router-link>
      {{ loginSuffix }}
    </template>
  </el-alert>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { isAuthBootstrapping, isLoggedIn } from '@/stores/authStore'

const props = withDefaults(
  defineProps<{
    /** 为 true 时仅在未登录展示；已登录不显示 */
    guestOnly?: boolean
    title?: string
    body?: string
    type?: 'warning' | 'info'
    closable?: boolean
    showLoginLink?: boolean
    loginSuffix?: string
  }>(),
  {
    guestOnly: true,
    title: '登录后可使用完整功能',
    body: '',
    type: 'warning',
    closable: false,
    showLoginLink: true,
    loginSuffix: '后继续使用',
  },
)

const route = useRoute()

const loginTo = computed(() => ({
  path: '/login',
  query: { redirect: route.fullPath },
}))

const show = computed(() => {
  if (isAuthBootstrapping.value) return false
  if (!props.guestOnly) return true
  return !isLoggedIn.value
})
</script>

<style scoped>
.auth-guest-banner {
  margin-bottom: 12px;
}
.auth-guest-banner a {
  color: var(--wc-accent-gold);
  font-weight: 600;
}
</style>
