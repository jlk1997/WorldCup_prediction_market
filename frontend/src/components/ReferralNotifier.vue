<template>
  <el-popover v-if="isLoggedIn && (latest || unread)" placement="bottom" :width="320" trigger="click">
    <template #reference>
      <el-badge :value="unread" :hidden="!unread" class="ref-badge">
        <el-button circle size="small" aria-label="召友奖励">
          <span>🤝</span>
        </el-button>
      </el-badge>
    </template>
    <div v-if="latest" class="ref-pop">
      <strong>{{ latest.title }}</strong>
      <p>{{ latest.body }}</p>
      <el-button type="primary" size="small" @click="goAction">查看详情</el-button>
      <el-button link size="small" @click="markRead">知道了</el-button>
    </div>
    <div v-else class="ref-pop">
      <p>你有 {{ unread }} 条召友奖励通知</p>
      <el-button link size="small" @click="$router.push('/invite')">去召友中心</el-button>
    </div>
  </el-popover>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  getNotifications,
  getUnreadNotificationCount,
  markNotificationsRead,
  type UserNotification,
} from '../api/notifications'
import { isLoggedIn } from '../stores/authStore'
import { useVisibilityPoll } from '../composables/useVisibilityPoll'

const router = useRouter()
const unread = ref(0)
const latest = ref<UserNotification | null>(null)

async function poll() {
  if (!isLoggedIn.value) return
  try {
    unread.value = await getUnreadNotificationCount('referral_reward')
    if (unread.value > 0) {
      const rows = await getNotifications({ unread_only: true, category: 'referral_reward', limit: 1 })
      latest.value = rows[0] ?? null
    } else {
      latest.value = null
    }
  } catch {
    unread.value = 0
  }
}

useVisibilityPoll(poll, 60000)

async function markRead() {
  if (!latest.value) return
  await markNotificationsRead([latest.value.id])
  unread.value = Math.max(0, unread.value - 1)
  latest.value = null
  await poll()
}

function goAction() {
  const action = (latest.value?.payload?.action as string) || '/invite'
  markRead()
  router.push(action)
}
</script>

<style scoped>
.ref-badge {
  margin-right: 4px;
}
.ref-pop p {
  margin: 8px 0 12px;
  font-size: 13px;
  line-height: 1.5;
  color: var(--wc-text-muted, #9a94a8);
}
</style>
