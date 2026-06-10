<template>
  <el-popover v-if="isLoggedIn && (latest || unread)" placement="bottom" :width="320" trigger="click">
    <template #reference>
      <el-badge :value="unread" :hidden="!unread" class="settle-badge">
        <el-button circle size="small" aria-label="竞猜结算通知">
          <span>🎯</span>
        </el-button>
      </el-badge>
    </template>
    <div v-if="latest" class="settle-pop">
      <strong>{{ latest.title }}</strong>
      <p>{{ latest.body }}</p>
      <el-button
        v-if="latest.payload?.next_match_id"
        type="primary"
        size="small"
        @click="goNext(latest.payload.next_match_id as number)"
      >
        去猜下一场
      </el-button>
      <el-button link size="small" @click="markRead">知道了</el-button>
    </div>
    <div v-else class="settle-pop">
      <p>你有 {{ unread }} 条未读结算通知</p>
      <el-button link size="small" @click="$router.push('/me')">去球迷中心查看</el-button>
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
import { isLoggedIn, fetchMe } from '../stores/authStore'
import { useVisibilityPoll } from '../composables/useVisibilityPoll'

const CATEGORY = 'predict_settled'

const router = useRouter()
const unread = ref(0)
const latest = ref<UserNotification | null>(null)

async function poll() {
  if (!isLoggedIn.value) return
  try {
    unread.value = await getUnreadNotificationCount(CATEGORY)
    if (unread.value > 0) {
      const rows = await getNotifications({ unread_only: true, category: CATEGORY, limit: 1 })
      latest.value = rows[0] ?? null
    } else {
      latest.value = null
    }
  } catch {
    /* ignore */
  }
}

useVisibilityPoll(poll, 60000)

async function markRead() {
  if (!latest.value) return
  await markNotificationsRead([latest.value.id])
  unread.value = Math.max(0, unread.value - 1)
  latest.value = null
  await fetchMe()
  window.dispatchEvent(new CustomEvent('predict-records-refresh'))
  await poll()
}

function goNext(matchId: number) {
  markRead()
  router.push({ path: '/predict', query: { highlight: String(matchId) } })
}
</script>

<style scoped>
.settle-badge {
  margin-right: 4px;
}
.settle-pop p {
  margin: 8px 0 12px;
  font-size: 13px;
  line-height: 1.5;
  color: var(--wc-text-muted, #9a94a8);
}
</style>
